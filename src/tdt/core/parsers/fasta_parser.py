"""
FASTA格式序列解析器

解析FASTA格式的序列文件，生成标准化的序列记录。
"""

import hashlib
import re
from pathlib import Path
from typing import List, Tuple

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


class FastaParser(BaseSequenceParser):
    """FASTA格式序列解析器"""
    
    def __init__(self):
        """初始化FASTA解析器"""
        super().__init__(SequenceFormat.FASTA)
    
    def parse(self, file_path: Path) -> List[SequenceRecord]:
        """
        解析FASTA文件
        
        Args:
            file_path: FASTA文件路径
            
        Returns:
            List[SequenceRecord]: 解析出的序列记录列表
            
        Raises:
            ParsingError: 解析错误
            FileNotFoundError: 文件不存在
        """
        self._validate_file(file_path)
        
        sequences = []
        current_header = None
        current_sequence_lines = []
        line_number = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # 跳过空行
                    if not line:
                        continue
                    
                    # 处理头部行
                    if line.startswith('>'):
                        # 如果已经有序列数据，先处理之前的序列
                        if current_header is not None:
                            sequence_record = self._create_sequence_record(
                                current_header,
                                current_sequence_lines,
                                file_path,
                                len(sequences)
                            )
                            sequences.append(sequence_record)
                        
                        # 开始新序列
                        current_header = line
                        current_sequence_lines = []
                    
                    # 处理序列行
                    else:
                        if current_header is None:
                            raise ParsingError(
                                "序列数据出现在头部行之前",
                                line_number,
                                {"line": line}
                            )
                        current_sequence_lines.append(line)
                
                # 处理最后一个序列
                if current_header is not None:
                    sequence_record = self._create_sequence_record(
                        current_header,
                        current_sequence_lines,
                        file_path,
                        len(sequences)
                    )
                    sequences.append(sequence_record)
        
        except UnicodeDecodeError as e:
            raise ParsingError(
                f"文件编码错误: {e}",
                line_number,
                {"encoding_error": str(e)}
            )
        except Exception as e:
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(
                f"解析过程中发生错误: {e}",
                line_number,
                {"original_error": str(e)}
            )
        
        if not sequences:
            raise ParsingError("文件中未找到任何有效的FASTA序列")
        
        self.logger.info(f"成功解析FASTA文件 {file_path}，共{len(sequences)}个序列")
        return sequences
    
    def _create_sequence_record(self, header_line: str, 
                              sequence_lines: List[str],
                              file_path: Path,
                              sequence_index: int) -> SequenceRecord:
        """
        创建序列记录
        
        Args:
            header_line: 头部行
            sequence_lines: 序列行列表
            file_path: 文件路径
            sequence_index: 序列索引
            
        Returns:
            SequenceRecord: 序列记录
        """
        # 解析头部信息
        sequence_id, name, description, annotations = self._parse_header(header_line)
        
        # 合并序列行
        raw_sequence = ''.join(sequence_lines)
        cleaned_sequence = self._clean_sequence(raw_sequence)
        
        if not cleaned_sequence:
            raise ParsingError(
                f"序列 {sequence_id} 的序列数据为空",
                context={"sequence_id": sequence_id}
            )
        
        # 检测分子类型
        molecular_type = self._detect_molecular_type(cleaned_sequence)
        
        # 计算序列组成
        composition_dict = self._calculate_composition(cleaned_sequence)
        composition = SequenceComposition(
            composition=composition_dict,
            total_residues=len(cleaned_sequence),
            most_frequent=max(composition_dict.items(), key=lambda x: x[1])[0],
            least_frequent=min(composition_dict.items(), key=lambda x: x[1])[0]
        )
        
        # 生成校验和
        checksum = hashlib.sha256(cleaned_sequence.encode()).hexdigest()[:16]
        
        # 创建序列数据
        sequence_data = SequenceData(
            raw_sequence=raw_sequence,
            cleaned_sequence=cleaned_sequence,
            length=len(cleaned_sequence),
            molecular_type=molecular_type,
            checksum=checksum,
            composition=composition
        )
        
        # 创建来源信息
        source = SequenceSource(
            file_path=str(file_path),
            file_format="fasta",
            original_header=header_line
        )
        
        # 验证序列
        sequence_errors = self._validate_sequence_characters(
            cleaned_sequence, molecular_type
        )
        
        validation = SequenceValidation(
            is_valid=len(sequence_errors) == 0,
            errors=sequence_errors
        )
        
        # 创建序列记录
        sequence_record = SequenceRecord(
            sequence_id=sequence_id,
            sequence_name=name,
            description=description,
            source=source,
            sequence_data=sequence_data,
            annotations=annotations,
            validation=validation
        )
        
        return sequence_record
    
    def _parse_header(self, header_line: str) -> Tuple[str, str, str, SequenceAnnotations]:
        """
        解析FASTA头部行
        
        Args:
            header_line: 头部行（包含>符号）
            
        Returns:
            Tuple: (序列ID, 名称, 描述, 注释信息)
        """
        # 移除开头的>符号
        header_content = header_line[1:].strip()
        
        if not header_content:
            raise ParsingError("FASTA头部行为空")
        
        # 分割ID和描述
        parts = header_content.split(None, 1)
        sequence_id = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        
        # 提取名称（通常与ID相同，除非有特殊格式）
        sequence_name = sequence_id
        
        # 解析特殊格式的头部（如GenBank格式）
        annotations = self._parse_special_header_formats(header_content)
        
        # 从描述中提取关键词
        keywords = self._extract_keywords_from_description(description)
        annotations.keywords.extend(keywords)
        
        return sequence_id, sequence_name, description, annotations
    
    def _parse_special_header_formats(self, header_content: str) -> SequenceAnnotations:
        """
        解析特殊格式的FASTA头部
        
        Args:
            header_content: 头部内容（不含>符号）
            
        Returns:
            SequenceAnnotations: 注释信息
        """
        annotations = SequenceAnnotations()
        
        # GenBank格式: gi|123456|ref|NP_123456.1| protein description
        genbank_pattern = r'gi\|(\d+)\|([^|]+)\|([^|]+)\|'
        genbank_match = re.match(genbank_pattern, header_content)
        
        if genbank_match:
            gi_number = genbank_match.group(1)
            db_type = genbank_match.group(2)
            accession = genbank_match.group(3)
            
            annotations.custom_annotations.update({
                'gi_number': gi_number,
                'database_type': db_type,
                'accession': accession,
                'header_format': 'genbank'
            })
        
        # UniProt格式: sp|P12345|PROT_HUMAN Protein description OS=Homo sapiens
        uniprot_pattern = r'([a-z]+)\|([^|]+)\|([^|]+)'
        uniprot_match = re.match(uniprot_pattern, header_content)
        
        if uniprot_match:
            db_code = uniprot_match.group(1)
            accession = uniprot_match.group(2)
            entry_name = uniprot_match.group(3)
            
            annotations.custom_annotations.update({
                'database_code': db_code,
                'accession': accession,
                'entry_name': entry_name,
                'header_format': 'uniprot'
            })
            
            # 提取生物名称
            organism_match = re.search(r'OS=([^=]+?)(?:\s+[A-Z]{2}=|$)', header_content)
            if organism_match:
                annotations.organism = organism_match.group(1).strip()
        
        # 检测常见的标签
        tags = []
        tag_patterns = {
            'His-tag': r'his',
            'GST-tag': r'gst',
            'FLAG-tag': r'flag',
            'Strep-tag': r'strep'
        }
        
        header_lower = header_content.lower()
        for tag_name, pattern in tag_patterns.items():
            if re.search(pattern, header_lower):
                tags.append(tag_name)
        
        annotations.tags = tags
        
        return annotations
    
    def _extract_keywords_from_description(self, description: str) -> List[str]:
        """
        从描述中提取关键词
        
        Args:
            description: 序列描述
            
        Returns:
            List[str]: 关键词列表
        """
        if not description:
            return []
        
        keywords = []
        
        # 生物学关键词
        bio_keywords = [
            'enzyme', 'protein', 'kinase', 'phosphatase', 'transferase',
            'oxidase', 'reductase', 'dehydrogenase', 'synthase',
            'receptor', 'channel', 'transporter', 'binding',
            'domain', 'motif', 'region', 'terminus'
        ]
        
        description_lower = description.lower()
        for keyword in bio_keywords:
            if keyword in description_lower:
                keywords.append(keyword)
        
        return keywords
    
    def validate(self, sequences: List[SequenceRecord]) -> ValidationResult:
        """
        验证FASTA解析结果
        
        Args:
            sequences: 序列记录列表
            
        Returns:
            ValidationResult: 验证结果
        """
        # 获取基础验证结果
        result = self._create_basic_validation_result(sequences)
        
        # FASTA特定验证
        fasta_errors = []
        fasta_warnings = []
        
        for i, seq in enumerate(sequences):
            # 检查序列ID格式
            if not seq.sequence_id or len(seq.sequence_id.strip()) == 0:
                fasta_errors.append(f"序列{i+1}的ID为空")
            
            # 检查序列字符
            cleaned_seq = seq.sequence_data.cleaned_sequence
            if re.search(r'[^A-Za-z\-\*]', cleaned_seq):
                fasta_warnings.append(
                    f"序列{i+1} ({seq.sequence_id}) 包含非标准字符"
                )
            
            # 检查序列长度合理性
            if seq.sequence_data.length > 50000:
                fasta_warnings.append(
                    f"序列{i+1} ({seq.sequence_id}) 长度异常大: {seq.sequence_data.length}"
                )
        
        # 合并验证结果
        result.errors.extend(fasta_errors)
        result.warnings.extend(fasta_warnings)
        result.total_errors = len(result.errors)
        result.total_warnings = len(result.warnings)
        result.is_valid = result.total_errors == 0
        
        return result
