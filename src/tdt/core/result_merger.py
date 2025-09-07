"""
分析结果智能合并器

该模块实现了将多个分析块的结果合并为最终统一结果的功能。
"""
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import json

from .chunked_analyzer import ChunkAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class MergedAnalysisResult:
    """合并后的分析结果"""
    patent_number: str
    total_claims_analyzed: int
    total_rules_generated: int
    merged_rules: List[Dict[str, Any]]
    analysis_summary: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    processing_stats: Dict[str, Any]


class ResultMerger:
    """分析结果智能合并器"""
    
    def __init__(self):
        self.logger = logger
    
    def merge_chunk_results(self, chunk_results: List[ChunkAnalysisResult],
                          patent_number: str) -> MergedAnalysisResult:
        """
        合并多个块的分析结果
        
        Args:
            chunk_results: 块分析结果列表
            patent_number: 专利号
            
        Returns:
            MergedAnalysisResult: 合并后的结果
        """
        self.logger.info(f"开始合并{len(chunk_results)}个块的分析结果")
        
        # 1. 收集所有规则
        all_rules = []
        for result in chunk_results:
            all_rules.extend(result.extracted_rules)
        
        # 2. 去重和清理
        deduplicated_rules = self._deduplicate_rules(all_rules)
        
        # 3. 规则优化和标准化
        optimized_rules = self._optimize_rules(deduplicated_rules)
        
        # 4. 生成分析摘要
        analysis_summary = self._generate_analysis_summary(chunk_results, optimized_rules)
        
        # 5. 计算质量指标
        quality_metrics = self._calculate_quality_metrics(chunk_results, optimized_rules)
        
        # 6. 处理统计信息
        processing_stats = self._calculate_processing_stats(chunk_results)
        
        merged_result = MergedAnalysisResult(
            patent_number=patent_number,
            total_claims_analyzed=sum(len(r.claim_numbers) for r in chunk_results),
            total_rules_generated=len(optimized_rules),
            merged_rules=optimized_rules,
            analysis_summary=analysis_summary,
            quality_metrics=quality_metrics,
            processing_stats=processing_stats
        )
        
        self.logger.info(f"合并完成: {len(optimized_rules)}条最终规则")
        return merged_result
    
    def _deduplicate_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重规则"""
        seen_rules = set()
        deduplicated = []
        
        for rule in rules:
            # 创建规则的唯一标识
            rule_signature = self._create_rule_signature(rule)
            
            if rule_signature not in seen_rules:
                seen_rules.add(rule_signature)
                deduplicated.append(rule)
            else:
                self.logger.debug(f"发现重复规则: {rule_signature}")
        
        self.logger.info(f"去重: {len(rules)} -> {len(deduplicated)}条规则")
        return deduplicated
    
    def _create_rule_signature(self, rule: Dict[str, Any]) -> str:
        """创建规则的唯一签名"""
        key_fields = [
            rule.get("wild_type", ""),
            rule.get("rule", ""),
            rule.get("mutation", ""),
            rule.get("mutation_logic", "")
        ]
        return "|".join(str(field).strip() for field in key_fields)
    
    def _optimize_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化和标准化规则"""
        optimized = []
        
        # 按野生型分组
        rules_by_wildtype = defaultdict(list)
        for rule in rules:
            wild_type = rule.get("wild_type", "UNKNOWN")
            rules_by_wildtype[wild_type].append(rule)
        
        # 对每个野生型的规则进行优化
        for wild_type, wild_type_rules in rules_by_wildtype.items():
            optimized_group = self._optimize_wildtype_rules(wild_type_rules)
            optimized.extend(optimized_group)
        
        # 排序：按复杂度和重要性
        optimized.sort(key=self._rule_priority_score, reverse=True)
        
        return optimized
    
    def _optimize_wildtype_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化同一野生型的规则"""
        if len(rules) <= 1:
            return rules
        
        # 合并相似的规则
        merged_rules = []
        processed_indices = set()
        
        for i, rule1 in enumerate(rules):
            if i in processed_indices:
                continue
            
            similar_rules = [rule1]
            processed_indices.add(i)
            
            # 查找相似规则
            for j, rule2 in enumerate(rules[i+1:], i+1):
                if j not in processed_indices and self._are_rules_similar(rule1, rule2):
                    similar_rules.append(rule2)
                    processed_indices.add(j)
            
            # 合并相似规则
            if len(similar_rules) > 1:
                merged_rule = self._merge_similar_rules(similar_rules)
                merged_rules.append(merged_rule)
            else:
                merged_rules.append(rule1)
        
        return merged_rules
    
    def _are_rules_similar(self, rule1: Dict[str, Any], rule2: Dict[str, Any]) -> bool:
        """判断两个规则是否相似"""
        # 检查规则类型
        if rule1.get("rule") != rule2.get("rule"):
            return False
        
        # 检查突变位点重叠度
        mutations1 = set(rule1.get("mutation", "").split("/"))
        mutations2 = set(rule2.get("mutation", "").split("/"))
        
        if mutations1 and mutations2:
            overlap = len(mutations1 & mutations2) / len(mutations1 | mutations2)
            if overlap > 0.6:  # 60%以上重叠认为相似
                return True
        
        return False
    
    def _merge_similar_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并相似规则"""
        base_rule = rules[0].copy()
        
        # 合并突变信息
        all_mutations = set()
        all_logic_parts = []
        
        for rule in rules:
            mutations = rule.get("mutation", "").split("/")
            all_mutations.update(m for m in mutations if m.strip())
            
            logic = rule.get("mutation_logic", "")
            if logic and logic not in all_logic_parts:
                all_logic_parts.append(logic)
        
        # 更新合并后的规则
        base_rule["mutation"] = "/".join(sorted(all_mutations))
        
        if len(all_logic_parts) > 1:
            base_rule["mutation_logic"] = " | ".join(f"({logic})" for logic in all_logic_parts)
        
        base_rule["comment"] = f"合并了{len(rules)}条相似规则"
        
        return base_rule
    
    def _rule_priority_score(self, rule: Dict[str, Any]) -> float:
        """计算规则优先级评分"""
        score = 0.0
        
        # 规则类型权重
        rule_type = rule.get("rule", "")
        if "identical" in rule_type:
            score += 10.0
        elif "identity>" in rule_type:
            score += 8.0
        elif "conditional" in rule_type:
            score += 6.0
        else:
            score += 3.0
        
        # 突变信息复杂度
        mutation = rule.get("mutation", "")
        mutation_count = len([m for m in mutation.split("/") if m.strip()])
        score += min(mutation_count * 0.5, 3.0)
        
        # 逻辑表达式复杂度
        logic = rule.get("mutation_logic", "")
        logic_complexity = logic.count("&") + logic.count("|") + logic.count("(")
        score += min(logic_complexity * 0.2, 2.0)
        
        # 描述质量
        statement = rule.get("statement", "")
        if len(statement) > 30:
            score += 1.0
        
        return score
    
    def _generate_analysis_summary(self, chunk_results: List[ChunkAnalysisResult],
                                 final_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成分析摘要"""
        # 成功/失败统计
        successful_chunks = [r for r in chunk_results if not r.error_message]
        failed_chunks = [r for r in chunk_results if r.error_message]
        
        # 规则类型统计
        rule_types = defaultdict(int)
        for rule in final_rules:
            rule_type = rule.get("rule", "unknown")
            rule_types[rule_type] += 1
        
        # 野生型覆盖统计
        wild_types = set(rule.get("wild_type", "") for rule in final_rules)
        
        return {
            "processing_summary": {
                "total_chunks": len(chunk_results),
                "successful_chunks": len(successful_chunks),
                "failed_chunks": len(failed_chunks),
                "success_rate": len(successful_chunks) / len(chunk_results) if chunk_results else 0
            },
            "rules_summary": {
                "total_rules": len(final_rules),
                "rule_types": dict(rule_types),
                "unique_wild_types": len(wild_types),
                "wild_types_covered": sorted(list(wild_types))
            },
            "complexity_analysis": {
                "rules_per_chunk": len(final_rules) / len(successful_chunks) if successful_chunks else 0,
                "avg_chunk_confidence": sum(r.analysis_confidence for r in successful_chunks) / len(successful_chunks) if successful_chunks else 0
            }
        }
    
    def _calculate_quality_metrics(self, chunk_results: List[ChunkAnalysisResult],
                                 final_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算质量指标"""
        # 完整性指标
        total_claims = sum(len(r.claim_numbers) for r in chunk_results)
        claims_with_rules = len(set(
            claim_num for result in chunk_results 
            for claim_num in result.claim_numbers 
            if result.extracted_rules
        ))
        
        # 规则质量指标
        quality_scores = []
        for rule in final_rules:
            score = self._evaluate_rule_quality(rule)
            quality_scores.append(score)
        
        return {
            "completeness": {
                "claims_coverage": claims_with_rules / total_claims if total_claims else 0,
                "rules_per_claim": len(final_rules) / total_claims if total_claims else 0
            },
            "rule_quality": {
                "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
                "high_quality_rules": len([s for s in quality_scores if s > 0.8]),
                "low_quality_rules": len([s for s in quality_scores if s < 0.5])
            },
            "consistency": {
                "unique_wild_types": len(set(r.get("wild_type", "") for r in final_rules)),
                "logical_expressions": len([r for r in final_rules if r.get("mutation_logic", "")])
            }
        }
    
    def _evaluate_rule_quality(self, rule: Dict[str, Any]) -> float:
        """评估单个规则的质量"""
        score = 0.0
        
        # 必要字段完整性
        required_fields = ["wild_type", "rule", "statement"]
        for field in required_fields:
            if rule.get(field):
                score += 0.2
        
        # 逻辑表达式质量
        mutation_logic = rule.get("mutation_logic", "")
        if mutation_logic and any(op in mutation_logic for op in ["&", "|", "("]):
            score += 0.2
        
        # 突变信息质量
        mutation = rule.get("mutation", "")
        if mutation and mutation != "待分析":
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_processing_stats(self, chunk_results: List[ChunkAnalysisResult]) -> Dict[str, Any]:
        """计算处理统计信息"""
        processing_times = [r.processing_time for r in chunk_results if r.processing_time > 0]
        
        return {
            "timing": {
                "total_processing_time": sum(processing_times),
                "avg_chunk_time": sum(processing_times) / len(processing_times) if processing_times else 0,
                "min_chunk_time": min(processing_times) if processing_times else 0,
                "max_chunk_time": max(processing_times) if processing_times else 0
            },
            "throughput": {
                "claims_per_second": sum(len(r.claim_numbers) for r in chunk_results) / sum(processing_times) if processing_times else 0,
                "rules_per_second": sum(len(r.extracted_rules) for r in chunk_results) / sum(processing_times) if processing_times else 0
            },
            "error_analysis": {
                "error_count": len([r for r in chunk_results if r.error_message]),
                "error_messages": [r.error_message for r in chunk_results if r.error_message]
            }
        }
    
    def export_detailed_report(self, merged_result: MergedAnalysisResult) -> str:
        """导出详细分析报告"""
        report = f"""# 分段专利分析详细报告

## 基本信息
- 专利号: {merged_result.patent_number}
- 分析的权利要求总数: {merged_result.total_claims_analyzed}
- 生成的规则总数: {merged_result.total_rules_generated}

## 处理统计
{json.dumps(merged_result.processing_stats, ensure_ascii=False, indent=2)}

## 质量指标
{json.dumps(merged_result.quality_metrics, ensure_ascii=False, indent=2)}

## 分析摘要
{json.dumps(merged_result.analysis_summary, ensure_ascii=False, indent=2)}

## 生成的规则
{json.dumps(merged_result.merged_rules, ensure_ascii=False, indent=2)}
"""
        return report
