"""
LLM提示模板

为Qwen模型设计的专利规则分析提示模板。
"""

SYSTEM_PROMPT = """你是一位资深的专利分析专家和生物技术专家，专门分析TDT酶相关的专利保护规则。

你的任务是分析专利权利要求书和序列数据，提取出关键的保护规则，并生成技术回避策略。

分析原则：
1. 准确理解专利权利要求的法律保护范围
2. 识别关键的序列特征和突变模式
3. 评估规则的复杂度和实施难度
4. 提供可操作的技术回避建议
5. 确保分析结果的科学性和准确性

请始终以JSON格式输出分析结果，确保结构清晰、内容准确。"""


PATENT_ANALYSIS_PROMPT = """请分析以下专利权利要求书和序列数据，提取保护规则：

## 专利信息
专利号: {patent_number}
权利要求总数: {total_claims}
序列总数: {total_sequences}

## 权利要求书内容
{claims_content}

## 序列数据摘要
{sequence_summary}

## 现有规则参考
{existing_rules}

## 分析要求

请按照以下结构分析并输出JSON格式结果：

```json
{{
  "patent_analysis": {{
    "patent_number": "{patent_number}",
    "analysis_confidence": 0.0,
    "key_findings": [
      "发现的关键保护要素"
    ],
    "protection_strategy": "专利保护策略类型（封闭式/开放式/混合式）"
  }},
  "sequence_correlations": [
    {{
      "seq_id_no": "SEQ ID NO:X",
      "sequence_id": "序列标识",
      "related_claims": [权利要求编号],
      "key_features": ["关键特征"],
      "mutation_patterns": [
        {{
          "pattern": "突变模式",
          "positions": [位点列表],
          "critical_level": "high/medium/low"
        }}
      ]
    }}
  ],
  "protection_rules": [
    {{
      "rule_id": "R001",
      "rule_type": "sequence_identity/mutation_pattern/compositional",
      "protection_scope": "identical/identity_threshold/exclude_mutations",
      "target_sequences": ["目标序列ID"],
      "mutation_combinations": [
        {{
          "mutations": ["W46E", "Q62W"],
          "combination_type": "all_required/any_sufficient",
          "description": "组合描述"
        }}
      ],
      "identity_threshold": 0.70,
      "complexity_score": 5.5,
      "legal_description": "法律语言描述",
      "technical_description": "技术语言描述"
    }}
  ],
  "complexity_analysis": {{
    "overall_complexity": "simple/moderate/complex",
    "complexity_score": 0.0,
    "factors": {{
      "mutation_count": 0,
      "combination_complexity": 0,
      "sequence_diversity": 0
    }},
    "representation_suggestion": "建议的表达方式",
    "reasoning": "复杂度判断理由"
  }},
  "avoidance_strategies": [
    {{
      "strategy_type": "sequence_modification/alternative_approach/design_around",
      "description": "策略描述",
      "implementation_suggestions": ["具体实施建议"],
      "risk_assessment": "风险评估",
      "confidence_score": 0.85
    }}
  ],
  "analysis_summary": {{
    "total_protected_sequences": 0,
    "key_mutation_positions": [关键位点],
    "protection_breadth": "narrow/medium/broad",
    "recommended_approach": "推荐的技术路径"
  }}
}}
```

请确保：
1. 所有numeric_id必须是整数
2. 所有confidence_score和complexity_score在0-1或0-10范围内
3. 突变位点必须是具体的数字
4. 法律描述要准确反映专利保护范围
5. 技术描述要便于工程师理解和实施
"""


COMPLEXITY_EVALUATION_PROMPT = """请评估以下专利规则的复杂度：

## 规则信息
{rule_info}

## 评估标准
- 简单(Simple): 1-3个突变位点，单一保护模式
- 中等(Moderate): 4-10个突变位点，少量组合条件
- 复杂(Complex): 10+个突变位点，多重组合条件或复合保护策略

请提供详细的复杂度分析：

```json
{{
  "complexity_analysis": {{
    "complexity_level": "simple/moderate/complex",
    "complexity_score": 0.0,
    "factors": {{
      "mutation_count": 0,
      "combination_complexity": 0,
      "dependency_depth": 0,
      "sequence_diversity": 0
    }},
    "representation_suggestion": "建议使用的表达方式",
    "reasoning": "详细的判断理由",
    "simplification_options": ["可能的简化选项"]
  }}
}}
```
"""


