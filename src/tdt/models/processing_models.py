"""
处理相关数据模型

定义了序列处理过程中使用的各种数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, field_validator


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ProcessingStatus(str, Enum):
    """处理状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class ProcessingLog(BaseModel):
    """处理日志条目"""
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="日志时间戳"
    )
    level: LogLevel = Field(..., description="日志级别")
    message: str = Field(..., description="日志消息")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="附加上下文信息"
    )
    
    class Config:
        use_enum_values = True


class ProcessingMetadata(BaseModel):
    """处理元数据"""
    
    source_file: str = Field(..., description="源文件路径")
    file_format: str = Field(..., description="检测到的文件格式")
    processing_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="处理时间戳"
    )
    processor_version: str = Field(..., description="处理器版本")
    total_sequences: int = Field(..., ge=0, description="序列总数")
    file_size_bytes: int = Field(..., ge=0, description="文件大小（字节）")
    md5_checksum: Optional[str] = Field(None, description="文件MD5校验和")
    processing_duration_ms: Optional[float] = Field(
        None, 
        description="处理耗时（毫秒）"
    )
    
    @field_validator('source_file')
    def validate_source_file(cls, v):
        """验证源文件路径"""
        if not v.strip():
            raise ValueError("源文件路径不能为空")
        return v.strip()


class ValidationResult(BaseModel):
    """验证结果"""
    
    is_valid: bool = Field(..., description="是否验证通过")
    total_errors: int = Field(0, ge=0, description="错误总数")
    total_warnings: int = Field(0, ge=0, description="警告总数")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    validation_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="验证时间戳"
    )
    
    @field_validator('total_errors')
    @classmethod
    def validate_error_count(cls, v, info):
        """验证错误计数"""
        if info.data and 'errors' in info.data:
            errors = info.data['errors']
            if v != len(errors):
                raise ValueError(f"错误计数不匹配：声明={v}, 实际={len(errors)}")
        return v
    
    @field_validator('total_warnings')
    @classmethod
    def validate_warning_count(cls, v, info):
        """验证警告计数"""
        if info.data and 'warnings' in info.data:
            warnings = info.data['warnings']
            if v != len(warnings):
                raise ValueError(f"警告计数不匹配：声明={v}, 实际={len(warnings)}")
        return v


class ProcessingResult(BaseModel):
    """单文件处理结果"""
    
    status: ProcessingStatus = Field(..., description="处理状态")
    metadata: ProcessingMetadata = Field(..., description="处理元数据")
    sequences: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="解析出的序列列表"
    )
    validation: ValidationResult = Field(..., description="验证结果")
    statistics: Dict[str, Any] = Field(
        default_factory=dict,
        description="统计信息"
    )
    processing_log: List[ProcessingLog] = Field(
        default_factory=list,
        description="处理日志"
    )
    
    @field_validator('sequences')
    @classmethod
    def validate_sequence_count(cls, v, info):
        """验证序列数量一致性"""
        if info.data and 'metadata' in info.data:
            metadata = info.data['metadata']
            if metadata and len(v) != metadata.total_sequences:
                raise ValueError(
                    f"序列数量不匹配：元数据声明={metadata.total_sequences}, "
                    f"实际数量={len(v)}"
                )
        return v
    
    class Config:
        use_enum_values = True


class BatchProcessingResult(BaseModel):
    """批量处理结果"""
    
    input_directory: str = Field(..., description="输入目录")
    output_directory: str = Field(..., description="输出目录")
    pattern: str = Field(..., description="文件匹配模式")
    
    # 处理统计
    total_files: int = Field(..., ge=0, description="总文件数")
    processed_files: int = Field(..., ge=0, description="已处理文件数")
    successful_files: int = Field(..., ge=0, description="成功处理文件数")
    failed_files: int = Field(..., ge=0, description="失败文件数")
    skipped_files: int = Field(..., ge=0, description="跳过文件数")
    
    # 时间信息
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    total_duration_ms: Optional[float] = Field(
        None, 
        description="总耗时（毫秒）"
    )
    
    # 详细结果
    file_results: Dict[str, ProcessingResult] = Field(
        default_factory=dict,
        description="各文件处理结果"
    )
    
    # 全局统计
    global_statistics: Dict[str, Any] = Field(
        default_factory=dict,
        description="全局统计信息"
    )
    
    # 处理日志
    global_log: List[ProcessingLog] = Field(
        default_factory=list,
        description="全局处理日志"
    )
    
    @field_validator('processed_files')
    @classmethod
    def validate_processed_count(cls, v, info):
        """验证已处理文件数"""
        if info.data:
            successful = info.data.get('successful_files', 0)
            failed = info.data.get('failed_files', 0) 
            skipped = info.data.get('skipped_files', 0)
            
            expected = successful + failed + skipped
            if v != expected:
                raise ValueError(
                    f"已处理文件数不匹配：声明={v}, "
                    f"计算值={expected} (成功{successful}+失败{failed}+跳过{skipped})"
                )
        return v
    
    @field_validator('total_files')
    @classmethod
    def validate_total_files(cls, v, info):
        """验证总文件数"""
        if info.data:
            processed = info.data.get('processed_files', 0)
            if v < processed:
                raise ValueError(
                    f"总文件数不能小于已处理文件数：总数={v}, 已处理={processed}"
                )
        return v
    
    def calculate_success_rate(self) -> float:
        """计算成功率"""
        if self.processed_files == 0:
            return 0.0
        return self.successful_files / self.processed_files
    
    def add_file_result(self, file_path: str, result: ProcessingResult) -> None:
        """添加文件处理结果"""
        self.file_results[file_path] = result
        
        # 更新计数
        if result.status == ProcessingStatus.SUCCESS:
            self.successful_files += 1
        elif result.status == ProcessingStatus.FAILED:
            self.failed_files += 1
        elif result.status == ProcessingStatus.SKIPPED:
            self.skipped_files += 1
        
        self.processed_files += 1
    
    def finalize(self) -> None:
        """完成批量处理，设置结束时间和总耗时"""
        self.end_time = datetime.now()
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            self.total_duration_ms = duration.total_seconds() * 1000
    
    class Config:
        use_enum_values = True
