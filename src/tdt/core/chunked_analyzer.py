"""
分段专利分析器

该模块实现了对权利要求书段落的详细分析，是智能分段处理架构的分析组件。
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import json

from .claims_splitter import ClaimSegment
from .llm_agent import LLMRuleAgent

logger = logging.getLogger(__name__)


@dataclass
class ChunkAnalysisResult:
    """单个分析块的结果"""
    chunk_id: int
    claim_numbers: List[int]
    extracted_rules: List[Dict[str, Any]]
    analysis_confidence: float
    processing_time: float
    error_message: Optional[str] = None


class ChunkedAnalyzer:
    """分段专利分析器"""
    
    def __init__(self, llm_agent: LLMRuleAgent):
        self.llm_agent = llm_agent
        self.logger = logger
    
    def analyze_chunks(self, claim_chunks: List[List[ClaimSegment]], 
                      sequence_data: Dict[str, Any],
                      existing_rules: List[Dict[str, Any]]) -> List[ChunkAnalysisResult]:
        """
        分析权利要求书块
        
        Args:
            claim_chunks: 权利要求书分块列表
            sequence_data: 序列数据
            existing_rules: 现有规则数据
            
        Returns:
            List[ChunkAnalysisResult]: 分析结果列表
        """
        self.logger.info(f"开始分析{len(claim_chunks)}个权利要求书块")
        
        results = []
        
        for chunk_id, chunk in enumerate(claim_chunks):
            self.logger.info(f"分析块 {chunk_id + 1}/{len(claim_chunks)}: 包含权利要求 {[c.claim_number for c in chunk]}")
            
            try:
                result = self._analyze_single_chunk(
                    chunk_id, chunk, sequence_data, existing_rules
                )
                results.append(result)
                
                # 记录分析进度
                self.logger.info(f"块 {chunk_id + 1} 分析完成: 提取{len(result.extracted_rules)}条规则")
                
            except Exception as e:
                self.logger.error(f"分析块 {chunk_id + 1} 失败: {e}")
                # 创建错误结果
                error_result = ChunkAnalysisResult(
                    chunk_id=chunk_id,
                    claim_numbers=[c.claim_number for c in chunk],
                    extracted_rules=[],
                    analysis_confidence=0.0,
                    processing_time=0.0,
                    error_message=str(e)
                )
                results.append(error_result)
        
        self.logger.info(f"完成所有块分析，总计{sum(len(r.extracted_rules) for r in results)}条规则")
        return results
    
    def _analyze_single_chunk(self, chunk_id: int, 
                            chunk: List[ClaimSegment],
                            sequence_data: Dict[str, Any],
                            existing_rules: List[Dict[str, Any]]) -> ChunkAnalysisResult:
        """分析单个权利要求书块"""
        import time
        start_time = time.time()
        
        # 1. 准备分析数据
        chunk_data = self._prepare_chunk_data(chunk, sequence_data)
        
        # 2. 构建针对块的专门提示
        chunk_prompt = self._build_chunk_prompt(chunk, existing_rules)
        
        # 3. 调用LLM进行分析
        analysis_result = self._call_llm_for_chunk(chunk_prompt, chunk_data)
        
        # 4. 解析和验证结果
        extracted_rules = self._parse_chunk_result(analysis_result, chunk)
        
        # 5. 计算置信度
        confidence = self._calculate_confidence(extracted_rules, chunk)
        
        processing_time = time.time() - start_time
        
        return ChunkAnalysisResult(
            chunk_id=chunk_id,
            claim_numbers=[c.claim_number for c in chunk],
            extracted_rules=extracted_rules,
            analysis_confidence=confidence,
            processing_time=processing_time
        )
    
    def _prepare_chunk_data(self, chunk: List[ClaimSegment], 
                          sequence_data: Dict[str, Any]) -> Dict[str, Any]:
        """准备块分析数据"""
        # 提取当前块中引用的序列
        all_seq_ids = set()
        for claim in chunk:
            all_seq_ids.update(claim.seq_id_references)
        
        # 筛选相关序列数据
        relevant_sequences = {}
        if "sequences" in sequence_data:
            for seq in sequence_data["sequences"]:
                seq_id = seq.get("sequence_id", "")
                if seq_id in all_seq_ids or any(sid in seq_id for sid in all_seq_ids):
                    relevant_sequences[seq_id] = seq
        
        # 安全转换为JSON可序列化的字典
        claims_dict = []
        for claim in chunk:
            claim_dict = asdict(claim)
            # 移除或转换不可序列化的字段
            if 'extraction_timestamp' in claim_dict:
                del claim_dict['extraction_timestamp']
            claims_dict.append(claim_dict)
            
        return {
            "claims": claims_dict,
            "relevant_sequences": relevant_sequences,
            "chunk_summary": {
                "total_claims": len(chunk),
                "complexity_range": (
                    min(c.complexity_score for c in chunk),
                    max(c.complexity_score for c in chunk)
                ),
                "seq_id_count": len(all_seq_ids),
                "claim_types": {
                    "independent": len([c for c in chunk if c.claim_type == "independent"]),
                    "dependent": len([c for c in chunk if c.claim_type == "dependent"])
                }
            }
        }
    
    def _build_chunk_prompt(self, chunk: List[ClaimSegment], 
                          existing_rules: List[Dict[str, Any]]) -> str:
        """构建针对块的专门提示"""
        
        # 分析块的特征
        complexity_scores = [c.complexity_score for c in chunk]
        avg_complexity = sum(complexity_scores) / len(complexity_scores)
        
        # 提取现有规则的样本
        rule_examples = existing_rules[:3] if existing_rules else []
        
        prompt = f"""你是专利序列保护分析专家。现在需要分析一个包含{len(chunk)}个权利要求的专利块。

