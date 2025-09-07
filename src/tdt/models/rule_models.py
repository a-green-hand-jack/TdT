"""
规则数据模型

定义专利保护规则、复杂度分析、回避策略等数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RuleType(str, Enum):
    """规则类型枚举"""
    SEQUENCE_IDENTITY = "sequence_identity"
    MUTATION_PATTERN = "mutation_pattern"
    FUNCTIONAL_DOMAIN = "functional_domain"
    COMPOSITIONAL = "compositional"
    HYBRID = "hybrid"


class ProtectionScope(str, Enum):
    """保护范围枚举"""
    IDENTICAL = "identical"           # 完全相同
    IDENTITY_THRESHOLD = "identity_threshold"  # 相似度阈值
    EXCLUDE_MUTATIONS = "exclude_mutations"    # 排除特定突变
    INCLUDE_VARIANTS = "include_variants"      # 包含变体


class ComplexityLevel(str, Enum):
    """复杂度级别"""
    SIMPLE = "simple"       # 简单：1-3个突变位点
    MODERATE = "moderate"   # 中等：4-10个突变位点
    COMPLEX = "complex"     # 复杂：10+个突变位点或复合条件


class MutationInfo(BaseModel):
    """突变信息"""
    position: int = Field(..., description="氨基酸位置")
    original: str = Field(..., description="原始氨基酸")
    mutated: str = Field(..., description="突变后氨基酸")
    mutation_code: str = Field(..., description="突变代码，如W46E")
    is_critical: bool = Field(default=False, description="是否为关键位点")


class MutationCombination(BaseModel):
    """突变组合"""
    mutations: List[MutationInfo] = Field(..., description="突变列表")
    combination_type: str = Field(..., description="组合类型：all_required, any_sufficient等")
    pattern_description: str = Field(..., description="模式描述")


class ProtectionRule(BaseModel):
    """保护规则"""
    rule_id: str = Field(..., description="规则唯一标识")
    rule_type: RuleType = Field(..., description="规则类型")
    protection_scope: ProtectionScope = Field(..., description="保护范围")
    
    # 目标序列
    target_sequences: List[str] = Field(..., description="目标序列ID列表")
    reference_seq_ids: List[str] = Field(default_factory=list, description="相关SEQ ID NO")
    
    # 突变相关
    mutation_combinations: List[MutationCombination] = Field(default_factory=list, description="突变组合")
    critical_positions: List[int] = Field(default_factory=list, description="关键位点")
    
    # 阈值设定
    identity_threshold: Optional[float] = Field(None, description="相似度阈值，如0.70表示70%")
    length_constraints: Optional[Dict[str, int]] = Field(None, description="长度约束")
    
    # 复杂度评估
    complexity_score: float = Field(..., description="复杂度评分 0-10")
    complexity_level: ComplexityLevel = Field(..., description="复杂度级别")
    
    # 法律描述
    legal_description: str = Field(..., description="法律语言描述")
    technical_description: str = Field(..., description="技术语言描述")
    
    @property
    def total_mutation_positions(self) -> int:
        """获取涉及的突变位点总数"""
        positions = set()
        for combination in self.mutation_combinations:
            for mutation in combination.mutations:
                positions.add(mutation.position)
        return len(positions)


class AvoidanceStrategy(BaseModel):
    """回避策略"""
    strategy_type: str = Field(..., description="策略类型")
    description: str = Field(..., description="策略描述")
    implementation_suggestions: List[str] = Field(..., description="实施建议")
    risk_assessment: str = Field(..., description="风险评估")
    confidence_score: float = Field(..., description="置信度评分 0-1")


class ComplexityAnalysis(BaseModel):
    """复杂度分析"""
    complexity_level: ComplexityLevel = Field(..., description="复杂度级别")
    complexity_score: float = Field(..., description="复杂度评分")
    
    # 分析维度
    mutation_count: int = Field(..., description="突变位点数量")
    combination_complexity: int = Field(..., description="组合复杂度")
    dependency_depth: int = Field(..., description="依赖深度")
    
    # 表达建议
    representation_suggestion: str = Field(..., description="表达方式建议")
    reasoning: str = Field(..., description="复杂度判断理由")
    
    # 简化建议
    simplification_options: List[str] = Field(default_factory=list, description="简化选项")


class RuleGenerationResult(BaseModel):
    """规则生成结果"""
    patent_number: str = Field(..., description="专利号")
    generation_timestamp: datetime = Field(default_factory=datetime.now, description="生成时间")
    llm_model: str = Field(..., description="使用的LLM模型")
    analysis_confidence: float = Field(..., description="分析置信度")
    
    # 生成的规则
    protection_rules: List[ProtectionRule] = Field(..., description="保护规则列表")
    
    # 分析结果
    complexity_analysis: ComplexityAnalysis = Field(..., description="复杂度分析")
    avoidance_strategies: List[AvoidanceStrategy] = Field(..., description="回避策略")
    
    # 统计摘要
    analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="分析摘要")
    
    # LLM分析过程
    llm_reasoning: str = Field(..., description="LLM推理过程")
    processing_log: List[Dict[str, Any]] = Field(default_factory=list, description="处理日志")
    raw_llm_response: Optional[str] = Field(None, description="原始LLM响应，用于调试")


class StandardizedRuleOutput(BaseModel):
    """标准化规则输出格式"""
    metadata: Dict[str, Any] = Field(..., description="元数据")
    rules: List[ProtectionRule] = Field(..., description="规则列表")
    analysis_summary: Dict[str, Any] = Field(..., description="分析摘要") 
    generation_info: Dict[str, Any] = Field(..., description="生成信息")
    
    class Config:
        # 配置JSON序列化
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
