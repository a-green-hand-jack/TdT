#!/usr/bin/env python3
"""
完整的LLM Agent演示

展示基于Qwen的专利规则生成Agent的完整功能。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from openai import OpenAI


def demo_patent_analysis_with_agent():
    """演示完整的专利分析Agent"""
    print("🧬 TDT专利规则生成Agent - 完整演示")
    print("=" * 60)

    # 读取API密钥
    with open("qwen_key", "r") as f:
        api_key = f.read().strip()

    # 配置Qwen客户端
    client = OpenAI(
        api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 模拟输入数据
    claims_content = """
1. 一种工程化末端脱氧核苷酸转移酶，其特征在于包含与SEQ ID NO:1具有至少95%序列同一性的氨基酸序列，
   其中所述氨基酸序列在以下位置含有突变：Y178A、F186R、I210L、V211A。

2. 根据权利要求1所述的工程化末端脱氧核苷酸转移酶，其特征在于所述氨基酸序列还包含以下至少一个突变：
   K220E、A225V、D230N、R235K。

3. 根据权利要求1或2所述的工程化末端脱氧核苷酸转移酶，其特征在于所述氨基酸序列与SEQ ID NO:1的序列同一性为96%、97%、98%或99%。
"""

    sequence_summary = """
序列信息：
- SEQ ID NO:1 对应 ZaTdT 蛋白质序列
- 长度：519个氨基酸
- 分子量：58,239.81 Da
- 等电点：8.82
- 主要氨基酸：L（亮氨酸）
"""

    existing_rules = """
现有规则模式：
- identical 类型规则：88.9%
- identity>70% 类型规则：11.1%
- 常见突变位点：W46E, Q62W, G70E, A73P等
- 主要保护策略：封闭式序列保护
"""

    # 构建系统提示
    system_prompt = """你是一位资深的专利分析专家和生物技术专家，专门分析TDT酶相关的专利保护规则。

你的任务是分析专利权利要求书和序列数据，提取出关键的保护规则，并生成技术回避策略。

分析原则：
1. 准确理解专利权利要求的法律保护范围
2. 识别关键的序列特征和突变模式
3. 评估规则的复杂度和实施难度
4. 提供可操作的技术回避建议
5. 确保分析结果的科学性和准确性

请始终以JSON格式输出分析结果，确保结构清晰、内容准确。"""

    # 构建专利分析提示
    analysis_prompt = f"""请分析以下专利权利要求书和序列数据，提取保护规则：

## 专利信息
专利号: CN202210107337
权利要求总数: 3
序列总数: 1

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
    "patent_number": "CN202210107337",
    "analysis_confidence": 0.9,
    "key_findings": [
      "识别出的关键保护要素"
    ],
    "protection_strategy": "专利保护策略类型"
  }},
  "sequence_correlations": [
    {{
      "seq_id_no": "SEQ ID NO:1",
      "sequence_id": "ZaTdT",
      "related_claims": [1, 2, 3],
      "key_features": ["关键特征"],
      "mutation_patterns": [
        {{
          "pattern": "Y178A/F186R/I210L/V211A",
          "positions": [178, 186, 210, 211],
          "critical_level": "high"
        }}
      ]
    }}
  ],
  "protection_rules": [
    {{
      "rule_id": "R001",
      "rule_type": "sequence_identity",
      "protection_scope": "identity_threshold",
      "target_sequences": ["ZaTdT"],
      "identity_threshold": 0.95,
      "critical_mutations": ["Y178A", "F186R", "I210L", "V211A"],
      "complexity_score": 6.5,
      "legal_description": "保护具有至少95%序列同一性且包含特定突变的TDT酶变体",
      "technical_description": "通过序列同一性阈值和关键突变位点组合实现保护"
    }}
  ],
  "complexity_analysis": {{
    "overall_complexity": "moderate",
    "complexity_score": 6.5,
    "factors": {{
      "mutation_count": 4,
      "combination_complexity": 3,
      "sequence_diversity": 2
    }},
    "representation_suggestion": "采用突变位点列表方式表达",
    "reasoning": "涉及4个关键突变位点，复杂度适中，适合具体列举"
  }},
  "avoidance_strategies": [
    {{
      "strategy_type": "sequence_modification",
      "description": "通过改变非关键位点实现功能保持的同时规避专利",
      "implementation_suggestions": [
        "选择Y178以外的178位点突变（如Y178F）",
        "在非保护区域添加额外有益突变",
        "调整序列同一性至94%以下"
      ],
      "risk_assessment": "中等风险，需要功能验证",
      "confidence_score": 0.8
    }}
  ],
  "analysis_summary": {{
    "total_protected_sequences": 1,
    "key_mutation_positions": [178, 186, 210, 211, 220, 225, 230, 235],
    "protection_breadth": "medium",
    "recommended_approach": "位点替代策略"
  }}
}}
```

请确保所有数值在合理范围内，分析结果具有实际指导意义。"""

    try:
        print("🔍 正在使用LLM Agent分析专利数据...")

        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analysis_prompt},
            ],
            temperature=0.3,
            max_tokens=3000,
        )

        analysis_text = response.choices[0].message.content

        print("✅ LLM分析完成！")

        # 尝试解析JSON响应
        try:
            # 提取JSON部分
            if "```json" in analysis_text:
                json_start = analysis_text.find("```json") + 7
                json_end = analysis_text.find("```", json_start)
                json_text = analysis_text[json_start:json_end].strip()
            else:
                json_text = analysis_text

            analysis_result = json.loads(json_text)

            print("\n📊 专利分析结果JSON:")
            print("-" * 50)
            print(json.dumps(analysis_result, ensure_ascii=False, indent=2))
            print("-" * 50)

            # 生成结构化报告
            generate_analysis_report(analysis_result)

            # 生成回避策略详情
            generate_avoidance_strategies(client, system_prompt, analysis_result)

            return True

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败，显示原始响应: {e}")
            print("\n📝 LLM原始响应:")
            print("-" * 50)
            print(analysis_text)
            print("-" * 50)
            return True

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return False


