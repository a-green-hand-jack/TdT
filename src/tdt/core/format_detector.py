"""
序列格式自动检测器

能够自动识别FASTA、CSV、JSON等序列文件格式。
"""

import csv
import json
import logging
import re
from pathlib import Path
from typing import Dict, TextIO

from ..models.format_models import (
    SequenceFormat, 
    FormatDetectionResult,
    FORMAT_SPECIFICATIONS
)

logger = logging.getLogger(__name__)


class SequenceFormatDetector:
    """序列格式自动检测器"""
    
    def __init__(self):
        """初始化检测器"""
        self.format_specs = FORMAT_SPECIFICATIONS
    
    def detect_format(self, file_path: Path) -> FormatDetectionResult:
        """
        自动检测序列文件格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            FormatDetectionResult: 检测结果
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"路径不是文件: {file_path}")
        
        # 获取基本文件信息
        file_size = file_path.stat().st_size
        file_extension = file_path.suffix.lower().lstrip('.')
        
        # 计算各格式的置信度
        confidence_scores = {}
        format_specific_info = {}
        
        try:
            # 读取文件内容进行分析
            with open(file_path, 'r', encoding='utf-8') as f:
                # 检测FASTA格式
                fasta_score, fasta_info = self._detect_fasta(f)
                confidence_scores[SequenceFormat.FASTA] = fasta_score
                format_specific_info['fasta'] = fasta_info
                
                # 重置文件指针
                f.seek(0)
                
                # 检测CSV格式
                csv_score, csv_info = self._detect_csv(f)
                confidence_scores[SequenceFormat.CSV] = csv_score
                format_specific_info['csv'] = csv_info
                
                # 重置文件指针
                f.seek(0)
                
                # 检测JSON格式
                json_score, json_info = self._detect_json(f)
                confidence_scores[SequenceFormat.JSON] = json_score
                format_specific_info['json'] = json_info
                
        except Exception as e:
            logger.warning(f"读取文件时出错 {file_path}: {e}")
            confidence_scores = {format_type: 0.0 for format_type in SequenceFormat}
        
        # 根据文件扩展名调整置信度
        self._adjust_scores_by_extension(confidence_scores, file_extension)
        
        # 确定最终格式
        detected_format = max(confidence_scores.items(), key=lambda x: x[1])[0]
        
        return FormatDetectionResult(
            file_path=str(file_path),
            detected_format=detected_format,
            confidence_scores=confidence_scores,
            detection_method="multi_criteria_analysis",
            file_extension=file_extension,
            file_size_bytes=file_size,
            format_specific_info=format_specific_info
        )
    
    def _detect_fasta(self, file_handle: TextIO) -> tuple[float, Dict]:
        """
        检测FASTA格式
        
        Args:
            file_handle: 文件句柄
            
        Returns:
            tuple: (置信度评分, 格式特定信息)
        """
        try:
            lines = [line.strip() for line in file_handle.readlines() if line.strip()]
            
            if not lines:
                return 0.0, {"error": "文件为空"}
            
            header_count = 0
            sequence_count = 0
            total_lines = len(lines)
            
            # 分析每一行
            for line in lines:
                if line.startswith('>'):
                    header_count += 1
                elif re.match(r'^[A-Za-z\-\*\s]+$', line):
                    sequence_count += 1
            
            # 计算置信度
            score = 0.0
            info = {
                "header_lines": header_count,
                "sequence_lines": sequence_count,
                "total_lines": total_lines
            }
            
            # 必须有至少一个头部行
            if header_count > 0:
                score += 0.4
            
            # 序列行与头部行的比例合理
            if header_count > 0 and sequence_count > 0:
                ratio = sequence_count / header_count
                if 1 <= ratio <= 50:  # 合理的序列行/头部行比例
                    score += 0.3
            
            # 头部行符合FASTA格式
            if header_count > 0:
                valid_headers = sum(
                    1 for line in lines 
                    if line.startswith('>') and len(line) > 1
                )
                header_validity = valid_headers / header_count
                score += 0.3 * header_validity
            
            return min(score, 1.0), info
            
        except Exception as e:
            return 0.0, {"error": str(e)}
    
    def _detect_csv(self, file_handle: TextIO) -> tuple[float, Dict]:
        """
        检测CSV格式
        
        Args:
            file_handle: 文件句柄
            
        Returns:
            tuple: (置信度评分, 格式特定信息)
        """
        try:
            # 尝试用不同分隔符解析
            content = file_handle.read()
            if not content.strip():
                return 0.0, {"error": "文件为空"}
            
            lines = content.strip().split('\n')
            if len(lines) < 2:
                return 0.0, {"error": "行数太少"}
            
            # 检测分隔符
            delimiters = [',', '\t', ';', '|']
            best_delimiter = None
            best_score = 0.0
            delimiter_info = {}
            
            for delimiter in delimiters:
                try:
                    # 重置内容并尝试解析
                    reader = csv.reader(content.splitlines(), delimiter=delimiter)
                    rows = list(reader)
                    
                    if len(rows) < 2:
                        continue
                    
                    header = rows[0]
                    data_rows = rows[1:]
                    
                    # 检查列数一致性
                    col_counts = [len(row) for row in data_rows]
                    if not col_counts:
                        continue
                    
                    consistency = sum(1 for c in col_counts if c == len(header)) / len(col_counts)
                    
                    # 检查是否有序列相关的列
                    header_lower = [h.lower() for h in header]
                    has_sequence_col = any(
                        keyword in ' '.join(header_lower) 
                        for keyword in ['sequence', 'seq', 'protein', 'dna', 'rna']
                    )
                    
                    has_id_col = any(
                        keyword in ' '.join(header_lower)
                        for keyword in ['id', 'name', 'identifier']
                    )
                    
                    # 计算该分隔符的评分
                    score = 0.0
                    if consistency > 0.8:
                        score += 0.4
                    if has_sequence_col:
                        score += 0.3
                    if has_id_col:
                        score += 0.2
                    if len(header) >= 2:
                        score += 0.1
                    
                    delimiter_info[delimiter] = {
                        "score": score,
                        "consistency": consistency,
                        "columns": len(header),
                        "rows": len(data_rows),
                        "has_sequence_col": has_sequence_col,
                        "has_id_col": has_id_col
                    }
                    
                    if score > best_score:
                        best_score = score
                        best_delimiter = delimiter
                        
                except Exception as e:
                    delimiter_info[delimiter] = {"error": str(e)}
            
            info = {
                "best_delimiter": best_delimiter,
                "delimiter_analysis": delimiter_info
            }
            
            return best_score, info
            
        except Exception as e:
            return 0.0, {"error": str(e)}
    
    def _detect_json(self, file_handle: TextIO) -> tuple[float, Dict]:
        """
        检测JSON格式
        
        Args:
            file_handle: 文件句柄
            
        Returns:
            tuple: (置信度评分, 格式特定信息)
        """
        try:
            content = file_handle.read()
            if not content.strip():
                return 0.0, {"error": "文件为空"}
            
            # 尝试解析JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                return 0.0, {"error": f"JSON解析失败: {e}"}
            
            score = 0.5  # 基础分，能解析JSON
            info = {
                "is_valid_json": True,
                "data_type": type(data).__name__
            }
            
            if isinstance(data, dict):
                # 检查是否有序列相关的键
                keys = list(data.keys())
                info["top_level_keys"] = keys
                
                if "sequences" in keys:
                    score += 0.3
                    info["has_sequences_key"] = True
                
                if "metadata" in keys:
                    score += 0.1
                    info["has_metadata_key"] = True
                
                if "statistics" in keys:
                    score += 0.1
                    info["has_statistics_key"] = True
                
            elif isinstance(data, list):
                # 检查列表中是否包含序列对象
                if data and isinstance(data[0], dict):
                    first_item_keys = list(data[0].keys())
                    info["first_item_keys"] = first_item_keys
                    
                    sequence_related = any(
                        keyword in ' '.join(first_item_keys).lower()
                        for keyword in ['sequence', 'seq', 'id', 'name']
                    )
                    
                    if sequence_related:
                        score += 0.2
                        info["appears_to_be_sequence_list"] = True
            
            return min(score, 1.0), info
            
        except Exception as e:
            return 0.0, {"error": str(e)}
    
    def _adjust_scores_by_extension(self, scores: Dict[SequenceFormat, float], 
                                  extension: str) -> None:
        """
        根据文件扩展名调整置信度评分
        
        Args:
            scores: 当前评分字典
            extension: 文件扩展名
        """
        extension_mapping = {
            'fasta': SequenceFormat.FASTA,
            'fas': SequenceFormat.FASTA,
            'fa': SequenceFormat.FASTA,
            'seq': SequenceFormat.FASTA,
            'csv': SequenceFormat.CSV,
            'tsv': SequenceFormat.CSV,
            'json': SequenceFormat.JSON
        }
        
        if extension in extension_mapping:
            format_type = extension_mapping[extension]
            # 扩展名匹配时增加置信度
            scores[format_type] = min(scores[format_type] + 0.2, 1.0)
    
    def validate_format(self, file_path: Path, 
                       expected_format: SequenceFormat) -> bool:
        """
        验证文件格式是否符合预期
        
        Args:
            file_path: 文件路径
            expected_format: 预期格式
            
        Returns:
            bool: 是否符合预期格式
        """
        try:
            detection_result = self.detect_format(file_path)
            return (detection_result.detected_format == expected_format and 
                   detection_result.is_confident())
        except Exception as e:
            logger.error(f"格式验证失败 {file_path}: {e}")
            return False
    
    def get_format_confidence(self, file_path: Path) -> Dict[SequenceFormat, float]:
        """
        获取各种格式的置信度评分
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 格式置信度字典
        """
        try:
            detection_result = self.detect_format(file_path)
            return detection_result.confidence_scores
        except Exception as e:
            logger.error(f"获取格式置信度失败 {file_path}: {e}")
            return {format_type: 0.0 for format_type in SequenceFormat}
