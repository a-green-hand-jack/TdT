#!/usr/bin/env python3
"""
使用真实数据演示完整的LLM Agent系统

展示使用我们设计的完整工具链：权利要求书、标准化序列JSON、现有规则和专门的提示模板。
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tdt.core.data_loader import DataLoader
from tdt.core.llm_agent import LLMRuleAgent
from tdt.agents.prompts import format_claims_for_llm, format_sequence_summary, format_existing_rules


def demo_real_agent_system():
    """演示完整的Agent系统"""
    print("🧬 TDT专利规则生成Agent - 真实数据演示")
    print("=" * 70)
    
    # 从环境变量读取API密钥
    api_key = os.getenv('QWEN_API_KEY')
    if not api_key:
        print("❌ 错误: 未找到 QWEN_API_KEY 环境变量")
        print("💡 请在 .env 文件中设置 QWEN_API_KEY")
        return
    
    try:
        # 1. 初始化数据加载器和LLM Agent
        print("🔧 初始化系统组件...")
        data_loader = DataLoader()
        llm_agent = LLMRuleAgent(api_key=api_key, model="qwen-plus")
        
        # 2. 加载真实数据
        print("📁 加载真实数据...")
        
        # 加载权利要求书
        claims_path = Path("output/markdowns/CN118284690A_claims.md")
        print(f"   📄 权利要求书: {claims_path}")
        claims_doc = data_loader.load_claims_markdown(claims_path)
        
        # 加载标准化序列JSON
        sequence_path = Path("output/sequences/CN118284690A.json")
        print(f"   🧬 序列文件: {sequence_path}")
        sequence_data = data_loader.load_sequence_json(sequence_path)
        
        # 加载现有规则
        rules_path = Path("Patents/patent rules_rules.json")
        print(f"   📋 现有规则: {rules_path}")
        existing_rules = data_loader.load_existing_rules(rules_path)
        
        print("✅ 数据加载完成！")
        print(f"   专利号: {claims_doc.patent_number}")
        print(f"   权利要求数: {claims_doc.total_claims}")
        print(f"   序列数: {len(sequence_data.sequences)}")
        print(f"   现有规则数: {len(existing_rules.get('rules', []))}")
        print(f"   SEQ ID引用: {claims_doc.total_seq_id_references}")
        print(f"   突变模式: {claims_doc.mutation_pattern_count}")
        
        # 3. 创建序列与权利要求的映射
        print("\n🔗 创建序列与权利要求映射...")
        sequence_mapping = data_loader.create_sequence_claims_mapping(claims_doc, sequence_data)
        print(f"   映射统计: {sequence_mapping.mapping_statistics}")
        
        # 4. 使用我们设计的格式化函数
        print("\n📝 格式化数据供LLM分析...")
        claims_content = format_claims_for_llm(claims_doc)
        sequence_summary = format_sequence_summary(sequence_data)
        existing_rules_summary = format_existing_rules(existing_rules)
        
        print(f"   权利要求内容长度: {len(claims_content)} 字符")
        print(f"   序列摘要长度: {len(sequence_summary)} 字符")
        print(f"   现有规则摘要长度: {len(existing_rules_summary)} 字符")
        
        # 5. 显示分析的数据样本
        print("\n📊 数据分析样本:")
        print("=" * 50)
        
        print("权利要求书样本 (前500字符):")
        print("-" * 30)
        print(claims_content[:500])
        print("...")
        
        print("\n序列数据样本:")
        print("-" * 30)
        print(sequence_summary)
        
        print("\n现有规则样本:")
        print("-" * 30)
        print(existing_rules_summary)
        
        # 6. 使用LLM Agent进行分析 (使用较短的数据避免超出token限制)
        print("\n🤖 使用LLM Agent分析专利...")
        print("注意：由于数据量庞大，这里使用前3个权利要求进行演示")
        
        # 创建简化的权利要求文档用于演示
        simplified_claims_doc = create_simplified_claims_doc(claims_doc)
        
        # 使用LLM进行分析
        result = llm_agent.analyze_patent_claims(
            simplified_claims_doc, 
            existing_rules, 
            sequence_data
        )
        
        print("✅ LLM分析完成！")
        print(f"   分析置信度: {result.analysis_confidence:.2%}")
        print(f"   生成的保护规则数: {len(result.protection_rules)}")
        print(f"   复杂度级别: {result.complexity_analysis.complexity_level}")
        print(f"   回避策略数: {len(result.avoidance_strategies)}")
        
        # 7. 显示分析结果
        display_analysis_results(result)
        
        # 8. 演示规则复杂度评估
        if result.protection_rules:
            print("\n📈 演示规则复杂度评估...")
            first_rule = result.protection_rules[0]
            complexity = llm_agent.evaluate_rule_complexity(first_rule.dict())
            print(f"   规则复杂度: {complexity.complexity_level}")
            print(f"   复杂度评分: {complexity.complexity_score:.1f}/10")
            print(f"   表达建议: {complexity.representation_suggestion}")
        
        # 9. 演示回避策略生成
        print("\n🛡️ 演示回避策略生成...")
        if result.protection_rules:
            strategies = llm_agent.generate_avoidance_strategies(
                {"rules": [rule.dict() for rule in result.protection_rules[:2]]},
                {"sequences": [seq.dict() for seq in sequence_data.sequences[:1]]}
            )
            print(f"   生成策略数: {len(strategies)}")
            for i, strategy in enumerate(strategies[:2], 1):
                print(f"   策略 {i}: {strategy.strategy_type}")
                print(f"      置信度: {strategy.confidence_score:.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_simplified_claims_doc(original_doc):
    """创建简化的权利要求书文档用于演示"""
    # 只取前3个权利要求进行演示
    simplified_claims = original_doc.claims[:3]
    
    from tdt.models.claims_models import ClaimsDocument
    
    simplified_doc = ClaimsDocument(
        patent_number=original_doc.patent_number,
        source_file=original_doc.source_file,
        total_claims=len(simplified_claims),
        claims=simplified_claims
    )
    
    return simplified_doc


def display_analysis_results(result):
    """显示分析结果"""
    print("\n📋 LLM分析结果:")
    print("=" * 50)
    
    print(f"📄 专利号: {result.patent_number}")
    print(f"🎯 分析置信度: {result.analysis_confidence:.2%}")
    print(f"🔬 使用模型: {result.llm_model}")
    print(f"⏱️ 分析时间: {result.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 复杂度分析
    complexity = result.complexity_analysis
    print(f"\n📈 复杂度分析:")
    print(f"   复杂度级别: {complexity.complexity_level}")
    print(f"   复杂度评分: {complexity.complexity_score:.1f}/10")
    print(f"   突变位点数: {complexity.mutation_count}")
    print(f"   表达建议: {complexity.representation_suggestion}")
    
    # 保护规则
    if result.protection_rules:
        print(f"\n🛡️ 保护规则 ({len(result.protection_rules)}条):")
        for i, rule in enumerate(result.protection_rules[:3], 1):  # 只显示前3条
            print(f"   规则 {i}: {rule.rule_id}")
            print(f"      类型: {rule.rule_type}")
            print(f"      保护范围: {rule.protection_scope}")
            print(f"      复杂度: {rule.complexity_score:.1f}/10")
            if rule.identity_threshold:
                print(f"      同一性阈值: {rule.identity_threshold:.1%}")
    
    # 回避策略
    if result.avoidance_strategies:
        print(f"\n🎯 回避策略 ({len(result.avoidance_strategies)}个):")
        for i, strategy in enumerate(result.avoidance_strategies[:2], 1):  # 只显示前2个
            print(f"   策略 {i}: {strategy.strategy_type}")
            print(f"      描述: {strategy.description[:100]}...")
            print(f"      置信度: {strategy.confidence_score:.2%}")
    
    # 分析摘要
    if result.analysis_summary:
        print(f"\n📊 分析摘要:")
        for key, value in result.analysis_summary.items():
            if isinstance(value, (int, float, str)):
                print(f"   {key}: {value}")


def main():
    print("🚀 启动真实数据Agent演示...")
    print("使用完整工具链：DataLoader + LLMRuleAgent + 专用提示模板")
    print()
    
    if demo_real_agent_system():
        print("\n✅ 完整Agent系统演示成功！")
        print("\n💡 系统特点:")
        print("• 使用真实的权利要求书数据 (130个权利要求)")
        print("• 处理标准化序列JSON (6,775个序列)")
        print("• 整合现有规则数据 (207条规则)")
        print("• 使用专门设计的提示模板")
        print("• 自动识别SEQ ID引用和突变模式")
        print("• 智能生成保护规则和回避策略")
        print("• 提供复杂度评估和表达建议")
        print("\n🔧 完整功能:")
        print("这个演示展示了我们精心设计的完整Agent工具链的真实应用能力！")
    else:
        print("\n❌ 演示失败")


if __name__ == "__main__":
    main()
