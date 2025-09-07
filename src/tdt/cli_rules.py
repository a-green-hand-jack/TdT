"""
序列规则提炼命令行工具

提供专利规则分析和序列规则提炼的命令行接口。
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from tdt.core.excel_converter import ExcelToJsonConverter

logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='启用详细日志输出')
def cli(verbose: bool):
    """TDT专利序列规则提炼工具"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@cli.command()
@click.argument('excel_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='输出JSON文件路径')
@click.option('--stats', is_flag=True, help='显示详细统计信息')
def convert_excel(excel_file: Path, output: Optional[Path], stats: bool):
    """转换Excel专利规则文件为JSON格式
    
    EXCEL_FILE: 输入的Excel文件路径
    """
    try:
        # 设置默认输出路径
        if output is None:
            output = excel_file.parent / f"{excel_file.stem}_rules.json"
        
        # 执行转换
        click.echo(f"正在转换Excel文件: {excel_file}")
        converter = ExcelToJsonConverter()
        result = converter.convert(excel_file)
        
        # 导出JSON
        converter.export_json(output)
        
        # 显示基本信息
        click.echo(f"✅ 转换完成！JSON文件已保存至: {output}")
        
        # 显示统计信息
        statistics = converter.get_statistics()
        click.echo(f"\n📊 基本统计:")
        click.echo(f"  总规则数: {statistics['total_rules']}")
        click.echo(f"  分组数: {statistics['total_groups']}")
        click.echo(f"  专利数: {statistics['patent_count']}")
        
        if stats:
            click.echo(f"\n📈 详细统计:")
            click.echo(f"  规则类型分布:")
            for rule_type, count in statistics['rule_types'].items():
                click.echo(f"    {rule_type}: {count}")
            
            # 显示部分数据样例
            click.echo(f"\n📋 数据样例 (前3条):")
            for i, rule in enumerate(result['rules'][:3]):
                click.echo(f"  规则 {i+1}:")
                click.echo(f"    专利号: {rule.get('patent_number', 'N/A')}")
                click.echo(f"    规则类型: {rule.get('rule', 'N/A')}")
                click.echo(f"    野生型: {rule.get('wild_type', 'N/A')[:50]}...")
                click.echo("")
        
    except Exception as e:
        click.echo(f"❌ 转换失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('json_file', type=click.Path(exists=True, path_type=Path))
def analyze_rules(json_file: Path):
    """分析JSON格式的专利规则文件
    
    JSON_FILE: 输入的JSON规则文件路径
    """
    try:
        import json
        
        click.echo(f"正在分析规则文件: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        rules = data.get('rules', [])
        
        click.echo(f"\n📄 文件元数据:")
        click.echo(f"  源文件: {metadata.get('source_file', 'N/A')}")
        click.echo(f"  总行数: {metadata.get('total_rows', 'N/A')}")
        click.echo(f"  转换时间: {metadata.get('conversion_timestamp', 'N/A')}")
        
        # 分析规则模式
        if rules:
            # 专利号分布
            patent_counts = {}
            rule_type_counts = {}
            mutation_patterns = set()
            
            for rule in rules:
                # 专利号统计
                patent = rule.get('patent_number', '')
                if patent:
                    patent_counts[patent] = patent_counts.get(patent, 0) + 1
                
                # 规则类型统计
                rule_type = rule.get('rule', '')
                if rule_type:
                    rule_type_counts[rule_type] = rule_type_counts.get(rule_type, 0) + 1
                
                # 突变模式收集
                mutant = rule.get('mutant', '')
                if mutant and mutant != '-':
                    mutation_patterns.add(mutant)
            
            click.echo(f"\n📊 规则分析:")
            click.echo(f"  总规则数: {len(rules)}")
            click.echo(f"  涉及专利数: {len(patent_counts)}")
            click.echo(f"  独特突变模式数: {len(mutation_patterns)}")
            
            click.echo(f"\n🏷️ 规则类型分布:")
            for rule_type, count in sorted(rule_type_counts.items()):
                percentage = (count / len(rules)) * 100
                click.echo(f"  {rule_type}: {count} ({percentage:.1f}%)")
            
            click.echo(f"\n📋 专利覆盖情况 (前10个):")
            sorted_patents = sorted(patent_counts.items(), key=lambda x: x[1], reverse=True)
            for patent, count in sorted_patents[:10]:
                click.echo(f"  {patent}: {count} 条规则")
            
            # 显示一些复杂的突变模式
            complex_mutations = [m for m in mutation_patterns if '/' in m][:5]
            if complex_mutations:
                click.echo(f"\n🧬 复杂突变模式示例:")
                for mutation in complex_mutations:
                    click.echo(f"  {mutation}")
        
    except Exception as e:
        click.echo(f"❌ 分析失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('claims_file', type=click.Path(exists=True, path_type=Path))
@click.argument('sequence_file', type=click.Path(exists=True, path_type=Path))
@click.argument('rules_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output-dir', '-o', type=click.Path(path_type=Path), 
              default=Path('output/rules'), help='输出目录')
@click.option('--api-key', type=str, help='Qwen API密钥（可从环境变量QWEN_API_KEY读取）')
@click.option('--model', default='qwen-plus', help='使用的Qwen模型')
@click.option('--export-markdown', is_flag=True, help='同时导出Markdown格式')
def generate_rules(claims_file: Path, sequence_file: Path, rules_file: Path,
                  output_dir: Path, api_key: str, model: str, export_markdown: bool):
    """使用LLM生成专利保护规则
    
    CLAIMS_FILE: 权利要求书Markdown文件
    SEQUENCE_FILE: 标准化序列JSON文件  
    RULES_FILE: 现有规则JSON文件
    """
    import os
    import json
    
    try:
        from .core.rule_generator import IntelligentRuleGenerator
        
        # 从环境变量读取API密钥（如果未通过参数提供）
        if not api_key:
            api_key = os.getenv('QWEN_API_KEY') or os.getenv('OPENAI_API_KEY')
        
        click.echo(f"🧬 开始生成专利保护规则")
        click.echo(f"权利要求书: {claims_file}")
        click.echo(f"序列文件: {sequence_file}")
        click.echo(f"现有规则: {rules_file}")
        click.echo("")
        
        # 创建规则生成器
        if api_key:
            generator = IntelligentRuleGenerator.create_with_qwen(api_key=api_key, model=model)
            # 测试连接
            click.echo("🔗 测试LLM连接...")
            if not generator.llm_agent.test_connection():
                click.echo("❌ LLM连接失败，请检查API密钥和网络连接", err=True)
                sys.exit(1)
            click.echo("✅ LLM连接成功")
        else:
            click.echo("⚠️  未提供API密钥，使用演示模式")
            generator = IntelligentRuleGenerator.create_with_qwen(model=model)
        
        # 生成规则
        click.echo("🔍 分析专利数据...")
        result = generator.generate_rules_from_patent(
            str(claims_file),
            str(sequence_file), 
            str(rules_file)
        )
        
        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成输出文件名
        patent_number = result.patent_number.replace(' ', '_').replace('/', '_')
        json_output = output_dir / f"{patent_number}_rules.json"
        
        # 导出简化JSON格式
        click.echo("📄 导出简化JSON格式规则...")
        raw_llm_response = getattr(result, 'raw_llm_response', None)
        generator.export_simplified_json(result, str(json_output), raw_llm_response)
        
        # 读取简化JSON用于Markdown生成
        simplified_data = None
        try:
            with open(json_output, 'r', encoding='utf-8') as f:
                simplified_data = json.load(f)
        except Exception as e:
            click.echo(f"⚠️ 简化JSON读取失败: {e}")
        
        # 导出Markdown（可选）
        if export_markdown:
            md_output = output_dir / f"{patent_number}_rules.md"
            click.echo("📝 导出简化Markdown格式文档...")
            generator.export_to_markdown(result, str(md_output), simplified_data)
        
        # 显示结果摘要
        click.echo("")
        click.echo("✅ 规则生成完成！")
        click.echo(f"📊 分析结果:")
        click.echo(f"  专利号: {result.patent_number}")
        click.echo(f"  保护规则数: {len(result.protection_rules)}")
        click.echo(f"  复杂度级别: {result.complexity_analysis.complexity_level}")
        click.echo(f"  分析置信度: {result.analysis_confidence:.2%}")
        click.echo(f"  回避策略数: {len(result.avoidance_strategies)}")
        click.echo("")
        click.echo(f"📁 输出文件:")
        click.echo(f"  JSON规则: {json_output}")
        if export_markdown:
            click.echo(f"  Markdown文档: {md_output}")
        
    except Exception as e:
        click.echo(f"❌ 规则生成失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--api-key', type=str, help='Qwen API密钥')
@click.option('--model', default='qwen-plus', help='测试的模型')
def test_llm(api_key: str, model: str):
    """测试LLM连接"""
    import os
    
    try:
        from .core.llm_agent import LLMRuleAgent
        
        # 从环境变量读取API密钥（如果未通过参数提供）
        if not api_key:
            api_key = os.getenv('QWEN_API_KEY') or os.getenv('OPENAI_API_KEY')
        
        click.echo(f"🔗 测试LLM连接 (模型: {model})")
        
        if not api_key:
            click.echo("⚠️  未提供API密钥，演示模式下无需连接测试")
            click.echo("💡 设置环境变量 QWEN_API_KEY 或使用 --api-key 参数")
            return
        
        agent = LLMRuleAgent(api_key=api_key, model=model)
        
        if agent.test_connection():
            click.echo("✅ LLM连接成功")
        else:
            click.echo("❌ LLM连接失败", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ 连接测试失败: {e}", err=True)
        sys.exit(1)


@cli.command()
def info():
    """显示工具信息和使用说明"""
    click.echo("🧬 TDT专利序列规则提炼工具")
    click.echo("=" * 50)
    click.echo("这是一个专门用于分析TDT酶专利序列规则的工具集。")
    click.echo("")
    click.echo("主要功能:")
    click.echo("• 将Excel格式的专利规则转换为JSON")
    click.echo("• 分析专利规则的模式和统计信息")
    click.echo("• 使用LLM从权利要求书中提取序列保护规则")
    click.echo("• 生成技术回避策略和复杂度分析")
    click.echo("")
    click.echo("使用流程:")
    click.echo("1. 使用 'convert-excel' 转换Excel规则文件")
    click.echo("2. 使用 'test-llm' 测试LLM连接")
    click.echo("3. 使用 'generate-rules' 生成智能规则分析")
    click.echo("4. 使用 'analyze-rules' 分析现有规则模式")
    click.echo("")
    click.echo("环境配置:")
    click.echo("• 设置环境变量 QWEN_API_KEY 或通过 --api-key 参数提供")
    click.echo("• 确保网络连接正常以访问Qwen API")
    click.echo("")
    click.echo("获取帮助: tdt-rules --help")


if __name__ == '__main__':
    cli()
