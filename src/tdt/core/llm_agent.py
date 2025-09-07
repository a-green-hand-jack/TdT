"""
基于Qwen的LLM规则生成Agent

使用Qwen API进行专利规则分析和生成。
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..agents.prompts import (
    PATENT_ANALYSIS_PROMPT, SYSTEM_PROMPT, format_claims_for_llm,
    format_existing_rules, format_sequence_summary
)
from ..models.claims_models import ClaimsDocument, SequenceClaimsMapping
from ..models.rule_models import (
    AvoidanceStrategy, ComplexityAnalysis, ComplexityLevel,
    RuleGenerationResult
)
from ..models.sequence_record import SequenceProcessingResult

logger = logging.getLogger(__name__)


class QwenAPIError(Exception):
    """Qwen API调用错误"""
    pass


class LLMRuleAgent:
    """基于Qwen的规则生成智能体"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-plus"):
        """初始化LLM Agent
        
        Args:
            api_key: Qwen API密钥，如果为None则从环境变量读取
            model: 使用的模型名称
        """
        self.api_key = api_key or os.getenv('QWEN_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供Qwen API密钥")
        
        self.model = model
        
        # 配置OpenAI客户端使用Qwen API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        logger.info(f"初始化LLM Agent，使用模型: {self.model}")
    
    def analyze_patent_claims(self, 
                            claims_data: ClaimsDocument,
                            existing_rules_data: Dict,
                            sequence_data: SequenceProcessingResult) -> RuleGenerationResult:
        """分析权利要求书内容，结合已有规则和序列数据
        
        Args:
            claims_data: 权利要求书文档
            existing_rules_data: 现有规则数据
            sequence_data: 标准化序列数据
            
        Returns:
            规则生成结果
        """
        logger.info(f"开始分析专利: {claims_data.patent_number}")
        
        try:
            # 格式化输入数据
            claims_content = format_claims_for_llm(claims_data)
            sequence_summary = format_sequence_summary(sequence_data)
            existing_rules = format_existing_rules(existing_rules_data)
            
            # 构建提示
            prompt = PATENT_ANALYSIS_PROMPT.format(
                patent_number=claims_data.patent_number,
                total_claims=claims_data.total_claims,
                total_sequences=len(sequence_data.sequences),
                claims_content=claims_content,
                sequence_summary=sequence_summary,
                existing_rules=existing_rules
            )
            
            # 调用LLM分析
            response = self._call_llm(prompt)
            
            # 解析响应
            analysis_result = self._parse_analysis_response(response, claims_data.patent_number)
            
            logger.info(f"完成专利分析: {claims_data.patent_number}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"专利分析失败: {e}")
            raise
    
    def correlate_sequences_with_claims(self, 
                                      seq_data: SequenceProcessingResult,
                                      claims_data: ClaimsDocument) -> SequenceClaimsMapping:
        """将标准化序列数据与权利要求进行关联
        
        Args:
            seq_data: 标准化序列数据
            claims_data: 权利要求书数据
            
        Returns:
            序列与权利要求的映射关系
        """
        logger.info("开始序列与权利要求关联分析")
        
        mapping = SequenceClaimsMapping(patent_number=claims_data.patent_number)
        
        # 创建序列ID到数字的映射
        sequence_lookup = {}
        for seq in seq_data.sequences:
            # 尝试从sequence_id中提取数字
            import re
            numbers = re.findall(r'\d+', seq.sequence_id)
            if numbers:
                sequence_lookup[int(numbers[0])] = seq.sequence_id
        
        # 建立关联
        for claim in claims_data.claims:
            for seq_ref in claim.seq_id_references:
                if seq_ref.numeric_id in sequence_lookup:
                    sequence_id = sequence_lookup[seq_ref.numeric_id]
                    mapping.add_mapping(seq_ref.seq_id_no, sequence_id, claim.claim_number)
                else:
                    mapping.unmatched_seq_ids.append(seq_ref.seq_id_no)
        
        # 找出未引用的序列
        referenced_sequences = set(mapping.sequence_to_claims.keys())
        all_sequences = {seq.sequence_id for seq in seq_data.sequences}
        mapping.orphaned_sequences = list(all_sequences - referenced_sequences)
        
        mapping.calculate_statistics()
        
        logger.info(f"关联完成: {mapping.mapping_statistics}")
        return mapping
    
    def evaluate_rule_complexity(self, rule_data: Dict) -> ComplexityAnalysis:
        """评估规则复杂度
        
        Args:
            rule_data: 规则数据
            
        Returns:
            复杂度分析结果
        """
        logger.info("开始规则复杂度评估")
        
        try:
            prompt = COMPLEXITY_EVALUATION_PROMPT.format(
                rule_info=json.dumps(rule_data, ensure_ascii=False, indent=2)
            )
            
            response = self._call_llm(prompt)
            result = json.loads(response)
            
            complexity_data = result.get('complexity_analysis', {})
            
            # 转换为ComplexityAnalysis对象
            complexity_level = ComplexityLevel(complexity_data.get('complexity_level', 'moderate'))
            
            analysis = ComplexityAnalysis(
                complexity_level=complexity_level,
                complexity_score=complexity_data.get('complexity_score', 0.5),
                mutation_count=complexity_data.get('factors', {}).get('mutation_count', 0),
                combination_complexity=complexity_data.get('factors', {}).get('combination_complexity', 0),
                dependency_depth=complexity_data.get('factors', {}).get('dependency_depth', 0),
                representation_suggestion=complexity_data.get('representation_suggestion', ''),
                reasoning=complexity_data.get('reasoning', ''),
                simplification_options=complexity_data.get('simplification_options', [])
            )
            
            logger.info(f"复杂度评估完成: {analysis.complexity_level}")
            return analysis
            
        except Exception as e:
            logger.error(f"复杂度评估失败: {e}")
            raise
    
    def generate_avoidance_strategies(self, 
                                    protection_rules: Dict,
                                    sequence_info: Dict) -> List[AvoidanceStrategy]:
        """生成回避策略
        
        Args:
            protection_rules: 保护规则
            sequence_info: 序列信息
            
        Returns:
            回避策略列表
        """
        logger.info("开始生成回避策略")
        
        try:
            prompt = AVOIDANCE_STRATEGY_PROMPT.format(
                protection_rules=json.dumps(protection_rules, ensure_ascii=False, indent=2),
                sequence_info=json.dumps(sequence_info, ensure_ascii=False, indent=2)
            )
            
            response = self._call_llm(prompt)
            result = json.loads(response)
            
            strategies = []
            for strategy_data in result.get('avoidance_strategies', []):
                strategy = AvoidanceStrategy(
                    strategy_type=strategy_data.get('strategy_type', ''),
                    description=strategy_data.get('description', ''),
                    implementation_suggestions=strategy_data.get('implementation_suggestions', []),
                    risk_assessment=strategy_data.get('risk_assessment', ''),
                    confidence_score=strategy_data.get('confidence_score', 0.5)
                )
                strategies.append(strategy)
            
            logger.info(f"生成回避策略完成: {len(strategies)}个策略")
            return strategies
            
        except Exception as e:
            logger.error(f"回避策略生成失败: {e}")
            raise
    
    def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """调用Qwen LLM API
        
        Args:
            prompt: 输入提示
            max_retries: 最大重试次数
            
        Returns:
            LLM响应文本
            
        Raises:
            QwenAPIError: API调用失败
        """
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4000
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise QwenAPIError("LLM返回空响应")
                
                return content.strip()
                
            except Exception as e:
                logger.warning(f"LLM调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise QwenAPIError(f"LLM调用失败: {e}")
    
    def _parse_analysis_response(self, response: str, patent_number: str) -> RuleGenerationResult:
        """解析LLM分析响应，支持容错机制
        
        Args:
            response: LLM响应文本
            patent_number: 专利号
            
        Returns:
            规则生成结果
        """
        # 多种解析策略
        json_content = None
        parsed_data = None
        
        try:
            # 策略1: 直接解析
            parsed_data = json.loads(response)
            json_content = response
        except json.JSONDecodeError:
            try:
                # 策略2: 清理markdown代码块标记
                cleaned_response = self._clean_markdown_json(response)
                parsed_data = json.loads(cleaned_response)
                json_content = cleaned_response
            except json.JSONDecodeError:
                try:
                    # 策略3: 提取JSON部分
                    extracted_json = self._extract_json_from_text(response)
                    if extracted_json:
                        parsed_data = json.loads(extracted_json)
                        json_content = extracted_json
                except json.JSONDecodeError:
                    pass
        
        # 如果所有解析策略都失败，创建备用结果并保存原始响应
        if parsed_data is None:
            logger.error(f"所有JSON解析策略失败，原始响应: {response[:500]}...")
            parsed_data = self._create_fallback_result(response, patent_number)
            json_content = json.dumps(parsed_data, ensure_ascii=False, indent=2)
        
        try:
            data = parsed_data
            
            # 创建规则生成结果
            result = RuleGenerationResult(
                patent_number=patent_number,
                llm_model=self.model,
                analysis_confidence=data.get('patent_analysis', {}).get('analysis_confidence', 0.8),
                protection_rules=[],  # 这里需要进一步解析
                complexity_analysis=ComplexityAnalysis(
                    complexity_level=ComplexityLevel.MODERATE,
                    complexity_score=5.0,
                    mutation_count=0,
                    combination_complexity=0,
                    dependency_depth=0,
                    representation_suggestion="",
                    reasoning=""
                ),
                avoidance_strategies=[],
                analysis_summary=data.get('analysis_summary', {}),
                llm_reasoning=str(data.get('patent_analysis', {}).get('key_findings', "分析完成"))
            )
            
        except Exception as e:
            logger.error(f"规则生成结果创建失败: {e}")
            # 创建最小化的备用结果
            result = self._create_minimal_fallback_result(patent_number, json_content or response)
            
        # 保存原始响应到结果中，便于调试
        if hasattr(result, 'raw_llm_response'):
            result.raw_llm_response = response
            
        return result
    
    def _clean_markdown_json(self, text: str) -> str:
        """清理markdown代码块标记
        
        Args:
            text: 包含markdown标记的文本
            
        Returns:
            清理后的JSON文本
        """
        import re
        
        # 移除markdown代码块标记
        # 匹配 ```json ... ``` 或 ``` ... ```
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'`([^`]*)`'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return text.strip()
    
    def _extract_json_from_text(self, text: str) -> str:
        """从文本中提取JSON部分
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            提取的JSON字符串，如果未找到则返回None
        """
        import re
        
        # 寻找JSON对象 { ... }
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        # 尝试解析每个匹配项
        for match in matches:
            try:
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
        
        # 寻找JSON数组 [ ... ]
        array_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
        matches = re.findall(array_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
                
        return None
    
    def _create_fallback_result(self, response: str, patent_number: str) -> Dict[str, Any]:
        """创建备用解析结果
        
        Args:
            response: 原始LLM响应
            patent_number: 专利号
            
        Returns:
            备用结果字典
        """
        return {
            "patent_number": patent_number,
            "group": 1,
            "rules": [
                {
                    "rule": "analysis_failed",
                    "statement": "LLM响应解析失败，需要人工处理",
                    "comment": f"原始响应长度: {len(response)} 字符"
                }
            ],
            "analysis_summary": {
                "status": "parsing_failed",
                "original_response_preview": response[:200] + "..." if len(response) > 200 else response
            }
        }
    
    def _create_minimal_fallback_result(self, patent_number: str, content: str) -> 'RuleGenerationResult':
        """创建最小化备用结果
        
        Args:
            patent_number: 专利号
            content: 内容
            
        Returns:
            最小化的RuleGenerationResult对象
        """
        from ..models.rule_models import ComplexityAnalysis, ComplexityLevel
        
        return RuleGenerationResult(
            patent_number=patent_number,
            llm_model=self.model,
            analysis_confidence=0.0,
            protection_rules=[],
            complexity_analysis=ComplexityAnalysis(
                complexity_level=ComplexityLevel.SIMPLE,
                complexity_score=0.0,
                mutation_count=0,
                combination_complexity=0,
                dependency_depth=0,
                representation_suggestion="parsing_failed",
                reasoning="LLM响应解析失败"
            ),
            avoidance_strategies=[],
            analysis_summary={"status": "parsing_failed", "content_preview": content[:200]},
            llm_reasoning="解析失败，保留原始内容"
        )
    
    def test_connection(self) -> bool:
        """测试LLM连接
        
        Returns:
            连接是否成功
        """
        try:
            response = self._call_llm("请回复'连接成功'")
            return "连接成功" in response or "connection" in response.lower()
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
