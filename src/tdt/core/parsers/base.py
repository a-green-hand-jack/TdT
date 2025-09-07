"""
序列解析器基类

定义了所有序列解析器的通用接口和基础功能。
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from ...models.sequence_record import SequenceRecord
from ...models.processing_models import ValidationResult
from ...models.format_models import SequenceFormat

logger = logging.getLogger(__name__)


class ParsingError(Exception):
    """解析错误异常"""
    
    def __init__(self, message: str, line_number: Optional[int] = None, 
                 context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.line_number = line_number
        self.context = context or {}
        
        full_message = message
        if line_number is not None:
            full_message = f"第{line_number}行: {message}"
        
        super().__init__(full_message)


class BaseSequenceParser(ABC):
    """序列解析器抽象基类"""
    
    def __init__(self, format_type: SequenceFormat):
        """
        初始化解析器
        
        Args:
            format_type: 支持的序列格式
        """
        self.format_type = format_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[SequenceRecord]:
        """
        解析序列文件，返回序列记录列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[SequenceRecord]: 序列记录列表
            
        Raises:
            ParsingError: 解析错误
            FileNotFoundError: 文件不存在
        """
        pass
    
    @abstractmethod
    def validate(self, sequences: List[SequenceRecord]) -> ValidationResult:
        """
        验证解析结果的正确性
        
        Args:
            sequences: 序列记录列表
            
        Returns:
            ValidationResult: 验证结果
        """
        pass
    
    def get_supported_extensions(self) -> List[str]:
        """
        返回支持的文件扩展名
        
        Returns:
            List[str]: 支持的扩展名列表
        """
        from ...models.format_models import FORMAT_SPECIFICATIONS
        spec = FORMAT_SPECIFICATIONS.get(self.format_type)
        return spec.file_extensions if spec else []
    
    def get_format_type(self) -> SequenceFormat:
        """
        获取解析器支持的格式类型
        
        Returns:
            SequenceFormat: 格式类型
        """
        return self.format_type
    
    def _validate_file(self, file_path: Path) -> None:
        """
        验证输入文件
        
        Args:
            file_path: 文件路径
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件无效
        """
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")
        
        if file_path.stat().st_size == 0:
            raise ValueError(f"文件为空: {file_path}")
    
    def _detect_molecular_type(self, sequence: str) -> str:
        """
        自动检测分子类型
        
        Args:
            sequence: 清理后的序列
            
        Returns:
            str: 分子类型 (protein|dna|rna|unknown)
        """
        if not sequence:
            return "unknown"
        
        # 转换为大写并去除空白字符
        clean_seq = sequence.upper().replace(' ', '').replace('\n', '').replace('\t', '')
        
        # 计算各种字符的比例
        total_chars = len(clean_seq)
        if total_chars == 0:
            return "unknown"
        
        # 蛋白质特有氨基酸
        protein_specific = set('EQHILKMFPWY')
        protein_chars = set('ACDEFGHIKLMNPQRSTVWY')
        
        # 核酸字符 
        nucleic_chars = set('ATCGUN')  # 包括通用核苷酸字符
        
        # 计算各类字符的出现次数
        protein_specific_count = sum(1 for c in clean_seq if c in protein_specific)
        protein_total_count = sum(1 for c in clean_seq if c in protein_chars)
        nucleic_total_count = sum(1 for c in clean_seq if c in nucleic_chars)
        
        # 决策逻辑
        protein_specific_ratio = protein_specific_count / total_chars
        protein_total_ratio = protein_total_count / total_chars
        nucleic_ratio = nucleic_total_count / total_chars
        
        # 如果有蛋白质特有氨基酸，很可能是蛋白质
        if protein_specific_ratio > 0.1:
            return "protein"
        
        # 如果所有字符都是核酸字符
        if nucleic_ratio > 0.95:
            # 区分DNA和RNA
            has_t = 'T' in clean_seq
            has_u = 'U' in clean_seq
            
            if has_u and not has_t:
                return "rna"
            elif has_t and not has_u:
                return "dna"
            elif not has_u and not has_t:
                # 只有A、C、G，默认为DNA
                return "dna"
            else:
                # 同时有T和U，不太可能，默认为DNA
                return "dna"
        
        # 如果大部分是蛋白质字符
        if protein_total_ratio > 0.8:
            return "protein"
        
        # 无法确定
        return "unknown"
    
    def _clean_sequence(self, sequence: str) -> str:
        """
        清理序列字符串
        
        Args:
            sequence: 原始序列
            
        Returns:
            str: 清理后的序列
        """
        import re
        
        # 移除空白字符和非字母字符（保留标准的序列字符）
        cleaned = re.sub(r'[^A-Za-z\-\*]', '', sequence)
        
        # 转换为大写
        cleaned = cleaned.upper()
        
        # 移除常见的gap字符（可选）
        # cleaned = cleaned.replace('-', '').replace('*', '')
        
        return cleaned
    
    def _calculate_composition(self, sequence: str) -> Dict[str, int]:
        """
        计算序列组成
        
        Args:
            sequence: 序列字符串
            
        Returns:
            Dict[str, int]: 字符计数字典
        """
        composition = {}
        for char in sequence:
            composition[char] = composition.get(char, 0) + 1
        
        return composition
    
    def _validate_sequence_characters(self, sequence: str, 
                                    molecular_type: str) -> List[str]:
        """
        验证序列字符是否符合分子类型
        
        Args:
            sequence: 序列字符串
            molecular_type: 分子类型
            
        Returns:
            List[str]: 错误信息列表
        """
        errors = []
        
        if not sequence:
            errors.append("序列为空")
            return errors
        
        # 定义各类型允许的字符
        allowed_chars = {
            'protein': set('ACDEFGHIKLMNPQRSTVWY*-'),
            'dna': set('ATCGNRYSWKMBDHV*-'),  # 包括IUPAC核酸代码
            'rna': set('AUCGNRYSWKMBDHV*-'),  # 包括IUPAC核酸代码
            'unknown': set('ABCDEFGHIJKLMNOPQRSTUVWXYZ*-')  # 允许所有字母
        }
        
        if molecular_type in allowed_chars:
            valid_chars = allowed_chars[molecular_type]
            invalid_chars = set(sequence.upper()) - valid_chars
            
            if invalid_chars:
                errors.append(
                    f"{molecular_type}序列包含无效字符: {sorted(invalid_chars)}"
                )
        
        return errors
    
    def _create_basic_validation_result(self, 
                                      sequences: List[SequenceRecord]) -> ValidationResult:
        """
        创建基础验证结果
        
        Args:
            sequences: 序列记录列表
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        if not sequences:
            errors.append("未解析到任何序列")
        
        # 检查序列ID唯一性
        sequence_ids = [seq.sequence_id for seq in sequences]
        duplicates = set([sid for sid in sequence_ids if sequence_ids.count(sid) > 1])
        
        if duplicates:
            warnings.append(f"发现重复的序列ID: {sorted(duplicates)}")
        
        # 检查序列长度
        for i, seq in enumerate(sequences):
            seq_length = seq.sequence_data.length
            if seq_length == 0:
                errors.append(f"序列{i+1} ({seq.sequence_id}) 长度为0")
            elif seq_length < 10:
                warnings.append(f"序列{i+1} ({seq.sequence_id}) 长度过短: {seq_length}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            total_errors=len(errors),
            total_warnings=len(warnings),
            errors=errors,
            warnings=warnings
        )
