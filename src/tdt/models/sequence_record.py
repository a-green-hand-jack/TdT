"""
序列记录数据模型

定义了用于存储和验证序列数据的核心数据结构。
"""

import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SequenceComposition(BaseModel):
    """序列组成分析结果"""
    
    composition: Dict[str, int] = Field(
        ..., 
        description="字符及其出现次数的字典"
    )
    total_residues: int = Field(..., description="总残基数")
    most_frequent: str = Field(..., description="最常见的残基")
    least_frequent: str = Field(..., description="最少见的残基")
    
    @field_validator('composition')
    def validate_composition(cls, v):
        """验证组成数据"""
        if not v:
            raise ValueError("组成数据不能为空")
        
        # 检查是否有负数
        for char, count in v.items():
            if count < 0:
                raise ValueError(f"字符 {char} 的计数不能为负数: {count}")
        
        return v
    
    @model_validator(mode='after')
    def validate_totals(self):
        """验证总数一致性"""
        composition = self.composition
        total_residues = self.total_residues
        
        calculated_total = sum(composition.values())
        if calculated_total != total_residues:
            raise ValueError(
                f"总残基数不匹配：计算值={calculated_total}, 声明值={total_residues}"
            )
        
        return self


class SequenceAnalysis(BaseModel):
    """序列分析结果"""
    
    molecular_weight: Optional[float] = Field(None, description="分子量 (Da)")
    isoelectric_point: Optional[float] = Field(None, description="等电点")
    hydrophobicity: Optional[float] = Field(None, description="疏水性指数")
    gc_content: Optional[float] = Field(None, description="GC含量 (仅DNA/RNA)")
    instability_index: Optional[float] = Field(None, description="不稳定性指数")
    aliphatic_index: Optional[float] = Field(None, description="脂肪族指数")
    
    @field_validator('gc_content')
    def validate_gc_content(cls, v):
        """验证GC含量范围"""
        if v is not None and not (0 <= v <= 1):
            raise ValueError(f"GC含量必须在0-1之间: {v}")
        return v
    
    @field_validator('isoelectric_point')
    def validate_pi(cls, v):
        """验证等电点范围"""
        if v is not None and not (0 <= v <= 14):
            raise ValueError(f"等电点必须在0-14之间: {v}")
        return v


class SequenceSource(BaseModel):
    """序列来源信息"""
    
    file_path: str = Field(..., description="源文件路径")
    file_format: str = Field(..., description="文件格式")
    line_start: Optional[int] = Field(None, description="起始行号")
    line_end: Optional[int] = Field(None, description="结束行号")
    original_header: Optional[str] = Field(None, description="原始头部信息")
    extraction_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="提取时间戳"
    )


class SequenceAnnotations(BaseModel):
    """序列注释信息"""
    
    gene_name: str = Field("", description="基因名称")
    organism: str = Field("", description="来源生物")
    expression_system: str = Field("", description="表达系统")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    modifications: List[str] = Field(default_factory=list, description="修饰列表")
    function: str = Field("", description="功能描述")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    references: List[str] = Field(default_factory=list, description="参考文献")
    custom_annotations: Dict[str, Any] = Field(
        default_factory=dict,
        description="自定义注释"
    )


class SequenceValidation(BaseModel):
    """序列验证结果"""
    
    is_valid: bool = Field(..., description="是否通过验证")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    errors: List[str] = Field(default_factory=list, description="错误信息")
    validation_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="验证时间戳"
    )
    
    @model_validator(mode='after')
    def validate_consistency(self):
        """验证一致性"""
        # 如果有错误，应该标记为无效
        if self.errors and self.is_valid:
            self.is_valid = False
        
        # 如果没有错误但标记为无效，添加通用错误信息
        if not self.errors and not self.is_valid:
            self.errors = ["序列验证失败，但未提供具体错误信息"]
        
        return self


