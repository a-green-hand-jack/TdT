"""
智能规则生成器

集成LLM Agent和数据加载器，提供完整的规则生成功能。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .data_loader import DataLoader
from .llm_agent import LLMRuleAgent
from ..models.rule_models import RuleGenerationResult, StandardizedRuleOutput

logger = logging.getLogger(__name__)


class IntelligentRuleGenerator:
    """智能规则生成和输出管理器"""
    
    def __init__(self, llm_agent: LLMRuleAgent):
        """初始化规则生成器
        
        Args:
            llm_agent: LLM规则生成智能体
        """
        self.llm_agent = llm_agent
        self.data_loader = DataLoader()
        
        logger.info("智能规则生成器初始化完成")
    
    def generate_rules_from_patent(self, 
                                 claims_path: str,
                                 sequence_json_path: str,
                                 existing_rules_json_path: str) -> RuleGenerationResult:
        """从专利数据生成完整的保护规则
        
        Args:
            claims_path: 权利要求书Markdown文件路径
            sequence_json_path: 标准化序列JSON文件路径
            existing_rules_json_path: 现有规则JSON文件路径
            
        Returns:
            规则生成结果
        """
        logger.info(f"开始生成规则: {claims_path}")
        
        try:
            # 加载数据
            claims_doc = self.data_loader.load_claims_markdown(Path(claims_path))
            sequence_data = self.data_loader.load_sequence_json(Path(sequence_json_path))
            existing_rules = self.data_loader.load_existing_rules(Path(existing_rules_json_path))
            
            logger.info(f"数据加载完成: {claims_doc.patent_number}")
            
            # 创建序列与权利要求的映射
            sequence_mapping = self.data_loader.create_sequence_claims_mapping(
                claims_doc, sequence_data
            )
            
            logger.info(f"序列映射完成: {sequence_mapping.mapping_statistics}")
            
            # 使用LLM进行分析
            result = self.llm_agent.analyze_patent_claims(
                claims_doc, existing_rules, sequence_data
            )
            
            # 添加映射信息到结果中
            result.analysis_summary.update({
                'sequence_mapping': sequence_mapping.mapping_statistics,
                'total_mapped_sequences': len(sequence_mapping.sequence_to_claims),
                'unmatched_seq_ids': len(sequence_mapping.unmatched_seq_ids)
            })
            
            logger.info(f"规则生成完成: {claims_doc.patent_number}")
            return result
            
        except Exception as e:
            logger.error(f"规则生成失败: {e}")
            raise
    
    def export_to_json(self, rules: RuleGenerationResult, output_path: str) -> None:
        """导出JSON格式规则文件
        
        Args:
            rules: 规则生成结果
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为标准化输出格式
        standardized_output = StandardizedRuleOutput(
            metadata={
                "patent_number": rules.patent_number,
                "generation_timestamp": rules.generation_timestamp.isoformat(),
                "llm_model": rules.llm_model,
                "analysis_confidence": rules.analysis_confidence,
                "total_rules": len(rules.protection_rules)
            },
            rules=rules.protection_rules,
            analysis_summary=rules.analysis_summary,
            generation_info={
                "complexity_analysis": rules.complexity_analysis.dict(),
                "avoidance_strategies": [strategy.dict() for strategy in rules.avoidance_strategies],
                "llm_reasoning": rules.llm_reasoning,
                "processing_log": rules.processing_log
            }
        )
        
        # 导出JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                standardized_output.dict(),
                f,
                ensure_ascii=False,
                indent=2
            )
        
        logger.info(f"JSON规则文件已导出: {output_path}")
    
    def export_to_markdown(self, rules: RuleGenerationResult, output_path: str) -> None:
        """导出Markdown格式说明文档
        
        Args:
            rules: 规则生成结果
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成Markdown内容
        md_content = self._generate_markdown_content(rules)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Markdown文档已导出: {output_path}")
    
    def generate_analysis_report(self, rules: RuleGenerationResult) -> str:
        """生成规则分析报告
        
        Args:
            rules: 规则生成结果
            
        Returns:
            分析报告文本
        """
        report_lines = []
        
        report_lines.append(f"# 专利规则分析报告")
        report_lines.append(f"**专利号**: {rules.patent_number}")
        report_lines.append(f"**分析时间**: {rules.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**使用模型**: {rules.llm_model}")
        report_lines.append(f"**分析置信度**: {rules.analysis_confidence:.2%}")
        report_lines.append("")
        
        # 基本统计
        report_lines.append("## 基本统计")
        report_lines.append(f"- 保护规则数量: {len(rules.protection_rules)}")
        report_lines.append(f"- 复杂度级别: {rules.complexity_analysis.complexity_level}")
        report_lines.append(f"- 复杂度评分: {rules.complexity_analysis.complexity_score:.1f}/10")
        report_lines.append(f"- 回避策略数量: {len(rules.avoidance_strategies)}")
        report_lines.append("")
        
        # 保护规则摘要
        if rules.protection_rules:
            report_lines.append("## 保护规则摘要")
            for i, rule in enumerate(rules.protection_rules, 1):
                report_lines.append(f"### 规则 {i}: {rule.rule_id}")
                report_lines.append(f"- **类型**: {rule.rule_type}")
                report_lines.append(f"- **保护范围**: {rule.protection_scope}")
                report_lines.append(f"- **复杂度**: {rule.complexity_score:.1f}/10")
                report_lines.append(f"- **技术描述**: {rule.technical_description}")
                report_lines.append("")
        
        # 回避策略
        if rules.avoidance_strategies:
            report_lines.append("## 推荐回避策略")
            for i, strategy in enumerate(rules.avoidance_strategies, 1):
                report_lines.append(f"### 策略 {i}: {strategy.strategy_type}")
                report_lines.append(f"**描述**: {strategy.description}")
                report_lines.append(f"**置信度**: {strategy.confidence_score:.2%}")
                report_lines.append("**实施建议**:")
                for suggestion in strategy.implementation_suggestions:
                    report_lines.append(f"- {suggestion}")
                report_lines.append(f"**风险评估**: {strategy.risk_assessment}")
                report_lines.append("")
        
        # 分析总结
        report_lines.append("## 分析总结")
        if rules.analysis_summary:
            for key, value in rules.analysis_summary.items():
                report_lines.append(f"- **{key}**: {value}")
        
        return "\n".join(report_lines)
    
    def _generate_markdown_content(self, rules: RuleGenerationResult) -> str:
        """生成Markdown内容"""
        lines = []
        
        # 标题和基本信息
        lines.append(f"# 专利保护规则分析")
        lines.append("")
        lines.append("## 基本信息")
        lines.append("")
        lines.append(f"**专利号**: {rules.patent_number}")
        lines.append(f"**分析时间**: {rules.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**LLM模型**: {rules.llm_model}")
        lines.append(f"**分析置信度**: {rules.analysis_confidence:.2%}")
        lines.append("")
        
        # 复杂度分析
        lines.append("## 复杂度分析")
        lines.append("")
        lines.append(f"**复杂度级别**: {rules.complexity_analysis.complexity_level}")
        lines.append(f"**复杂度评分**: {rules.complexity_analysis.complexity_score:.1f}/10")
        lines.append(f"**突变位点数量**: {rules.complexity_analysis.mutation_count}")
        lines.append(f"**表达建议**: {rules.complexity_analysis.representation_suggestion}")
        lines.append("")
        lines.append(f"**判断理由**: {rules.complexity_analysis.reasoning}")
        lines.append("")
        
        # 保护规则详情
        if rules.protection_rules:
            lines.append("## 保护规则详情")
            lines.append("")
            
            for i, rule in enumerate(rules.protection_rules, 1):
                lines.append(f"### 规则 {i}: {rule.rule_id}")
                lines.append("")
                lines.append(f"**规则类型**: {rule.rule_type}")
                lines.append(f"**保护范围**: {rule.protection_scope}")
                lines.append(f"**复杂度评分**: {rule.complexity_score:.1f}/10")
                lines.append(f"**目标序列**: {', '.join(rule.target_sequences)}")
                
                if rule.identity_threshold:
                    lines.append(f"**相似度阈值**: {rule.identity_threshold:.1%}")
                
                lines.append("")
                lines.append(f"**法律描述**: {rule.legal_description}")
                lines.append("")
                lines.append(f"**技术描述**: {rule.technical_description}")
                lines.append("")
                
                if rule.mutation_combinations:
                    lines.append("**突变组合**:")
                    for combo in rule.mutation_combinations:
                        lines.append(f"- {combo.pattern_description}")
                        lines.append(f"  - 突变: {', '.join([m.mutation_code for m in combo.mutations])}")
                        lines.append(f"  - 类型: {combo.combination_type}")
                    lines.append("")
        
        # 回避策略
        if rules.avoidance_strategies:
            lines.append("## 回避策略")
            lines.append("")
            
            for i, strategy in enumerate(rules.avoidance_strategies, 1):
                lines.append(f"### 策略 {i}: {strategy.strategy_type}")
                lines.append("")
                lines.append(f"**描述**: {strategy.description}")
                lines.append(f"**置信度**: {strategy.confidence_score:.2%}")
                lines.append("")
                lines.append("**实施建议**:")
                for suggestion in strategy.implementation_suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")
                lines.append(f"**风险评估**: {strategy.risk_assessment}")
                lines.append("")
        
        # 分析摘要
        lines.append("## 分析摘要")
        lines.append("")
        if rules.analysis_summary:
            for key, value in rules.analysis_summary.items():
                if isinstance(value, dict):
                    lines.append(f"**{key}**:")
                    for sub_key, sub_value in value.items():
                        lines.append(f"- {sub_key}: {sub_value}")
                else:
                    lines.append(f"**{key}**: {value}")
                lines.append("")
        
        # 页脚
        lines.append("---")
        lines.append("")
        lines.append("*此文档由TDT专利序列规则提取工具自动生成*")
        
        return "\n".join(lines)
    
    @classmethod
    def create_with_qwen(cls, api_key: Optional[str] = None, model: str = "qwen-plus") -> 'IntelligentRuleGenerator':
        """创建使用Qwen的规则生成器
        
        Args:
            api_key: Qwen API密钥
            model: 模型名称
            
        Returns:
            智能规则生成器实例
        """
        llm_agent = LLMRuleAgent(api_key=api_key, model=model)
        return cls(llm_agent)
