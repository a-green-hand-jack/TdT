"""
权利要求书数据模型

定义权利要求书文档、SEQ ID引用、突变模式等数据结构。
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field, validator


class SeqIdReference(BaseModel):
    """SEQ ID NO引用"""
    seq_id_no: str = Field(..., description="SEQ ID编号，如'SEQ ID NO:2'")
    numeric_id: int = Field(..., description="数字ID，如2")
    context: str = Field(..., description="引用的上下文")
    position_in_text: int = Field(..., description="在文本中的位置")


class MutationPattern(BaseModel):
    """突变模式"""
    pattern_type: str = Field(..., description="模式类型：single_point, combinatorial, range等")
    positions: List[int] = Field(default_factory=list, description="涉及的氨基酸位置")
    mutations: List[str] = Field(default_factory=list, description="具体突变，如['W46E', 'Q62W']")
    description: str = Field(..., description="原始描述文本")
    context: str = Field(..., description="在权利要求中的上下文")


class ClaimItem(BaseModel):
    """单个权利要求条目"""
    claim_number: int = Field(..., description="权利要求编号")
    claim_type: str = Field(..., description="权利要求类型：independent, dependent等")
    dependencies: List[int] = Field(default_factory=list, description="从属关系")
    content: str = Field(..., description="权利要求内容")
    seq_id_references: List[SeqIdReference] = Field(default_factory=list, description="SEQ ID引用")
    mutation_patterns: List[MutationPattern] = Field(default_factory=list, description="突变模式")
    technical_features: List[str] = Field(default_factory=list, description="技术特征")


class ClaimsDocument(BaseModel):
    """权利要求书文档"""
    patent_number: str = Field(..., description="专利号")
    source_file: Path = Field(..., description="源文件路径")
    extraction_timestamp: datetime = Field(default_factory=datetime.now, description="提取时间")
    total_claims: int = Field(..., description="权利要求总数")
    claims: List[ClaimItem] = Field(..., description="权利要求列表")
    
    # 统计信息
    total_seq_id_references: int = Field(default=0, description="SEQ ID引用总数")
    unique_seq_ids: Set[str] = Field(default_factory=set, description="唯一SEQ ID集合")
    mutation_pattern_count: int = Field(default=0, description="突变模式总数")
    
    @validator('total_seq_id_references', always=True)
    def calculate_seq_id_count(cls, v, values):
        if 'claims' in values:
            return sum(len(claim.seq_id_references) for claim in values['claims'])
        return 0
    
    @validator('unique_seq_ids', always=True)
    def calculate_unique_seq_ids(cls, v, values):
        if 'claims' in values:
            seq_ids = set()
            for claim in values['claims']:
                for ref in claim.seq_id_references:
                    seq_ids.add(ref.seq_id_no)
            return seq_ids
        return set()
    
    @validator('mutation_pattern_count', always=True)
    def calculate_mutation_count(cls, v, values):
        if 'claims' in values:
            return sum(len(claim.mutation_patterns) for claim in values['claims'])
        return 0
    
    class Config:
        # 允许使用Set类型
        arbitrary_types_allowed = True


class SequenceClaimsMapping(BaseModel):
    """序列与权利要求的映射关系"""
    patent_number: str = Field(..., description="专利号")
    mapping_timestamp: datetime = Field(default_factory=datetime.now, description="映射时间")
    
    # 映射关系
    seq_id_to_sequence: Dict[str, str] = Field(default_factory=dict, description="SEQ ID到sequence_id的映射")
    sequence_to_claims: Dict[str, List[int]] = Field(default_factory=dict, description="sequence_id到权利要求编号的映射")
    claim_to_sequences: Dict[int, List[str]] = Field(default_factory=dict, description="权利要求编号到sequence_id的映射")
    
    # 未匹配的引用
    unmatched_seq_ids: List[str] = Field(default_factory=list, description="未找到对应序列的SEQ ID")
    orphaned_sequences: List[str] = Field(default_factory=list, description="未在权利要求中引用的序列")
    
    # 统计信息
    mapping_statistics: Dict[str, int] = Field(default_factory=dict, description="映射统计")
    
    def add_mapping(self, seq_id_no: str, sequence_id: str, claim_number: int):
        """添加映射关系"""
        # SEQ ID到序列ID的映射
        self.seq_id_to_sequence[seq_id_no] = sequence_id
        
        # 序列ID到权利要求的映射
        if sequence_id not in self.sequence_to_claims:
            self.sequence_to_claims[sequence_id] = []
        if claim_number not in self.sequence_to_claims[sequence_id]:
            self.sequence_to_claims[sequence_id].append(claim_number)
        
        # 权利要求到序列ID的映射
        if claim_number not in self.claim_to_sequences:
            self.claim_to_sequences[claim_number] = []
        if sequence_id not in self.claim_to_sequences[claim_number]:
            self.claim_to_sequences[claim_number].append(sequence_id)
    
    def get_sequences_for_claim(self, claim_number: int) -> List[str]:
        """获取指定权利要求涉及的序列"""
        return self.claim_to_sequences.get(claim_number, [])
    
    def get_claims_for_sequence(self, sequence_id: str) -> List[int]:
        """获取引用指定序列的权利要求"""
        return self.sequence_to_claims.get(sequence_id, [])
    
    def calculate_statistics(self):
        """计算映射统计信息"""
        self.mapping_statistics = {
            'total_mapped_seq_ids': len(self.seq_id_to_sequence),
            'total_mapped_sequences': len(self.sequence_to_claims),
            'total_mapped_claims': len(self.claim_to_sequences),
            'unmatched_seq_ids_count': len(self.unmatched_seq_ids),
            'orphaned_sequences_count': len(self.orphaned_sequences)
        }
