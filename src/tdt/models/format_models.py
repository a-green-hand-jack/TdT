"""
格式相关数据模型

定义了文件格式检测和处理相关的数据结构。
"""

from enum import Enum
from typing import Dict, List, Any

from pydantic import BaseModel, Field, field_validator


class SequenceFormat(str, Enum):
    """支持的序列格式枚举"""
    FASTA = "fasta"
    CSV = "csv"
    JSON = "json"
    UNKNOWN = "unknown"


class FormatDetectionResult(BaseModel):
    """格式检测结果"""
    
    file_path: str = Field(..., description="文件路径")
    detected_format: SequenceFormat = Field(..., description="检测到的格式")
    confidence_scores: Dict[SequenceFormat, float] = Field(
        ..., 
        description="各格式的置信度评分"
    )
    detection_method: str = Field(..., description="检测方法")
    file_extension: str = Field(..., description="文件扩展名")
    file_size_bytes: int = Field(..., ge=0, description="文件大小")
    
    # 格式特定信息
    format_specific_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="格式特定的附加信息"
    )
    
    @field_validator('confidence_scores')
    def validate_confidence_scores(cls, v):
        """验证置信度评分"""
        for format_type, score in v.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(
                    f"置信度评分必须在0-1之间: {format_type}={score}"
                )
        return v
    
    @field_validator('file_extension')
    def normalize_extension(cls, v):
        """标准化文件扩展名"""
        return v.lower().lstrip('.')
    
    def get_highest_confidence_format(self) -> tuple[SequenceFormat, float]:
        """获取置信度最高的格式"""
        if not self.confidence_scores:
            return SequenceFormat.UNKNOWN, 0.0
        
        best_format = max(
            self.confidence_scores.items(),
            key=lambda x: x[1]
        )
        return SequenceFormat(best_format[0]), best_format[1]
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """判断检测结果是否足够可信"""
        _, max_score = self.get_highest_confidence_format()
        return max_score >= threshold
    
    class Config:
        use_enum_values = True


class FormatSpecification(BaseModel):
    """格式规范定义"""
    
    format_name: SequenceFormat = Field(..., description="格式名称")
    description: str = Field(..., description="格式描述")
    file_extensions: List[str] = Field(..., description="支持的文件扩展名")
    mime_types: List[str] = Field(
        default_factory=list,
        description="MIME类型"
    )
    
    # 格式特征
    characteristics: Dict[str, Any] = Field(
        default_factory=dict,
        description="格式特征"
    )
    
    # 检测规则
    detection_rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="自动检测规则"
    )
    
    # 解析规则
    parsing_rules: Dict[str, Any] = Field(
        default_factory=dict,
        description="解析规则"
    )
    
    @field_validator('file_extensions')
    def normalize_extensions(cls, v):
        """标准化文件扩展名"""
        return [ext.lower().lstrip('.') for ext in v]
    
    class Config:
        use_enum_values = True


# 预定义的格式规范
FORMAT_SPECIFICATIONS = {
    SequenceFormat.FASTA: FormatSpecification(
        format_name=SequenceFormat.FASTA,
        description="FASTA格式序列文件",
        file_extensions=["fasta", "fas", "fa", "seq"],
        mime_types=["text/plain", "application/x-fasta"],
        characteristics={
            "header_prefix": ">",
            "line_based": True,
            "sequence_per_record": True,
            "supports_multiline_sequence": True,
            "case_sensitive": False
        },
        detection_rules={
            "header_pattern": r"^>\s*\S+",
            "sequence_pattern": r"^[A-Za-z\-\*]+$",
            "min_header_lines": 1,
            "header_line_ratio_threshold": 0.1
        },
        parsing_rules={
            "ignore_empty_lines": True,
            "strip_whitespace": True,
            "validate_sequence_chars": True,
            "allow_gaps": True
        }
    ),
    
    SequenceFormat.CSV: FormatSpecification(
        format_name=SequenceFormat.CSV,
        description="CSV格式序列文件",
        file_extensions=["csv", "tsv"],
        mime_types=["text/csv", "application/csv"],
        characteristics={
            "tabular_format": True,
            "header_row": True,
            "delimiter_separated": True,
            "supports_metadata": True,
            "single_line_sequence": True
        },
        detection_rules={
            "required_columns": ["sequence", "sequenceID"],
            "optional_columns": ["length", "mol_type", "description"],
            "delimiter_chars": [",", "\t", ";"],
            "min_columns": 2
        },
        parsing_rules={
            "auto_detect_delimiter": True,
            "skip_empty_rows": True,
            "validate_column_mapping": True,
            "infer_data_types": True
        }
    ),
    
    SequenceFormat.JSON: FormatSpecification(
        format_name=SequenceFormat.JSON,
        description="JSON格式序列文件",
        file_extensions=["json"],
        mime_types=["application/json"],
        characteristics={
            "structured_format": True,
            "supports_nested_data": True,
            "supports_metadata": True,
            "schema_validatable": True
        },
        detection_rules={
            "json_parseable": True,
            "required_keys": ["sequences"],
            "optional_keys": ["metadata", "statistics"]
        },
        parsing_rules={
            "validate_schema": True,
            "preserve_structure": True,
            "handle_nested_objects": True
        }
    )
}
