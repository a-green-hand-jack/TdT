#!/usr/bin/env python3
"""
使用CN202210107337数据测试完整的Agent系统

这个脚本使用较小的CN202210107337数据集来验证我们的完整Agent系统，
并将分析结果保存到output/strategy目录中。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tdt.core.data_loader import DataLoader
from tdt.core.llm_agent import LLMRuleAgent
from tdt.core.rule_generator import IntelligentRuleGenerator


def test_cn202210107337_system():
    """使用CN202210107337数据测试完整的Agent系统"""
    print("🧬 CN202210107337 Agent系统测试")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = Path("output/strategy")
    output_dir.mkdir(exist_ok=True)
    
    # 读取API密钥
    with open('qwen_key', 'r') as f:
        api_key = f.read().strip()
    
    # 设置环境变量
    os.environ['QWEN_API_KEY'] = api_key
    
    try:
        # 1. 初始化系统组件
        print("🔧 初始化系统组件...")
        data_loader = DataLoader()
        llm_agent = LLMRuleAgent(api_key=api_key, model="qwen-plus")
        rule_generator = IntelligentRuleGenerator(llm_agent)
        
        # 2. 加载CN202210107337数据
        print("📁 加载CN202210107337数据...")
        
        # 加载权利要求书
        claims_path = Path("output/markdowns/CN202210107337_claims.md")
        print(f"   📄 权利要求书: {claims_path}")
        claims_doc = data_loader.load_claims_markdown(claims_path)
        
        # 加载标准化序列JSON
        sequence_path = Path("output/sequences/CN202210107337.json")
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
        
        # 3. 使用智能规则生成器进行完整分析
        print("\n🤖 使用智能规则生成器进行分析...")
        
        generated_rules = rule_generator.generate_rules_from_patent(
            str(claims_path), str(sequence_path), str(rules_path)
        )
        
        # 获取原始LLM响应用于简化格式导出
        raw_llm_response = getattr(generated_rules, 'raw_llm_response', None)
        print(f"🔍 原始LLM响应预览: {raw_llm_response[:200] if raw_llm_response else '无响应'}...")
        
        print("✅ 规则生成完成！")
        print(f"   生成规则数: {len(generated_rules.protection_rules)}")
        print(f"   分析置信度: {generated_rules.analysis_confidence:.2%}")
        print(f"   复杂度级别: {generated_rules.complexity_analysis.complexity_level}")
        print(f"   回避策略数: {len(generated_rules.avoidance_strategies)}")
        
        # 4. 保存结果到output/strategy
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存简化JSON格式的规则
        json_output_path = output_dir / f"CN202210107337_rules_{timestamp}.json"
        rule_generator.export_simplified_json(generated_rules, str(json_output_path), raw_llm_response)
        print(f"\n💾 简化JSON规则已保存: {json_output_path}")
        
        # 读取简化JSON用于Markdown生成
        simplified_data = None
        try:
            with open(json_output_path, 'r', encoding='utf-8') as f:
                simplified_data = json.load(f)
        except Exception as e:
            print(f"   ⚠️ 简化JSON读取失败: {e}")
        
        # 保存简化Markdown格式的报告
        md_output_path = output_dir / f"CN202210107337_analysis_{timestamp}.md"
        rule_generator.export_to_markdown(generated_rules, str(md_output_path), simplified_data)
        print(f"📄 Markdown报告已保存: {md_output_path}")
        
        # 生成分析报告
        analysis_report = rule_generator.generate_analysis_report(generated_rules)
        report_path = output_dir / f"CN202210107337_report_{timestamp}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(analysis_report)
        print(f"📊 分析报告已保存: {report_path}")
        
        # 5. 显示主要结果
        display_results_summary(generated_rules)
        
        # 6. 创建结果索引文件
        create_results_index(output_dir, timestamp, {
            'json_rules': json_output_path.name,
            'markdown_analysis': md_output_path.name,
            'text_report': report_path.name,
            'patent_number': claims_doc.patent_number,
            'analysis_time': datetime.now().isoformat(),
            'rules_count': len(generated_rules.protection_rules),
            'confidence': generated_rules.analysis_confidence
        })
        
        print(f"\n✅ 完整测试成功完成！")
        print(f"📁 所有结果已保存到: {output_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def display_results_summary(rules):
    """显示结果摘要"""
    print("\n📋 分析结果摘要:")
    print("=" * 50)
    
    print(f"📄 专利号: {rules.patent_number}")
    print(f"🎯 分析置信度: {rules.analysis_confidence:.2%}")
    print(f"⏱️ 分析时间: {rules.generation_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 复杂度分析
    complexity = rules.complexity_analysis
    print(f"\n📈 复杂度分析:")
    print(f"   复杂度级别: {complexity.complexity_level}")
    print(f"   复杂度评分: {complexity.complexity_score:.1f}/10")
    print(f"   突变位点数: {complexity.mutation_count}")
    print(f"   表达建议: {complexity.representation_suggestion}")
    
    # 保护规则摘要
    if rules.protection_rules:
        print(f"\n🛡️ 保护规则 ({len(rules.protection_rules)}条):")
        for i, rule in enumerate(rules.protection_rules[:3], 1):  # 显示前3条
            print(f"   规则 {i}: {rule.rule_id}")
            print(f"      类型: {rule.rule_type}")
            print(f"      保护范围: {rule.protection_scope}")
            print(f"      复杂度: {rule.complexity_score:.1f}/10")
            if hasattr(rule, 'identity_threshold') and rule.identity_threshold:
                print(f"      同一性阈值: {rule.identity_threshold:.1%}")
    
    # 回避策略摘要
    if rules.avoidance_strategies:
        print(f"\n🎯 回避策略 ({len(rules.avoidance_strategies)}个):")
        for i, strategy in enumerate(rules.avoidance_strategies[:2], 1):  # 显示前2个
            print(f"   策略 {i}: {strategy.strategy_type}")
            print(f"      描述: {strategy.description[:80]}...")
            print(f"      置信度: {strategy.confidence_score:.2%}")


def create_results_index(output_dir, timestamp, info):
    """创建结果索引文件"""
    index_path = output_dir / "results_index.json"
    
    # 读取现有索引
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    else:
        index_data = {"analyses": []}
    
    # 添加新的分析记录
    index_data["analyses"].append({
        "timestamp": timestamp,
        "files": info,
        "summary": {
            "patent": info['patent_number'],
            "rules": info['rules_count'],
            "confidence": info['confidence']
        }
    })
    
    # 保存索引
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"📇 结果索引已更新: {index_path}")


def main():
    print("🚀 启动CN202210107337 Agent系统测试...")
    print("这将验证我们的完整工具链并保存结果到output/strategy目录")
    print()
    
    if test_cn202210107337_system():
        print("\n✅ CN202210107337 Agent系统测试成功！")
        print("\n💡 测试验证了以下功能:")
        print("• DataLoader - 成功加载权利要求书和序列数据")
        print("• LLMRuleAgent - 智能分析专利内容")
        print("• IntelligentRuleGenerator - 生成完整的保护规则")
        print("• 专用提示模板 - 确保高质量的LLM响应")
        print("• 多格式输出 - JSON、Markdown、Text报告")
        print("• 结果管理 - 时间戳、索引、组织化存储")
        print("\n🔧 下一步:")
        print("可以在output/strategy目录中查看完整的分析结果！")
    else:
        print("\n❌ 测试失败，请检查错误信息")


if __name__ == "__main__":
    main()