class SequenceData(BaseModel):
    """序列数据核心信息"""
    
    raw_sequence: str = Field(..., min_length=1, description="原始序列")
    cleaned_sequence: str = Field("", description="清理后的序列")
    length: int = Field(..., gt=0, description="序列长度")
    molecular_type: str = Field(
        ..., 
        pattern="^(protein|dna|rna|unknown)$",
        description="分子类型"
    )
    checksum: str = Field(..., description="序列校验和")
    composition: SequenceComposition = Field(..., description="序列组成")
    
    @field_validator('raw_sequence')
    def validate_sequence(cls, v):
        """验证序列格式"""
        if not v.strip():
            raise ValueError("序列不能为空或仅包含空白字符")
        return v.strip()
    
    @field_validator('cleaned_sequence')
    @classmethod
    def set_cleaned_sequence(cls, v, info):
        """自动生成清理后的序列"""
        if not v and info.data and 'raw_sequence' in info.data:
            raw_seq = info.data['raw_sequence']
            # 移除空白字符和非字母字符
            v = re.sub(r'[^A-Za-z]', '', raw_seq).upper()
        return v
    
    @field_validator('length')
    @classmethod
    def validate_length(cls, v, info):
        """验证长度一致性"""
        if info.data and 'cleaned_sequence' in info.data:
            cleaned_sequence = info.data['cleaned_sequence']
            if cleaned_sequence and v != len(cleaned_sequence):
                raise ValueError(
                    f"长度不匹配：声明长度={v}, 实际长度={len(cleaned_sequence)}"
                )
        return v
    
    @field_validator('checksum')
    @classmethod
    def generate_checksum(cls, v, info):
        """自动生成校验和"""
        if not v and info.data and 'cleaned_sequence' in info.data:
            cleaned_sequence = info.data['cleaned_sequence']
            if cleaned_sequence:
                v = hashlib.sha256(cleaned_sequence.encode()).hexdigest()[:16]
        return v
    
    @model_validator(mode='after')
    def validate_molecular_type(self):
        """根据序列内容验证分子类型"""
        cleaned_sequence = self.cleaned_sequence
        molecular_type = self.molecular_type
        
        if cleaned_sequence and molecular_type != 'unknown':
            # 检查序列字符是否符合分子类型
            protein_chars = set('ACDEFGHIKLMNPQRSTVWY')
            dna_chars = set('ATCGNRYSWKMBDHV')  # 包括IUPAC核酸代码
            rna_chars = set('AUCGNRYSWKMBDHV')  # 包括IUPAC核酸代码
            
            seq_chars = set(cleaned_sequence.upper())
            
            if molecular_type == 'protein':
                invalid_chars = seq_chars - protein_chars
                if invalid_chars:
                    raise ValueError(
                        f"蛋白质序列包含无效字符: {invalid_chars}"
                    )
            elif molecular_type == 'dna':
                invalid_chars = seq_chars - dna_chars
                if invalid_chars:
                    raise ValueError(
                        f"DNA序列包含无效字符: {invalid_chars}"
                    )
            elif molecular_type == 'rna':
                invalid_chars = seq_chars - rna_chars
                if invalid_chars:
                    raise ValueError(
                        f"RNA序列包含无效字符: {invalid_chars}"
                    )
        
        return self


class SequenceRecord(BaseModel):
    """完整的序列记录"""
    
    sequence_id: str = Field(..., min_length=1, description="序列标识符")
    sequence_name: str = Field("", description="序列名称")
    description: str = Field("", description="序列描述")
    
    # 核心数据
    source: SequenceSource = Field(..., description="来源信息")
    sequence_data: SequenceData = Field(..., description="序列数据")
    
    # 分析和注释
    analysis: SequenceAnalysis = Field(
        default_factory=SequenceAnalysis,
        description="分析结果"
    )
    annotations: SequenceAnnotations = Field(
        default_factory=SequenceAnnotations,
        description="注释信息"
    )
    validation: SequenceValidation = Field(..., description="验证结果")
    
    # 元数据
    creation_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="创建时间戳"
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="最后修改时间"
    )
    
    @field_validator('sequence_id')
    def validate_sequence_id(cls, v):
        """验证序列ID格式"""
        # 移除前后空白字符
        v = v.strip()
        
        # 检查是否为空
        if not v:
            raise ValueError("序列ID不能为空")
        
        # 检查长度
        if len(v) > 100:
            raise ValueError("序列ID长度不能超过100个字符")
        
        return v
    
    class Config:
        """Pydantic配置"""
        # 允许使用枚举值
        use_enum_values = True
        # 验证赋值
        validate_assignment = True
        # JSON编码器
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
