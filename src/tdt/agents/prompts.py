"""
LLM提示模板

为Qwen模型设计的专利规则分析提示模板。
"""

SYSTEM_PROMPT = """你是专利序列保护分析专家。你的任务是识别专利权利要求对序列的保护范围，并使用结构化的逻辑表达式描述保护规则。

核心任务：
1. 识别专利保护的野生型序列（wild_type）
2. 识别专利保护的突变模式（mutation patterns）
3. 将复杂的保护条件转化为逻辑表达式
4. 确定保护规则类型（identical, identity>X%, conditional等）

输出要求：
1. 仅关注保护内容，不提供回避建议或复杂度分析
2. 使用逻辑操作符（&, |, !, ()）表达复杂规则
3. 按照group-patent-rule的层次结构组织信息
4. 使用简洁明确的语言，避免冗余信息

逻辑表达规范：
- 突变位点格式：Y178A（原氨基酸+位置+新氨基酸）
- 组合突变：(Y178A & F186R) 表示同时突变
- 可选突变：(Y178A | Y178F) 表示任一突变
- 复合条件：mutation_logic AND identity_logic
- 排除条件：NOT excluded_mutations

请始终输出简洁的JSON格式结果。"""


PATENT_ANALYSIS_PROMPT = """请分析以下专利权利要求书和序列数据，识别保护规则：

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

请分析专利保护范围，重点回答以下4个核心问题：
1. Wild_type: 这个专利保护哪个（些）野生型序列？
2. Protection_scope: 保护范围是什么（identical/identity>X%/conditional）？  
3. Mutation_rules: 突变规则是什么（用逻辑表达式）？
4. Key_conditions: 关键保护条件是什么？

输出格式（必须严格按照此JSON结构）：

```json
{{
  "patent_number": "{patent_number}",
  "group": 1,
  "rules": [
    {{
      "wild_type": "SEQ_ID_NO_1或序列标识",
      "rule": "identical 或 identity>80 或 conditional_protection",
      "mutation": "Y178A/F186R/I210L/I228L",
      "mutation_logic": "(Y178A & F186R) | (I210L & I228L)",
      "identity_logic": "seq_identity >= 80%",
      "statement": "简洁描述这个专利对序列的保护内容",
      "comment": "保护策略的简短说明（封闭式/开放式/混合式）"
    }}
  ]
}}
```

重要说明：
1. 每个规则对应一种保护模式
2. mutation字段用斜杠分隔的标准格式：Y178A/F186R
3. mutation_logic字段用逻辑表达式：(Y178A & F186R) | (I210L & I228L)
4. 如果专利有多种保护策略，rules数组包含多个对象
5. statement字段要用最简洁的语言说明"专利对序列产生了哪些保护"
6. 避免生成回避策略、复杂度分析等无关内容

逻辑操作符使用规范：
- & 或 AND：同时满足
- | 或 OR：满足任一 
- !或 NOT：排除
- ()：逻辑分组
"""


# 注意：根据新的需求，我们不再需要复杂度分析和回避策略提示模板
# 这些功能已被移除，Agent专注于识别保护范围


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
