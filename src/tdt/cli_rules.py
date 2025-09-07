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
def info():
    """显示工具信息和使用说明"""
    click.echo("🧬 TDT专利序列规则提炼工具")
    click.echo("=" * 50)
    click.echo("这是一个专门用于分析TDT酶专利序列规则的工具集。")
    click.echo("")
    click.echo("主要功能:")
    click.echo("• 将Excel格式的专利规则转换为JSON")
    click.echo("• 分析专利规则的模式和统计信息")
    click.echo("• 提取权利要求书中的序列信息")
    click.echo("• 生成标准化的序列保护规则")
    click.echo("")
    click.echo("使用流程:")
    click.echo("1. 使用 'convert-excel' 转换Excel规则文件")
    click.echo("2. 使用 'analyze-rules' 分析转换后的JSON文件")
    click.echo("3. 基于分析结果制定序列保护策略")
    click.echo("")
    click.echo("获取帮助: tdt-rules --help")


if __name__ == '__main__':
    cli()
