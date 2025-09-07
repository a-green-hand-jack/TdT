"""
TDT序列处理数据模型

本模块包含用于序列数据处理的所有数据模型，基于Pydantic实现严格的类型检查和数据验证。
"""

from .sequence_record import (
    SequenceRecord,
    SequenceData,
    SequenceComposition,
    SequenceAnalysis,
    SequenceSource,
    SequenceAnnotations,
    SequenceValidation
)

from .processing_models import (
    ProcessingMetadata,
    ProcessingResult,
    BatchProcessingResult,
    ValidationResult,
    ProcessingLog
)

from .format_models import (
    SequenceFormat,
    FormatDetectionResult
)

__all__ = [
    # 序列记录相关
    'SequenceRecord',
    'SequenceData', 
    'SequenceComposition',
    'SequenceAnalysis',
    'SequenceSource',
    'SequenceAnnotations',
    'SequenceValidation',
    
    # 处理结果相关
    'ProcessingMetadata',
    'ProcessingResult',
    'BatchProcessingResult',
    'ValidationResult',
    'ProcessingLog',
    
    # 格式相关
    'SequenceFormat',
    'FormatDetectionResult'
]