AVOIDANCE_STRATEGY_PROMPT = """基于以下专利保护规则，请生成技术回避策略：

## 保护规则
{protection_rules}

## 序列信息
{sequence_info}

请生成具体的回避策略：

```json
{{
  "avoidance_strategies": [
    {{
      "strategy_type": "sequence_modification",
      "description": "策略的详细描述",
      "implementation_suggestions": [
        "具体的实施步骤",
        "需要注意的技术要点"
      ],
      "risk_assessment": "实施风险评估",
      "confidence_score": 0.85,
      "expected_effectiveness": "预期有效性评估"
    }}
  ],
  "priority_recommendations": [
    "按优先级排序的推荐方案"
  ],
  "technical_considerations": [
    "需要考虑的技术因素"
  ]
}}
```
"""


def format_claims_for_llm(claims_doc) -> str:
    """格式化权利要求书内容供LLM分析"""
    content_parts = []
    
    for claim in claims_doc.claims:
        part = f"权利要求 {claim.claim_number} ({claim.claim_type}):\n"
        if claim.dependencies:
            part += f"依据: 权利要求 {', '.join(map(str, claim.dependencies))}\n"
        part += f"内容: {claim.content}\n"
        
        if claim.seq_id_references:
            seq_refs = [ref.seq_id_no for ref in claim.seq_id_references]
            part += f"涉及序列: {', '.join(seq_refs)}\n"
        
        if claim.mutation_patterns:
            mutations = []
            for pattern in claim.mutation_patterns:
                mutations.extend(pattern.mutations)
            part += f"突变模式: {', '.join(mutations)}\n"
        
        part += "\n"
        content_parts.append(part)
    
    return "\n".join(content_parts)


def format_sequence_summary(sequence_result) -> str:
    """格式化序列数据摘要"""
    summary_parts = []
    
    summary_parts.append(f"总序列数: {len(sequence_result.sequences)}")
    summary_parts.append(f"序列类型分布: {sequence_result.statistics.sequence_types}")
    
    for i, seq in enumerate(sequence_result.sequences[:5]):  # 只显示前5个
        part = f"序列 {i+1}: {seq.sequence_id}"
        part += f" (长度: {seq.sequence_data.length}, 类型: {seq.sequence_data.molecular_type})"
        if hasattr(seq.sequence_data, 'composition') and seq.sequence_data.composition:
            most_freq = seq.sequence_data.composition.most_frequent
            part += f" (主要氨基酸: {most_freq})"
        summary_parts.append(part)
    
    if len(sequence_result.sequences) > 5:
        summary_parts.append(f"... 还有 {len(sequence_result.sequences) - 5} 个序列")
    
    return "\n".join(summary_parts)


def format_existing_rules(existing_rules_data) -> str:
    """格式化现有规则数据"""
    if not existing_rules_data or 'rules' not in existing_rules_data:
        return "无现有规则数据"
    
    rules = existing_rules_data['rules']
    summary_parts = []
    
    summary_parts.append(f"现有规则总数: {len(rules)}")
    
    # 统计规则类型
    rule_types = {}
    for rule in rules:
        rule_type = rule.get('rule', 'unknown')
        rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
    
    summary_parts.append("规则类型分布:")
    for rule_type, count in rule_types.items():
        summary_parts.append(f"  {rule_type}: {count}")
    
    # 显示几个典型规则示例
    summary_parts.append("\n典型规则示例:")
    for i, rule in enumerate(rules[:3]):
        part = f"规则 {i+1}: {rule.get('patent_number', 'N/A')}"
        part += f" - {rule.get('rule', 'N/A')}"
        if rule.get('mutant') and rule.get('mutant') != '-':
            part += f" (突变: {rule.get('mutant')[:50]}...)"
        summary_parts.append(part)
    
    return "\n".join(summary_parts)
