"""
CSV格式序列解析器

解析CSV格式的序列文件，生成标准化的序列记录。
"""

import csv
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

from .base import BaseSequenceParser, ParsingError
from ...models.sequence_record import (
    SequenceRecord,
    SequenceData,
    SequenceComposition,
    SequenceSource,
    SequenceAnnotations,
    SequenceValidation
)
from ...models.processing_models import ValidationResult
from ...models.format_models import SequenceFormat


class CsvParser(BaseSequenceParser):
    """CSV格式序列解析器"""
    
    def __init__(self):
        """初始化CSV解析器"""
        super().__init__(SequenceFormat.CSV)
        
        # 预定义的列名映射
        self.column_mappings = {
            # 序列ID相关
            'sequence_id': ['sequenceID', 'sequence_id', 'seq_id', 'id', 'name', 'identifier'],
            'sequence_name': ['sequence_name', 'name', 'gene_name', 'protein_name'],
            'description': ['description', 'desc', 'comment', 'annotation'],
            
            # 序列数据相关
            'sequence': ['sequence', 'seq', 'protein_sequence', 'dna_sequence', 'amino_acids'],
            'length': ['length', 'len', 'sequence_length', 'size'],
            'molecular_type': ['mol_type', 'molecular_type', 'type', 'molecule_type'],
            
            # 注释相关
            'organism': ['organism', 'species', 'source_organism'],
            'gene_name': ['gene_name', 'gene', 'gene_symbol'],
            'function': ['function', 'product', 'protein_function'],
        }
    
    def parse(self, file_path: Path) -> List[SequenceRecord]:
        """
        解析CSV文件
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            List[SequenceRecord]: 解析出的序列记录列表
            
        Raises:
            ParsingError: 解析错误
            FileNotFoundError: 文件不存在
        """
        self._validate_file(file_path)
        
        # 检测分隔符
        delimiter = self._detect_delimiter(file_path)
        
        sequences = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                # 验证并映射列名
                if reader.fieldnames is None:
                    raise ParsingError("CSV文件没有列头")
                column_mapping = self._map_columns(reader.fieldnames)
                
                # 验证必需列
                self._validate_required_columns(column_mapping)
                
                for row_number, row in enumerate(reader, 2):  # 从第2行开始（第1行是头部）
                    try:
                        sequence_record = self._create_sequence_record_from_row(
                            row, column_mapping, file_path, row_number
                        )
                        sequences.append(sequence_record)
                    except Exception as e:
                        raise ParsingError(
                            f"处理第{row_number}行数据时出错: {e}",
                            row_number,
                            {"row_data": row, "original_error": str(e)}
                        )
        
        except UnicodeDecodeError as e:
            raise ParsingError(
                f"文件编码错误: {e}",
                context={"encoding_error": str(e)}
            )
        except csv.Error as e:
            raise ParsingError(
                f"CSV格式错误: {e}",
                context={"csv_error": str(e)}
            )
        except Exception as e:
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(
                f"解析过程中发生错误: {e}",
                context={"original_error": str(e)}
            )
        
        if not sequences:
            raise ParsingError("CSV文件中未找到任何有效的序列记录")
        
        self.logger.info(f"成功解析CSV文件 {file_path}，共{len(sequences)}个序列")
        return sequences
    
    def _detect_delimiter(self, file_path: Path) -> str:
        """
        自动检测CSV分隔符
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 检测到的分隔符
        """
        possible_delimiters = [',', '\t', ';', '|']
        
        with open(file_path, 'r', encoding='utf-8') as f:
            # 读取前几行进行分析
            sample_lines = [f.readline().strip() for _ in range(min(5, sum(1 for _ in f)))]
            f.seek(0)
            sample_lines.extend([f.readline().strip() for _ in range(min(5, len(sample_lines)))])
        
        delimiter_scores = {}
        
        for delimiter in possible_delimiters:
            try:
                # 尝试解析样本
                reader = csv.reader(sample_lines, delimiter=delimiter)
                rows = list(reader)
                
                if len(rows) < 2:
                    delimiter_scores[delimiter] = 0
                    continue
                
                # 检查列数一致性
                header_cols = len(rows[0])
                if header_cols < 2:
                    delimiter_scores[delimiter] = 0
                    continue
                
                consistency = sum(1 for row in rows[1:] if len(row) == header_cols) / len(rows[1:])
                
                # 检查是否有序列相关的列名
                header_text = ' '.join(rows[0]).lower()
                has_sequence_keywords = any(
                    keyword in header_text 
                    for keyword in ['sequence', 'seq', 'protein', 'dna', 'rna', 'id']
                )
                
                score = consistency * 0.7
                if has_sequence_keywords:
                    score += 0.3
                
                delimiter_scores[delimiter] = score
                
            except Exception:
                delimiter_scores[delimiter] = 0
        
        # 选择得分最高的分隔符
        best_delimiter = max(delimiter_scores.items(), key=lambda x: x[1])
        
        if best_delimiter[1] < 0.5:
            # 如果所有分隔符得分都很低，使用文件扩展名推断
            if file_path.suffix.lower() == '.tsv':
                return '\t'
            else:
                return ','
        
        return best_delimiter[0]
    
    def _map_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """
        映射CSV列名到标准字段
        
        Args:
            fieldnames: CSV文件的列名列表
            
        Returns:
            Dict[str, str]: 映射字典 {标准字段名: 实际列名}
        """
        if not fieldnames:
            raise ParsingError("CSV文件没有列头")
        
        column_mapping = {}
        fieldnames_lower = [name.lower().strip() for name in fieldnames]
        
        for standard_field, possible_names in self.column_mappings.items():
            for possible_name in possible_names:
                if possible_name.lower() in fieldnames_lower:
                    original_index = fieldnames_lower.index(possible_name.lower())
                    column_mapping[standard_field] = fieldnames[original_index]
                    break
        
        self.logger.debug(f"列名映射结果: {column_mapping}")
        return column_mapping
    
    def _validate_required_columns(self, column_mapping: Dict[str, str]) -> None:
        """
        验证必需的列是否存在
        
        Args:
            column_mapping: 列名映射
            
        Raises:
            ParsingError: 缺少必需列
        """
        required_fields = ['sequence']  # 至少需要序列列
        recommended_fields = ['sequence_id']  # 推荐但不强制
        
        missing_required = [field for field in required_fields if field not in column_mapping]
        missing_recommended = [field for field in recommended_fields if field not in column_mapping]
        
        if missing_required:
            raise ParsingError(
                f"CSV文件缺少必需的列: {missing_required}。"
                f"可用列: {list(column_mapping.values())}"
            )
        
        if missing_recommended:
            self.logger.warning(f"CSV文件缺少推荐的列: {missing_recommended}")
    
    def _create_sequence_record_from_row(self, row: Dict[str, str],
                                       column_mapping: Dict[str, str],
                                       file_path: Path,
                                       row_number: int) -> SequenceRecord:
        """
        从CSV行创建序列记录
        
        Args:
            row: CSV行数据
            column_mapping: 列名映射
            file_path: 文件路径
            row_number: 行号
            
        Returns:
            SequenceRecord: 序列记录
        """
        # 提取基本信息
        sequence_id = self._get_field_value(row, column_mapping, 'sequence_id') or f"seq_{row_number-1}"
        sequence_name = self._get_field_value(row, column_mapping, 'sequence_name') or sequence_id
        description = self._get_field_value(row, column_mapping, 'description') or ""
        
        # 提取序列数据
        raw_sequence = self._get_field_value(row, column_mapping, 'sequence')
        if not raw_sequence:
            raise ParsingError(f"序列 {sequence_id} 的序列数据为空")
        
        cleaned_sequence = self._clean_sequence(raw_sequence)
        if not cleaned_sequence:
            raise ParsingError(f"序列 {sequence_id} 清理后为空")
        
        # 分子类型
        molecular_type = self._get_field_value(row, column_mapping, 'molecular_type')
        if molecular_type:
            # 标准化分子类型
            molecular_type = self._normalize_molecular_type(molecular_type)
        else:
            # 自动检测
            molecular_type = self._detect_molecular_type(cleaned_sequence)
        
        # 长度信息
        length_str = self._get_field_value(row, column_mapping, 'length')
        expected_length = int(length_str) if length_str and length_str.isdigit() else None
        actual_length = len(cleaned_sequence)
        
        # 验证长度一致性
        if expected_length is not None and expected_length != actual_length:
            self.logger.warning(
                f"序列 {sequence_id} 长度不一致: 声明={expected_length}, 实际={actual_length}"
            )
        
        # 计算序列组成
        composition_dict = self._calculate_composition(cleaned_sequence)
        composition = SequenceComposition(
            composition=composition_dict,
            total_residues=actual_length,
            most_frequent=max(composition_dict.items(), key=lambda x: x[1])[0],
            least_frequent=min(composition_dict.items(), key=lambda x: x[1])[0]
        )
        
        # 生成校验和
        checksum = hashlib.sha256(cleaned_sequence.encode()).hexdigest()[:16]
        
        # 创建序列数据
        sequence_data = SequenceData(
            raw_sequence=raw_sequence,
            cleaned_sequence=cleaned_sequence,
            length=actual_length,
            molecular_type=molecular_type,
            checksum=checksum,
            composition=composition
        )
        
        # 创建来源信息
        source = SequenceSource(
            file_path=str(file_path),
            file_format="csv",
            line_start=row_number,
            line_end=row_number
        )
        
        # 创建注释信息
        annotations = SequenceAnnotations(
            organism=self._get_field_value(row, column_mapping, 'organism') or "",
            gene_name=self._get_field_value(row, column_mapping, 'gene_name') or "",
            function=self._get_field_value(row, column_mapping, 'function') or ""
        )
        
        # 添加所有CSV字段到自定义注释中
        csv_data = {k: v for k, v in row.items() if v and k not in column_mapping.values()}
        if csv_data:
            annotations.custom_annotations['csv_extra_fields'] = csv_data
        
        # 验证序列
        sequence_errors = self._validate_sequence_characters(cleaned_sequence, molecular_type)
        
        validation = SequenceValidation(
            is_valid=len(sequence_errors) == 0,
            errors=sequence_errors
        )
        
        # 创建序列记录
        sequence_record = SequenceRecord(
            sequence_id=sequence_id,
            sequence_name=sequence_name,
            description=description,
            source=source,
            sequence_data=sequence_data,
            annotations=annotations,
            validation=validation
        )
        
        return sequence_record
    
    def _get_field_value(self, row: Dict[str, str], 
                        column_mapping: Dict[str, str],
                        field_name: str) -> Optional[str]:
        """
        从行数据中获取字段值
        
        Args:
            row: 行数据
            column_mapping: 列名映射
            field_name: 字段名
            
        Returns:
            Optional[str]: 字段值
        """
        if field_name in column_mapping:
            column_name = column_mapping[field_name]
            value = row.get(column_name, "").strip()
            return value if value else None
        return None
    
    def _normalize_molecular_type(self, mol_type: str) -> str:
        """
        标准化分子类型
        
        Args:
            mol_type: 原始分子类型字符串
            
        Returns:
            str: 标准化的分子类型
        """
        mol_type_lower = mol_type.lower().strip()
        
        # 映射表
        type_mapping = {
            'aa': 'protein',
            'amino_acid': 'protein',
            'protein': 'protein',
            'peptide': 'protein',
            'dna': 'dna',
            'nucleotide': 'dna',
            'rna': 'rna',
            'mrna': 'rna',
            'cdna': 'dna'
        }
        
        return type_mapping.get(mol_type_lower, 'unknown')
    
    def validate(self, sequences: List[SequenceRecord]) -> ValidationResult:
        """
        验证CSV解析结果
        
        Args:
            sequences: 序列记录列表
            
        Returns:
            ValidationResult: 验证结果
        """
        # 获取基础验证结果
        result = self._create_basic_validation_result(sequences)
        
        # CSV特定验证
        csv_errors = []
        csv_warnings = []
        
        # 检查数据完整性
        for i, seq in enumerate(sequences):
            # 检查序列ID的唯一性（这在基础验证中已有，但我们可以加强）
            if not seq.sequence_id or seq.sequence_id.startswith('seq_'):
                csv_warnings.append(
                    f"序列{i+1}使用了自动生成的ID: {seq.sequence_id}"
                )
            
            # 检查分子类型一致性
            if seq.sequence_data.molecular_type == 'unknown':
                csv_warnings.append(
                    f"序列{i+1} ({seq.sequence_id}) 的分子类型未能确定"
                )
        
        # 检查数据质量
        if sequences:
            # 检查序列长度分布
            lengths = [seq.sequence_data.length for seq in sequences]
            avg_length = sum(lengths) / len(lengths)
            
            extremely_short = [seq for seq in sequences if seq.sequence_data.length < avg_length * 0.1]
            extremely_long = [seq for seq in sequences if seq.sequence_data.length > avg_length * 10]
            
            if extremely_short:
                csv_warnings.append(
                    f"发现{len(extremely_short)}个异常短的序列（少于平均长度的10%）"
                )
            
            if extremely_long:
                csv_warnings.append(
                    f"发现{len(extremely_long)}个异常长的序列（超过平均长度的10倍）"
                )
        
        # 合并验证结果
        result.errors.extend(csv_errors)
        result.warnings.extend(csv_warnings)
        result.total_errors = len(result.errors)
        result.total_warnings = len(result.warnings)
        result.is_valid = result.total_errors == 0
        
        return result