def generate_analysis_report(analysis_result):
    """生成结构化分析报告"""
    print("\n📋 结构化分析报告:")
    print("=" * 50)

    # 基本信息
    patent_info = analysis_result.get("patent_analysis", {})
    print(f"📄 专利号: {patent_info.get('patent_number', 'N/A')}")
    print(f"🎯 分析置信度: {patent_info.get('analysis_confidence', 0):.1%}")
    print(f"🔒 保护策略: {patent_info.get('protection_strategy', 'N/A')}")

    # 保护规则
    rules = analysis_result.get("protection_rules", [])
    if rules:
        print(f"\n🛡️ 保护规则 ({len(rules)}条):")
        for i, rule in enumerate(rules, 1):
            print(
                f"  {i}. {rule.get('rule_id', 'N/A')} - {rule.get('rule_type', 'N/A')}"
            )
            print(f"     复杂度: {rule.get('complexity_score', 0):.1f}/10")
            print(f"     保护范围: {rule.get('protection_scope', 'N/A')}")
            if rule.get("identity_threshold"):
                print(f"     同一性阈值: {rule.get('identity_threshold', 0):.1%}")

    # 复杂度分析
    complexity = analysis_result.get("complexity_analysis", {})
    if complexity:
        print(f"\n📈 复杂度分析:")
        print(f"  总体复杂度: {complexity.get('overall_complexity', 'N/A')}")
        print(f"  复杂度评分: {complexity.get('complexity_score', 0):.1f}/10")
        print(f"  表达建议: {complexity.get('representation_suggestion', 'N/A')}")

    # 关键发现
    key_findings = patent_info.get("key_findings", [])
    if key_findings:
        print(f"\n🔍 关键发现:")
        for finding in key_findings:
            print(f"  • {finding}")


def generate_avoidance_strategies(client, system_prompt, analysis_result):
    """生成详细的回避策略"""
    print("\n🎯 生成详细回避策略...")

    strategies_prompt = f"""基于以下专利分析结果，请为每个回避策略提供更详细的技术实施方案：

分析结果：
{json.dumps(analysis_result, ensure_ascii=False, indent=2)}

请为每个回避策略提供：
1. 具体的突变位点建议
2. 预期的功能影响评估
3. 实验验证步骤
4. 风险评估和缓解措施
5. 成功概率评估

请以结构化的方式回答。"""

    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": strategies_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        strategies_text = response.choices[0].message.content

        print("✅ 详细回避策略生成完成！")
        print("\n🛡️ 技术回避策略详情:")
        print("-" * 50)
        print(strategies_text)
        print("-" * 50)

    except Exception as e:
        print(f"⚠️ 回避策略生成失败: {e}")


def main():
    print("🚀 启动完整的LLM Agent演示...")

    if demo_patent_analysis_with_agent():
        print("\n✅ Agent演示完成！")
        print("\n💡 Agent系统特点:")
        print("• 智能理解专利权利要求书")
        print("• 自动识别关键突变模式")
        print("• 评估保护规则复杂度")
        print("• 生成具体的技术回避策略")
        print("• 提供JSON格式的结构化输出")
        print("\n🔧 实际使用:")
        print("使用 'tdt-rules generate-rules' 命令进行完整的专利分析")
    else:
        print("\n❌ Agent演示失败")


if __name__ == "__main__":
    main()
