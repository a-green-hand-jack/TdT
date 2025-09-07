"""
数据加载器

负责加载权利要求书Markdown文件、标准化序列JSON文件和现有规则数据。
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models.claims_models import (
    ClaimItem, ClaimsDocument, MutationPattern, SeqIdReference,
    SequenceClaimsMapping
)
from ..models.sequence_record import SequenceProcessingResult

logger = logging.getLogger(__name__)


class DataLoader:
    """数据加载和预处理器"""
    
    def __init__(self):
        """初始化数据加载器"""
        # SEQ ID NO识别正则表达式
        self.seq_id_pattern = re.compile(
            r'SEQ\s+ID\s+NO\s*[:\.]?\s*(\d+)', 
            re.IGNORECASE
        )
        
        # 突变模式识别正则表达式  
        self.mutation_patterns = {
            'single_point': re.compile(r'[A-Z]\d+[A-Z]'),  # W46E
            'multi_point': re.compile(r'[A-Z]\d+[A-Z](?:/[A-Z]\d+[A-Z])+'),  # W46E/Q62W
            'position_range': re.compile(r'(\d+)-(\d+)'),  # 46-62
            'variable_position': re.compile(r'[A-Z](\d+)X'),  # W46X
        }
    
    def load_claims_markdown(self, md_path: Path) -> ClaimsDocument:
        """加载权利要求书Markdown文件
        
        Args:
            md_path: Markdown文件路径
            
        Returns:
            解析后的权利要求书文档
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not md_path.exists():
            raise FileNotFoundError(f"权利要求书文件不存在: {md_path}")
        
        logger.info(f"开始加载权利要求书: {md_path}")
        
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取专利号
            patent_number = self._extract_patent_number(content)
            
            # 解析权利要求条目
            claims = self._parse_claims(content)
            
            # 为每个权利要求提取SEQ ID引用和突变模式
            for claim in claims:
                claim.seq_id_references = self.extract_seq_id_references(claim.content)
                claim.mutation_patterns = self.identify_mutation_patterns(claim.content)
                claim.technical_features = self._extract_technical_features(claim.content)
            
            document = ClaimsDocument(
                patent_number=patent_number,
                source_file=md_path,
                total_claims=len(claims),
                claims=claims
            )
            
            logger.info(f"成功加载权利要求书: {patent_number}, 包含{len(claims)}个权利要求")
            return document
            
        except Exception as e:
            logger.error(f"加载权利要求书失败: {e}")
            raise
    
    def load_sequence_json(self, json_path: Path) -> SequenceProcessingResult:
        """加载标准化序列JSON文件
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            序列处理结果对象
        """
        if not json_path.exists():
            raise FileNotFoundError(f"序列JSON文件不存在: {json_path}")
        
        logger.info(f"开始加载序列JSON: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 使用现有的序列处理结果模型
            result = SequenceProcessingResult(**data)
            
            logger.info(f"成功加载序列数据: {result.metadata.total_sequences}个序列")
            return result
            
        except Exception as e:
            logger.error(f"加载序列JSON失败: {e}")
            raise
    
    def load_existing_rules(self, json_path: Path) -> Dict:
        """加载现有规则JSON数据
        
        Args:
            json_path: 规则JSON文件路径
            
        Returns:
            现有规则数据字典
        """
        if not json_path.exists():
            raise FileNotFoundError(f"规则JSON文件不存在: {json_path}")
        
        logger.info(f"开始加载现有规则: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"成功加载现有规则: {len(data.get('rules', []))}条规则")
            return data
            
        except Exception as e:
            logger.error(f"加载现有规则失败: {e}")
            raise
    
    def extract_seq_id_references(self, text: str) -> List[SeqIdReference]:
        """从文本中提取SEQ ID NO引用
        
        Args:
            text: 要分析的文本
            
        Returns:
            SEQ ID引用列表
        """
        references = []
        
        for match in self.seq_id_pattern.finditer(text):
            seq_id_no = f"SEQ ID NO:{match.group(1)}"
            numeric_id = int(match.group(1))
            position = match.start()
            
            # 获取上下文（前后50个字符）
            start = max(0, position - 50)
            end = min(len(text), position + 50)
            context = text[start:end].strip()
            
            ref = SeqIdReference(
                seq_id_no=seq_id_no,
                numeric_id=numeric_id,
                context=context,
                position_in_text=position
            )
            references.append(ref)
        
        logger.debug(f"提取到{len(references)}个SEQ ID引用")
        return references
    
    def identify_mutation_patterns(self, text: str) -> List[MutationPattern]:
        """识别突变模式和位点描述
        
        Args:
            text: 要分析的文本
            
        Returns:
            突变模式列表
        """
        patterns = []
        
        # 单点突变模式
        for match in self.mutation_patterns['single_point'].finditer(text):
            mutation = match.group(0)
            position = int(re.search(r'\d+', mutation).group())
            
            pattern = MutationPattern(
                pattern_type="single_point",
                positions=[position],
                mutations=[mutation],
                description=mutation,
                context=self._get_context(text, match.start())
            )
            patterns.append(pattern)
        
        # 多点突变模式
        for match in self.mutation_patterns['multi_point'].finditer(text):
            mutation_str = match.group(0)
            mutations = mutation_str.split('/')
            positions = []
            
            for mut in mutations:
                pos_match = re.search(r'\d+', mut)
                if pos_match:
                    positions.append(int(pos_match.group()))
            
            pattern = MutationPattern(
                pattern_type="combinatorial",
                positions=positions,
                mutations=mutations,
                description=mutation_str,
                context=self._get_context(text, match.start())
            )
            patterns.append(pattern)
        
        # 可变位点模式（如W46X）
        for match in self.mutation_patterns['variable_position'].finditer(text):
            mutation = match.group(0)
            position = int(match.group(1))
            
            pattern = MutationPattern(
                pattern_type="variable_position",
                positions=[position],
                mutations=[mutation],
                description=mutation,
                context=self._get_context(text, match.start())
            )
            patterns.append(pattern)
        
        logger.debug(f"识别到{len(patterns)}个突变模式")
        return patterns
    
    def create_sequence_claims_mapping(self, claims_doc: ClaimsDocument, 
                                     sequence_result: SequenceProcessingResult) -> SequenceClaimsMapping:
        """创建序列与权利要求的映射关系
        
        Args:
            claims_doc: 权利要求书文档
            sequence_result: 序列处理结果
            
        Returns:
            序列与权利要求的映射关系
        """
        mapping = SequenceClaimsMapping(patent_number=claims_doc.patent_number)
        
        # 创建SEQ ID到序列的映射表
        seq_id_to_sequence = {}
        for seq_record in sequence_result.sequences:
            # 尝试从sequence_id中提取SEQ ID信息
            # 这里可能需要根据实际数据格式调整
            if 'SEQ_ID_NO' in seq_record.sequence_id:
                seq_id_to_sequence[seq_record.sequence_id] = seq_record.sequence_id
        
        # 建立映射关系
        for claim in claims_doc.claims:
            for seq_ref in claim.seq_id_references:
                # 查找对应的序列
                sequence_id = None
                for seq_record in sequence_result.sequences:
                    # 这里需要根据实际情况调整匹配逻辑
                    if str(seq_ref.numeric_id) in seq_record.sequence_id:
                        sequence_id = seq_record.sequence_id
                        break
                
                if sequence_id:
                    mapping.add_mapping(seq_ref.seq_id_no, sequence_id, claim.claim_number)
                else:
                    mapping.unmatched_seq_ids.append(seq_ref.seq_id_no)
        
        # 找出未引用的序列
        referenced_sequences = set(mapping.sequence_to_claims.keys())
        all_sequences = {seq.sequence_id for seq in sequence_result.sequences}
        mapping.orphaned_sequences = list(all_sequences - referenced_sequences)
        
        # 计算统计信息
        mapping.calculate_statistics()
        
        logger.info(f"创建序列映射: {mapping.mapping_statistics}")
        return mapping
    
    def _extract_patent_number(self, content: str) -> str:
        """从内容中提取专利号"""
        # 尝试多种专利号模式
        patterns = [
            # 专利申请公布号：CN 202210107337 或 CN118284690A
            r'专利申请公布号：?\s*([A-Z]{2}\s*\d+(?:\s*[A-Z])?)',
            # Patent No.: CN118284690A
            r'Patent\s+No\.?\s*:?\s*([A-Z]{2}\s*\d+(?:\s*[A-Z])?)',
            # 通用模式：CN118284690A 或 CN 202210107337
            r'([A-Z]{2}\s*\d+(?:\s*[A-Z])?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # 清理空格并返回
                patent_number = match.group(1).strip()
                # 规范化格式：确保国家代码和数字之间有空格
                if re.match(r'^[A-Z]{2}\d', patent_number):
                    patent_number = patent_number[:2] + ' ' + patent_number[2:]
                return patent_number
        
        return "UNKNOWN"
    
    def _parse_claims(self, content: str) -> List[ClaimItem]:
        """解析权利要求条目"""
        claims = []
        
        # 按数字编号分割权利要求
        claim_pattern = r'^(\d+)\.\s*(.*?)(?=^\d+\.|$)'
        matches = re.findall(claim_pattern, content, re.MULTILINE | re.DOTALL)
        
        for claim_num_str, claim_content in matches:
            claim_number = int(claim_num_str)
            
            # 判断是否为从属权利要求
            dependencies = self._extract_dependencies(claim_content)
            claim_type = "dependent" if dependencies else "independent"
            
            claim = ClaimItem(
                claim_number=claim_number,
                claim_type=claim_type,
                dependencies=dependencies,
                content=claim_content.strip()
            )
            claims.append(claim)
        
        return claims
    
    def _extract_dependencies(self, content: str) -> List[int]:
        """提取权利要求的从属关系"""
        dependencies = []
        
        # 查找"根据权利要求X"等模式
        patterns = [
            r'根据权利要求\s*(\d+)',
            r'according\s+to\s+claim\s*(\d+)',
            r'依据权利要求\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dependencies.extend([int(m) for m in matches])
        
        return list(set(dependencies))  # 去重
    
    def _extract_technical_features(self, content: str) -> List[str]:
        """提取技术特征"""
        features = []
        
        # 这里可以添加更复杂的技术特征提取逻辑
        # 目前简单地以句号分割
        sentences = [s.strip() for s in content.split('。') if s.strip()]
        
        # 过滤掉太短的句子
        features = [s for s in sentences if len(s) > 10]
        
        return features
    
    def _get_context(self, text: str, position: int, window: int = 50) -> str:
        """获取指定位置的上下文"""
        start = max(0, position - window)
        end = min(len(text), position + window)
        return text[start:end].strip()
