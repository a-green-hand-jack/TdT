"""
统一序列处理器

集成格式检测、解析和JSON输出功能的主要处理器类。
"""

import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .format_detector import SequenceFormatDetector
from .parsers import BaseSequenceParser, FastaParser, CsvParser
from ..models.sequence_record import SequenceRecord
from ..models.processing_models import (
    ProcessingResult,
    ProcessingMetadata,
    BatchProcessingResult,
    ValidationResult,
    ProcessingLog,
    LogLevel,
    ProcessingStatus
)
from ..models.format_models import SequenceFormat

logger = logging.getLogger(__name__)


class UnifiedSequenceProcessor:
    """统一序列处理器主类"""
    
    def __init__(self, processor_version: str = "1.0.0"):
        """
        初始化处理器
        
        Args:
            processor_version: 处理器版本号
        """
        self.processor_version = processor_version
        self.format_detector = SequenceFormatDetector()
        
        # 注册解析器
        self.parsers = {
            SequenceFormat.FASTA: FastaParser(),
            SequenceFormat.CSV: CsvParser()
        }
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def process_file(self, file_path: Union[str, Path], 
                    output_path: Optional[Union[str, Path]] = None,
                    output_format: str = "json",
                    auto_detect_format: bool = True,
                    expected_format: Optional[SequenceFormat] = None) -> ProcessingResult:
        """
        处理单个序列文件
        
        Args:
            file_path: 输入文件路径
            output_path: 输出文件路径（可选）
            output_format: 输出格式 ("json")
            auto_detect_format: 是否自动检测格式
            expected_format: 预期的输入格式
            
        Returns:
            ProcessingResult: 处理结果
        """
        file_path = Path(file_path)
        processing_log = []
        start_time = datetime.now()
        
        try:
            # 验证输入文件
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            processing_log.append(ProcessingLog(
                level=LogLevel.INFO,
                message=f"开始处理文件: {file_path}"
            ))
            
            # 获取文件信息
            file_size = file_path.stat().st_size
            file_md5 = self._calculate_file_md5(file_path)
            
            # 格式检测
            if auto_detect_format:
                detection_result = self.format_detector.detect_format(file_path)
                detected_format = detection_result.detected_format
                
                processing_log.append(ProcessingLog(
                    level=LogLevel.INFO,
                    message=f"检测到文件格式: {detected_format}",
                    context={"confidence_scores": detection_result.confidence_scores}
                ))
                
                # 如果指定了预期格式，验证是否匹配
                if expected_format and detected_format != expected_format:
                    processing_log.append(ProcessingLog(
                        level=LogLevel.WARNING,
                        message=f"检测格式({detected_format})与预期格式({expected_format})不匹配"
                    ))
            else:
                if not expected_format:
                    raise ValueError("禁用自动检测时必须指定预期格式")
                detected_format = expected_format
                
                processing_log.append(ProcessingLog(
                    level=LogLevel.INFO,
                    message=f"使用指定格式: {detected_format}"
                ))
            
            # 选择解析器
            parser = self._get_parser(detected_format)
            if not parser:
                raise ValueError(f"不支持的格式: {detected_format}")
            
            # 解析序列
            sequences = parser.parse(file_path)
            
            processing_log.append(ProcessingLog(
                level=LogLevel.INFO,
                message=f"成功解析{len(sequences)}个序列"
            ))
            
            # 验证结果
            validation_result = parser.validate(sequences)
            
            if validation_result.total_errors > 0:
                processing_log.append(ProcessingLog(
                    level=LogLevel.ERROR,
                    message=f"发现{validation_result.total_errors}个错误",
                    context={"errors": validation_result.errors}
                ))
            
            if validation_result.total_warnings > 0:
                processing_log.append(ProcessingLog(
                    level=LogLevel.WARNING,
                    message=f"发现{validation_result.total_warnings}个警告",
                    context={"warnings": validation_result.warnings}
                ))
            
            # 计算处理时间
            end_time = datetime.now()
            processing_duration = (end_time - start_time).total_seconds() * 1000
            
            # 创建元数据
            format_str = detected_format.value if hasattr(detected_format, 'value') else str(detected_format)
            metadata = ProcessingMetadata(
                source_file=str(file_path),
                file_format=format_str,
                processor_version=self.processor_version,
                total_sequences=len(sequences),
                file_size_bytes=file_size,
                md5_checksum=file_md5,
                processing_duration_ms=processing_duration
            )
            
            # 生成统计信息
            statistics = self._generate_statistics(sequences)
            
            # 创建处理结果
            status = ProcessingStatus.SUCCESS if validation_result.is_valid else ProcessingStatus.PARTIAL
            
            result = ProcessingResult(
                status=status,
                metadata=metadata,
                sequences=[seq.model_dump() for seq in sequences],
                validation=validation_result,
                statistics=statistics,
                processing_log=processing_log
            )
            
            # 保存输出文件
            if output_path:
                self._save_output(result, Path(output_path), output_format)
                processing_log.append(ProcessingLog(
                    level=LogLevel.INFO,
                    message=f"结果已保存到: {output_path}"
                ))
            
            processing_log.append(ProcessingLog(
                level=LogLevel.INFO,
                message=f"处理完成，耗时: {processing_duration:.2f}ms"
            ))
            
            return result
            
        except Exception as e:
            processing_log.append(ProcessingLog(
                level=LogLevel.ERROR,
                message=f"处理失败: {e}",
                context={"error_type": type(e).__name__, "error_details": str(e)}
            ))
            
            # 创建失败的处理结果
            metadata = ProcessingMetadata(
                source_file=str(file_path),
                file_format="unknown",
                processor_version=self.processor_version,
                total_sequences=0,
                file_size_bytes=file_path.stat().st_size if file_path.exists() else 0
            )
            
            validation_result = ValidationResult(
                is_valid=False,
                total_errors=1,
                errors=[str(e)]
            )
            
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                metadata=metadata,
                sequences=[],
                validation=validation_result,
                statistics={},
                processing_log=processing_log
            )
    
    def process_directory(self, input_dir: Union[str, Path],
                         output_dir: Union[str, Path],
                         pattern: str = "*",
                         output_format: str = "json",
                         auto_detect_format: bool = True,
                         recursive: bool = False,
                         max_workers: Optional[int] = None) -> BatchProcessingResult:
        """
        批量处理目录中的序列文件
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            pattern: 文件匹配模式
            output_format: 输出格式
            auto_detect_format: 是否自动检测格式
            recursive: 是否递归处理子目录
            max_workers: 最大并发数
            
        Returns:
            BatchProcessingResult: 批量处理结果
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 查找文件
        if recursive:
            files = list(input_dir.rglob(pattern))
        else:
            files = list(input_dir.glob(pattern))
        
        # 过滤出文件（排除目录）
        files = [f for f in files if f.is_file()]
        
        # 初始化批量处理结果
        batch_result = BatchProcessingResult(
            input_directory=str(input_dir),
            output_directory=str(output_dir),
            pattern=pattern,
            total_files=len(files),
            processed_files=0,
            successful_files=0,
            failed_files=0,
            skipped_files=0,
            start_time=datetime.now()
        )
        
        batch_result.global_log.append(ProcessingLog(
            level=LogLevel.INFO,
            message=f"开始批量处理，共找到{len(files)}个文件"
        ))
        
        # 处理每个文件
        for file_path in files:
            try:
                # 生成输出文件路径
                relative_path = file_path.relative_to(input_dir)
                output_file = output_dir / relative_path.with_suffix(f'.{output_format}')
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 处理文件
                result = self.process_file(
                    file_path=file_path,
                    output_path=output_file,
                    output_format=output_format,
                    auto_detect_format=auto_detect_format
                )
                
                # 记录结果
                batch_result.add_file_result(str(file_path), result)
                
                if result.status == ProcessingStatus.SUCCESS:
                    batch_result.global_log.append(ProcessingLog(
                        level=LogLevel.INFO,
                        message=f"成功处理: {file_path}"
                    ))
                else:
                    batch_result.global_log.append(ProcessingLog(
                        level=LogLevel.WARNING,
                        message=f"处理有问题: {file_path} (状态: {result.status})"
                    ))
                
            except Exception as e:
                batch_result.failed_files += 1
                batch_result.processed_files += 1
                
                batch_result.global_log.append(ProcessingLog(
                    level=LogLevel.ERROR,
                    message=f"处理失败: {file_path} - {e}"
                ))
        
        # 完成批量处理
        batch_result.finalize()
        
        # 生成全局统计信息
        batch_result.global_statistics = self._generate_batch_statistics(batch_result)
        
        batch_result.global_log.append(ProcessingLog(
            level=LogLevel.INFO,
            message=f"批量处理完成，成功率: {batch_result.calculate_success_rate():.2%}"
        ))
        
        return batch_result
    
    def convert_to_json(self, sequences: List[SequenceRecord],
                       metadata: Optional[ProcessingMetadata] = None,
                       include_analysis: bool = True,
                       include_statistics: bool = True) -> Dict[str, Any]:
        """
        转换序列为标准JSON格式
        
        Args:
            sequences: 序列记录列表
            metadata: 处理元数据
            include_analysis: 是否包含分析信息
            include_statistics: 是否包含统计信息
            
        Returns:
            Dict[str, Any]: JSON格式数据
        """
        json_data = {
            "metadata": metadata.model_dump() if metadata else {},
            "sequences": []
        }
        
        # 转换序列数据
        for seq in sequences:
            seq_dict = seq.model_dump()
            
            # 根据参数决定是否包含分析信息
            if not include_analysis:
                seq_dict.pop('analysis', None)
            
            json_data["sequences"].append(seq_dict)
        
        # 添加统计信息
        if include_statistics:
            json_data["statistics"] = self._generate_statistics(sequences)
        
        return json_data
    
    def _get_parser(self, format_type: SequenceFormat) -> Optional[BaseSequenceParser]:
        """
        获取指定格式的解析器
        
        Args:
            format_type: 格式类型
            
        Returns:
            Optional[BaseSequenceParser]: 解析器实例
        """
        return self.parsers.get(format_type)
    
    def _calculate_file_md5(self, file_path: Path) -> str:
        """
        计算文件MD5校验和
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: MD5校验和
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _generate_statistics(self, sequences: List[SequenceRecord]) -> Dict[str, Any]:
        """
        生成序列统计信息
        
        Args:
            sequences: 序列记录列表
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not sequences:
            return {}
        
        # 基本统计
        total_residues = sum(seq.sequence_data.length for seq in sequences)
        lengths = [seq.sequence_data.length for seq in sequences]
        
        # 分子类型统计
        type_counts = {}
        for seq in sequences:
            mol_type = seq.sequence_data.molecular_type
            type_counts[mol_type] = type_counts.get(mol_type, 0) + 1
        
        # 长度分布
        length_stats = {
            "min": min(lengths),
            "max": max(lengths),
            "mean": total_residues / len(sequences),
            "median": sorted(lengths)[len(lengths) // 2]
        }
        
        # 验证状态统计
        valid_sequences = sum(1 for seq in sequences if seq.validation.is_valid)
        
        return {
            "total_sequences": len(sequences),
            "total_residues": total_residues,
            "sequence_types": type_counts,
            "length_distribution": length_stats,
            "validation_summary": {
                "valid_sequences": valid_sequences,
                "invalid_sequences": len(sequences) - valid_sequences,
                "validity_rate": valid_sequences / len(sequences)
            }
        }
    
    def _generate_batch_statistics(self, batch_result: BatchProcessingResult) -> Dict[str, Any]:
        """
        生成批量处理统计信息
        
        Args:
            batch_result: 批量处理结果
            
        Returns:
            Dict[str, Any]: 批量统计信息
        """
        # 收集所有成功处理的序列
        all_sequences = []
        format_counts = {}
        
        for file_path, result in batch_result.file_results.items():
            if result.status == ProcessingStatus.SUCCESS:
                format_type = result.metadata.file_format
                format_counts[format_type] = format_counts.get(format_type, 0) + 1
                
                # 收集序列统计（不重新创建SequenceRecord对象，直接使用字典）
                all_sequences.extend(result.sequences)
        
        return {
            "file_format_distribution": format_counts,
            "total_sequences_processed": len(all_sequences),
            "processing_summary": {
                "success_rate": batch_result.calculate_success_rate(),
                "average_sequences_per_file": (
                    len(all_sequences) / batch_result.successful_files 
                    if batch_result.successful_files > 0 else 0
                )
            }
        }
    
    def _save_output(self, result: ProcessingResult, 
                    output_path: Path, 
                    output_format: str) -> None:
        """
        保存处理结果到文件
        
        Args:
            result: 处理结果
            output_path: 输出文件路径
            output_format: 输出格式
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
    
    def register_parser(self, format_type: SequenceFormat, 
                       parser: BaseSequenceParser) -> None:
        """
        注册新的解析器
        
        Args:
            format_type: 格式类型
            parser: 解析器实例
        """
        self.parsers[format_type] = parser
        self.logger.info(f"注册解析器: {format_type} -> {parser.__class__.__name__}")
    
    def get_supported_formats(self) -> List[SequenceFormat]:
        """
        获取支持的格式列表
        
        Returns:
            List[SequenceFormat]: 支持的格式列表
        """
        return list(self.parsers.keys())