## 当前分析块特征
- 权利要求编号: {[c.claim_number for c in chunk]}
- 平均复杂度: {avg_complexity:.2f}
- 独立权利要求: {len([c for c in chunk if c.claim_type == "independent"])}个
- 从属权利要求: {len([c for c in chunk if c.claim_type == "dependent"])}个

## 分析要求
请对每个权利要求进行详细分析，识别：

1. **保护范围识别**
   - 野生型序列标识 (wild_type)
   - 保护类型 (identical/identity>X%/conditional)
   - 突变模式描述

2. **逻辑表达式生成**
   - 使用数学逻辑操作符 (&, |, !, ())
   - 标准突变格式 (Y178A/F186R)
   - 序列同一性逻辑 (seq_identity >= X%)

3. **规则输出格式**
每个权利要求应生成至少1-3条具体规则，格式如下：
```json
{{
  "wild_type": "SEQ_ID_NO_X",
  "rule": "规则类型",
  "mutation": "突变描述",
  "mutation_logic": "逻辑表达式",
  "identity_logic": "同一性逻辑",
  "statement": "保护描述",
  "comment": "策略说明"
}}
```

## 现有规则样本参考
{json.dumps(rule_examples, ensure_ascii=False, indent=2) if rule_examples else "无现有规则"}

## 重要提醒
- 必须为每个权利要求生成具体、可操作的规则
- 复杂权利要求应生成多条规则来覆盖不同保护层次
- 避免生成空洞的"analysis_completed"类型规则
- 专注于序列保护范围，不要生成回避策略

请开始分析："""

        return prompt
    
    def _call_llm_for_chunk(self, prompt: str, chunk_data: Dict[str, Any]) -> str:
        """调用LLM分析块"""
        try:
            # 构建完整的提示文本
            full_prompt = f"{prompt}\n\n## 分析数据\n{json.dumps(chunk_data, ensure_ascii=False, indent=2)}"
            
            # 调用LLM
            response = self.llm_agent._call_llm(full_prompt)
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            # 返回备用响应
            return self._generate_fallback_response(chunk_data)
    
    def _generate_fallback_response(self, chunk_data: Dict[str, Any]) -> str:
        """生成备用响应"""
        claims = chunk_data.get("claims", [])
        rules = []
        
        for claim in claims:
            # 基于权利要求数据生成基础规则
            rule = {
                "wild_type": f"SEQ_ID_NO_{claim.get('claim_number', 1)}",
                "rule": "conditional_protection",
                "mutation": "待进一步分析",
                "mutation_logic": "基于权利要求复杂度生成",
                "identity_logic": "seq_identity >= 80%",
                "statement": f"权利要求{claim.get('claim_number')}的保护规则（备用生成）",
                "comment": "系统备用规则，需要人工审核"
            }
            rules.append(rule)
        
        return json.dumps({"rules": rules}, ensure_ascii=False, indent=2)
    
    def _parse_chunk_result(self, llm_response: str, 
                          chunk: List[ClaimSegment]) -> List[Dict[str, Any]]:
        """解析块分析结果"""
        try:
            # 尝试解析JSON响应
            if "```json" in llm_response:
                # 提取JSON代码块
                json_match = json.loads(llm_response.split("```json")[1].split("```")[0])
            else:
                # 直接解析JSON
                json_match = json.loads(llm_response)
            
            # 提取规则
            if "rules" in json_match:
                return json_match["rules"]
            elif isinstance(json_match, list):
                return json_match
            else:
                return [json_match]
                
        except Exception as e:
            self.logger.warning(f"解析LLM响应失败: {e}")
            # 生成最小备用规则
            return self._generate_minimal_rules(chunk)
    
    def _generate_minimal_rules(self, chunk: List[ClaimSegment]) -> List[Dict[str, Any]]:
        """生成最小备用规则"""
        rules = []
        
        for claim in chunk:
            rule = {
                "wild_type": f"SEQ_ID_NO_{claim.seq_id_references[0] if claim.seq_id_references else '1'}",
                "rule": "需要详细分析",
                "mutation": "/".join(claim.mutation_positions[:5]) if claim.mutation_positions else "待分析",
                "mutation_logic": f"复杂度评分: {claim.complexity_score}",
                "identity_logic": "seq_identity >= 60%",
                "statement": f"权利要求{claim.claim_number}需要进一步分析",
                "comment": f"权利要求类型: {claim.claim_type}"
            }
            rules.append(rule)
        
        return rules
    
    def _calculate_confidence(self, extracted_rules: List[Dict[str, Any]], 
                           chunk: List[ClaimSegment]) -> float:
        """计算分析置信度"""
        if not extracted_rules:
            return 0.0
        
        confidence = 0.5  # 基础置信度
        
        # 规则数量因子
        rules_per_claim = len(extracted_rules) / len(chunk)
        confidence += min(rules_per_claim * 0.2, 0.3)
        
        # 规则质量因子
        quality_score = 0
        for rule in extracted_rules:
            # 检查关键字段
            if rule.get("wild_type") and "SEQ_ID_NO" in rule.get("wild_type", ""):
                quality_score += 0.1
            if rule.get("mutation_logic") and any(op in rule.get("mutation_logic", "") for op in ["&", "|", "("]):
                quality_score += 0.1
            if rule.get("statement") and len(rule.get("statement", "")) > 20:
                quality_score += 0.1
        
        confidence += min(quality_score / len(extracted_rules), 0.2)
        
        return min(confidence, 1.0)
