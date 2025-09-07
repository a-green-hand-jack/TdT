"""
序列处理命令行工具

提供统一的序列文件处理命令行接口。
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .core.sequence_processor import UnifiedSequenceProcessor
from .models.format_models import SequenceFormat


def setup_logging(verbose: bool) -> None:
    """
    配置日志
    
    Args:
        verbose: 是否启用详细日志
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='启用详细日志输出')
@click.pass_context
def cli(ctx, verbose):
    """TDT序列处理工具 - 统一的序列文件处理器"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    setup_logging(verbose)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='输出文件路径（默认在同目录生成.json文件）')
@click.option('--format', '-f', 'output_format', default='json',
              type=click.Choice(['json']), help='输出格式')
@click.option('--no-auto-detect', is_flag=True, 
              help='禁用自动格式检测')
@click.option('--expected-format', type=click.Choice(['fasta', 'csv']),
              help='指定预期输入格式')
@click.option('--include-analysis/--no-analysis', default=True,
              help='是否包含序列分析信息')
@click.option('--include-stats/--no-stats', default=True,
              help='是否包含统计信息')
@click.pass_context
def process(ctx, input_file, output, output_format, no_auto_detect, 
           expected_format, include_analysis, include_stats):
    """
    处理单个序列文件
    
    INPUT_FILE: 输入序列文件路径
    """
    processor = UnifiedSequenceProcessor()
    
    # 确定输出文件路径
    if not output:
        output = input_file.with_suffix(f'.{output_format}')
    
    # 转换格式枚举
    expected_seq_format = None
    if expected_format:
        expected_seq_format = SequenceFormat(expected_format)
    
    try:
        click.echo(f"处理文件: {input_file}")
        
        result = processor.process_file(
            file_path=input_file,
            output_path=output,
            output_format=output_format,
            auto_detect_format=not no_auto_detect,
            expected_format=expected_seq_format
        )
        
        # 显示处理结果摘要
        click.echo(f"✅ 处理完成!")
        click.echo(f"   📁 输出文件: {output}")
        click.echo(f"   📊 序列数量: {result.metadata.total_sequences}")
        click.echo(f"   📏 文件大小: {result.metadata.file_size_bytes} 字节")
        duration = result.metadata.processing_duration_ms
        if duration is not None:
            click.echo(f"   ⏱️  处理耗时: {duration:.2f} ms")
        
        if result.validation.total_warnings > 0:
            click.echo(f"   ⚠️  警告: {result.validation.total_warnings} 个")
        
        if result.validation.total_errors > 0:
            click.echo(f"   ❌ 错误: {result.validation.total_errors} 个")
            click.echo("   详细错误信息:")
            for error in result.validation.errors:
                click.echo(f"      • {error}")
        
        if ctx.obj.get('verbose'):
            click.echo("\n📋 详细统计信息:")
            for key, value in result.statistics.items():
                click.echo(f"   {key}: {value}")
        
    except Exception as e:
        click.echo(f"❌ 处理失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.pass_context
def info(ctx, input_file):
    """
    显示序列文件信息（不进行完整处理）
    
    INPUT_FILE: 输入序列文件路径
    """
    processor = UnifiedSequenceProcessor()
    
    try:
        click.echo(f"分析文件: {input_file}")
        
        # 只进行格式检测
        detection_result = processor.format_detector.detect_format(input_file)
        
        click.echo(f"\n📄 文件信息:")
        click.echo(f"   路径: {input_file}")
        click.echo(f"   大小: {detection_result.file_size_bytes} 字节")
        click.echo(f"   扩展名: .{detection_result.file_extension}")
        
        click.echo(f"\n🔍 格式检测结果:")
        click.echo(f"   检测格式: {detection_result.detected_format}")
        click.echo(f"   检测方法: {detection_result.detection_method}")
        click.echo(f"   置信度: {detection_result.is_confident()}")
        
        click.echo(f"\n📊 各格式置信度评分:")
        for format_type, score in detection_result.confidence_scores.items():
            indicator = "✅" if format_type == detection_result.detected_format else "  "
            format_name = format_type.value if hasattr(format_type, 'value') else str(format_type)
            click.echo(f"   {indicator} {format_name}: {score:.3f}")
        
        if detection_result.format_specific_info:
            click.echo(f"\n🔧 格式特定信息:")
            for key, value in detection_result.format_specific_info.items():
                if isinstance(value, dict) and not value.get('error'):
                    click.echo(f"   {key}:")
                    for subkey, subvalue in value.items():
                        if subkey != 'error':
                            click.echo(f"      {subkey}: {subvalue}")
        
        # 如果置信度足够高，可以尝试快速解析获取序列数量
        if detection_result.is_confident():
            try:
                result = processor.process_file(
                    file_path=input_file,
                    auto_detect_format=True
                )
                click.echo(f"\n📝 序列信息:")
                click.echo(f"   序列数量: {result.metadata.total_sequences}")
                
                if result.statistics:
                    stats = result.statistics
                    if 'length_distribution' in stats:
                        length_dist = stats['length_distribution']
                        click.echo(f"   长度范围: {length_dist['min']} - {length_dist['max']}")
                        click.echo(f"   平均长度: {length_dist['mean']:.1f}")
                    
                    if 'sequence_types' in stats:
                        click.echo(f"   分子类型: {stats['sequence_types']}")
                
            except Exception as e:
                click.echo(f"\n⚠️  无法快速解析序列内容: {e}")
        
    except Exception as e:
        click.echo(f"❌ 分析失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument('output_dir', type=click.Path(path_type=Path))
@click.option('--pattern', default='*', help='文件匹配模式（默认: *）')
@click.option('--format', '-f', 'output_format', default='json',
              type=click.Choice(['json']), help='输出格式')
@click.option('--recursive', '-r', is_flag=True, help='递归处理子目录')
@click.option('--no-auto-detect', is_flag=True, help='禁用自动格式检测')
@click.option('--max-workers', type=int, help='最大并发数')
@click.pass_context
def batch(ctx, input_dir, output_dir, pattern, output_format, recursive, 
          no_auto_detect, max_workers):
    """
    批量处理目录中的序列文件
    
    INPUT_DIR: 输入目录路径
    OUTPUT_DIR: 输出目录路径
    """
    processor = UnifiedSequenceProcessor()
    
    try:
        click.echo(f"批量处理目录: {input_dir}")
        click.echo(f"输出目录: {output_dir}")
        click.echo(f"文件模式: {pattern}")
        click.echo(f"递归处理: {'是' if recursive else '否'}")
        
        with click.progressbar(length=100, label='处理进度') as bar:
            # 启动批量处理
            result = processor.process_directory(
                input_dir=input_dir,
                output_dir=output_dir,
                pattern=pattern,
                output_format=output_format,
                auto_detect_format=not no_auto_detect,
                recursive=recursive,
                max_workers=max_workers
            )
            bar.update(100)  # 由于我们无法实时更新进度，直接完成
        
        # 显示批量处理结果
        click.echo(f"\n✅ 批量处理完成!")
        click.echo(f"   📁 总文件数: {result.total_files}")
        click.echo(f"   ✅ 成功处理: {result.successful_files}")
        click.echo(f"   ❌ 处理失败: {result.failed_files}")
        click.echo(f"   ⏭️  跳过文件: {result.skipped_files}")
        click.echo(f"   📊 成功率: {result.calculate_success_rate():.1%}")
        click.echo(f"   ⏱️  总耗时: {result.total_duration_ms:.2f} ms")
        
        if result.global_statistics:
            stats = result.global_statistics
            if 'total_sequences_processed' in stats:
                click.echo(f"   📝 处理序列总数: {stats['total_sequences_processed']}")
            
            if 'file_format_distribution' in stats:
                click.echo(f"   📋 文件格式分布:")
                for format_type, count in stats['file_format_distribution'].items():
                    click.echo(f"      {format_type}: {count} 个文件")
        
        # 显示失败的文件
        if result.failed_files > 0:
            click.echo(f"\n❌ 失败的文件:")
            failed_files = [
                file_path for file_path, file_result in result.file_results.items()
                if file_result.status.value == 'failed'
            ]
            for file_path in failed_files[:10]:  # 最多显示10个
                click.echo(f"   • {file_path}")
            
            if len(failed_files) > 10:
                click.echo(f"   ... 还有 {len(failed_files) - 10} 个文件")
        
        if ctx.obj.get('verbose') and result.global_log:
            click.echo(f"\n📋 处理日志:")
            for log_entry in result.global_log[-10:]:  # 显示最后10条日志
                level_icon = {
                    'INFO': 'ℹ️',
                    'WARNING': '⚠️',
                    'ERROR': '❌',
                    'DEBUG': '🔧'
                }.get(log_entry.level.value, '📝')
                click.echo(f"   {level_icon} {log_entry.message}")
        
    except Exception as e:
        click.echo(f"❌ 批量处理失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='输出JSON文件路径')
@click.option('--pretty', is_flag=True, help='美化JSON输出')
@click.pass_context
def convert(ctx, input_file, output, pretty):
    """
    转换序列文件为标准JSON格式（仅转换，不保存）
    
    INPUT_FILE: 输入序列文件路径
    """
    processor = UnifiedSequenceProcessor()
    
    try:
        click.echo(f"转换文件: {input_file}")
        
        result = processor.process_file(
            file_path=input_file,
            auto_detect_format=True
        )
        
        # 创建SequenceRecord对象列表（从字典重建）
        from .models.sequence_record import SequenceRecord
        sequences = [SequenceRecord(**seq_dict) for seq_dict in result.sequences]
        
        # 转换为JSON
        json_data = processor.convert_to_json(
            sequences=sequences,
            metadata=result.metadata,
            include_analysis=True,
            include_statistics=True
        )
        
        # 输出JSON
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, 
                         indent=2 if pretty else None)
            click.echo(f"✅ JSON已保存到: {output}")
        else:
            # 输出到标准输出
            json_str = json.dumps(json_data, ensure_ascii=False, 
                                indent=2 if pretty else None)
            click.echo(json_str)
        
    except Exception as e:
        click.echo(f"❌ 转换失败: {e}", err=True)
        sys.exit(1)


@cli.command()
def formats():
    """显示支持的序列格式信息"""
    processor = UnifiedSequenceProcessor()
    supported_formats = processor.get_supported_formats()
    
    click.echo("🧬 支持的序列格式:")
    click.echo()
    
    for format_type in supported_formats:
        parser = processor._get_parser(format_type)
        extensions = parser.get_supported_extensions() if parser else []
        
        format_name = format_type.value if hasattr(format_type, 'value') else str(format_type)
        click.echo(f"📋 {format_name.upper()}")
        click.echo(f"   文件扩展名: {', '.join(extensions)}")
        
        # 获取格式规范信息
        from .models.format_models import FORMAT_SPECIFICATIONS
        spec = FORMAT_SPECIFICATIONS.get(format_type)
        if spec:
            click.echo(f"   描述: {spec.description}")
            if spec.characteristics:
                click.echo(f"   特征:")
                for key, value in spec.characteristics.items():
                    if isinstance(value, bool):
                        value = "是" if value else "否"
                    click.echo(f"      {key}: {value}")
        click.echo()


if __name__ == '__main__':
    cli()
