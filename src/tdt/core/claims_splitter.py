"""
权利要求书智能分段器

该模块实现了智能分段处理架构的核心组件，用于将复杂的权利要求书
分解为可管理的段落，以便LLM进行详细分析。
"""
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClaimSegment:
    """权利要求段落数据结构"""
    claim_number: int
    claim_text: str
    claim_type: str  # "independent" or "dependent"
    references: List[int]  # 引用的其他权利要求编号
    seq_id_references: List[str]  # 引用的SEQ ID NO
    mutation_positions: List[str]  # 突变位点
    complexity_score: float  # 复杂度评分


class ClaimsSplitter:
    """权利要求书智能分段器"""
    
    def __init__(self):
        self.logger = logger
    
    def split_claims(self, claims_text: str) -> List[ClaimSegment]:
        """
        将权利要求书分解为独立的权利要求段落
        
        Args:
            claims_text: 完整的权利要求书文本
            
        Returns:
            List[ClaimSegment]: 分段后的权利要求列表
        """
        self.logger.info("开始智能分段权利要求书")
        
        # 1. 清理和预处理文本
        cleaned_text = self._preprocess_text(claims_text)
        
        # 2. 识别权利要求边界
        claim_boundaries = self._identify_claim_boundaries(cleaned_text)
        
        # 3. 提取各个权利要求
        segments = []
        for i, (start, end) in enumerate(claim_boundaries):
            claim_text = cleaned_text[start:end].strip()
            if claim_text:
                segment = self._parse_single_claim(i + 1, claim_text)
                if segment:
                    segments.append(segment)
        
        self.logger.info(f"成功分段: {len(segments)}个权利要求")
        return segments
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本，清理格式并标准化"""
        # 移除文档信息部分
        if "---" in text:
            parts = text.split("---")
            if len(parts) > 1:
                text = parts[-1]  # 取最后一部分（实际权利要求内容）
        
        # 标准化空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 移除文档生成信息
        text = re.sub(r'\*此文档由.*?自动生成\*', '', text)
        
        return text.strip()
    
    def _identify_claim_boundaries(self, text: str) -> List[tuple]:
        """识别权利要求的边界位置"""
        boundaries = []
        
        # 使用正则表达式查找权利要求编号模式
        # 匹配 "数字. " 格式，例如 "1. " "2. " 等
        pattern = r'(\d+)\.\s+'
        matches = list(re.finditer(pattern, text))
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            # 下一个权利要求的开始位置作为当前权利要求的结束位置
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            boundaries.append((start_pos, end_pos))
        
        return boundaries
    
    def _parse_single_claim(self, claim_number: int, claim_text: str) -> Optional[ClaimSegment]:
        """解析单个权利要求"""
        try:
            # 提取权利要求类型（独立或从属）
            claim_type = self._determine_claim_type(claim_text)
            
            # 提取引用的其他权利要求
            references = self._extract_claim_references(claim_text)
            
            # 提取SEQ ID NO引用
            seq_id_references = self._extract_seq_id_references(claim_text)
            
            # 提取突变位点
            mutation_positions = self._extract_mutation_positions(claim_text)
            
            # 计算复杂度评分
            complexity_score = self._calculate_complexity_score(
                claim_text, seq_id_references, mutation_positions
            )
            
            return ClaimSegment(
                claim_number=claim_number,
                claim_text=claim_text,
                claim_type=claim_type,
                references=references,
                seq_id_references=seq_id_references,
                mutation_positions=mutation_positions,
                complexity_score=complexity_score
            )
        
        except Exception as e:
            self.logger.warning(f"解析权利要求{claim_number}失败: {e}")
            return None
    
    def _determine_claim_type(self, claim_text: str) -> str:
        """确定权利要求类型"""
        # 检查是否引用了其他权利要求
        if re.search(r'根据权利要求\d+', claim_text):
            return "dependent"
        else:
            return "independent"
    
    def _extract_claim_references(self, claim_text: str) -> List[int]:
        """提取引用的其他权利要求编号"""
        references = []
        # 匹配 "根据权利要求X" 或 "权利要求X-Y"
        patterns = [
            r'根据权利要求(\d+)',
            r'权利要求(\d+)[‑-](\d+)',
            r'权利要求(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, claim_text)
            for match in matches:
                if isinstance(match, tuple):
                    # 处理范围引用，如 "权利要求1-5"
                    start, end = map(int, match)
                    references.extend(range(start, end + 1))
                else:
                    references.append(int(match))
        
        return sorted(list(set(references)))
    
    def _extract_seq_id_references(self, claim_text: str) -> List[str]:
        """提取SEQ ID NO引用"""
        seq_ids = []
        
        # 匹配各种SEQ ID格式
        patterns = [
            r'SEQ\s+ID\s+NO[:\s]*(\d+)',
            r'SEQ\s+ID\s+NO[:\s]*(\d+[‑\-]\d+)',  # 范围格式
            r'SEQ\s+ID\s+NO[:\s]*(\d+(?:[、，,]\s*\d+)*)',  # 列表格式
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, claim_text, re.IGNORECASE)
            for match in matches:
                if '‑' in match or '-' in match:
                    # 处理范围
                    parts = re.split('[‑-]', match)
                    if len(parts) == 2:
                        start, end = int(parts[0]), int(parts[1])
                        seq_ids.extend([str(i) for i in range(start, end + 1)])
                elif any(sep in match for sep in ['、', '，', ',']):
                    # 处理列表
                    parts = re.split('[、，,]', match)
                    seq_ids.extend([part.strip() for part in parts if part.strip().isdigit()])
                else:
                    seq_ids.append(match)
        
        return sorted(list(set(seq_ids)))
    
    def _extract_mutation_positions(self, claim_text: str) -> List[str]:
        """提取突变位点信息"""
        mutations = []
        
        # 匹配各种突变位点格式
        patterns = [
            r'(\d+(?:/\d+)*)',  # 位置列表，如 "20/21/68"
            r'([A-Z]\d+[A-Z])',  # 标准突变格式，如 "Y178A"
            r'位置(\d+)',  # 中文描述的位置
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, claim_text)
            mutations.extend(matches)
        
        return sorted(list(set(mutations)))
    
    def _calculate_complexity_score(self, claim_text: str, 
                                  seq_id_refs: List[str], 
                                  mutations: List[str]) -> float:
        """计算权利要求的复杂度评分"""
        score = 0.0
        
        # 基础分数
        score += 1.0
        
        # 文本长度因子
        score += min(len(claim_text) / 500, 3.0)
        
        # SEQ ID引用数量因子
        score += len(seq_id_refs) * 0.1
        
        # 突变位点数量因子
        score += len(mutations) * 0.2
        
        # 逻辑复杂度因子（检查AND/OR等逻辑词）
        logic_words = ['和/或', '和', '或', '以及', '任何组合']
        for word in logic_words:
            score += claim_text.count(word) * 0.1
        
        # 百分比阈值因子
        percentage_matches = re.findall(r'(\d+)％', claim_text)
        score += len(percentage_matches) * 0.1
        
        return min(score, 10.0)  # 限制最大评分为10
    
    def group_claims_by_complexity(self, segments: List[ClaimSegment]) -> Dict[str, List[ClaimSegment]]:
        """按复杂度对权利要求分组"""
        groups = {
            "simple": [],      # 复杂度 < 3
            "moderate": [],    # 复杂度 3-6
            "complex": []      # 复杂度 > 6
        }
        
        for segment in segments:
            if segment.complexity_score < 3.0:
                groups["simple"].append(segment)
            elif segment.complexity_score <= 6.0:
                groups["moderate"].append(segment)
            else:
                groups["complex"].append(segment)
        
        return groups
    
    def create_analysis_chunks(self, segments: List[ClaimSegment], 
                             max_chunk_size: int = 5) -> List[List[ClaimSegment]]:
        """创建用于LLM分析的块"""
        chunks = []
        current_chunk = []
        current_complexity = 0.0
        
        # 按复杂度分组
        groups = self.group_claims_by_complexity(segments)
        
        # 优先处理简单的权利要求
        for complexity_level in ["simple", "moderate", "complex"]:
            for segment in groups[complexity_level]:
                # 检查是否需要开始新块
                if (len(current_chunk) >= max_chunk_size or 
                    current_complexity + segment.complexity_score > 15.0):
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_complexity = 0.0
                
                current_chunk.append(segment)
                current_complexity += segment.complexity_score
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        self.logger.info(f"创建了{len(chunks)}个分析块")
        return chunks
