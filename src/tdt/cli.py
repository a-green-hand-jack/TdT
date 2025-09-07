"""
命令行接口模块

提供TDT专利序列提取工具的命令行接口。
"""
import logging
import sys
from pathlib import Path
from typing import List, Optional

import click
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

from tdt import extract_claims_from_pdf
from tdt.core.parser import PDFParser
from tdt.core.extractor import ClaimsExtractor
from tdt.utils.file_utils import get_pdf_files_in_directory, validate_pdf_file


# 配置日志
def setup_logging(verbose: bool = False) -> None:
    """
    配置日志系统。
    
    Args:
        verbose: 是否启用详细日志
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='启用详细日志输出')
@click.version_option(version='0.1.0', message='TDT专利序列提取工具 v%(version)s')
def cli(verbose: bool) -> None:
    """
    TDT酶专利序列提取工具
    
    从专利PDF文件中提取权利要求书内容，生成便于LLM处理的结构化文本。
    """
    setup_logging(verbose)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    default='./output',
    help='输出目录路径，默认为 ./output'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['markdown', 'text']),
    default='markdown',
    help='输出格式，默认为 markdown'
)
@click.option(
    '--force', 
    is_flag=True,
    help='强制覆盖已存在的输出文件'
)
def extract(
    pdf_path: Path, 
    output_dir: Path, 
    format: str,
    force: bool
) -> None:
    """
    从单个PDF文件中提取权利要求书内容。
    
    PDF_PATH: 要处理的PDF文件路径
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 验证PDF文件
        pdf_path = validate_pdf_file(pdf_path)
        
        # 检查输出文件是否已存在
        from tdt.utils.file_utils import get_output_filename
        output_filename = get_output_filename(pdf_path, format)
        output_file = output_dir / output_filename
        
        if output_file.exists() and not force:
            click.echo(f"输出文件已存在: {output_file}")
            click.echo("使用 --force 选项强制覆盖")
            return
        
        # 显示处理信息
        click.echo(f"正在处理PDF文件: {pdf_path}")
        click.echo(f"输出目录: {output_dir}")
        click.echo(f"输出格式: {format}")
        
        # 执行提取
        with click.progressbar(length=100, label='提取进度') as bar:
            bar.update(20)  # 开始解析
            
            result_path = extract_claims_from_pdf(
                str(pdf_path),
                str(output_dir),
                format
            )
            
            bar.update(80)  # 完成提取
            
            if result_path:
                bar.finish()
                click.echo(f"\n✅ 成功提取权利要求书内容")
                click.echo(f"输出文件: {result_path}")
            else:
                bar.finish()
                click.echo(f"\n❌ 未在PDF文件中找到权利要求书内容")
                
    except Exception as e:
        logger.error(f"处理PDF文件失败: {e}")
        click.echo(f"❌ 错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    default='./output',
    help='输出目录路径，默认为 ./output'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['markdown', 'text']),
    default='markdown',
    help='输出格式，默认为 markdown'
)
@click.option(
    '--force', 
    is_flag=True,
    help='强制覆盖已存在的输出文件'
)
@click.option(
    '--max-files', '-n',
    type=int,
    help='最大处理文件数量，用于测试'
)
def batch(
    input_dir: Path,
    output_dir: Path,
    format: str,
    force: bool,
    max_files: Optional[int]
) -> None:
    """
    批量处理目录中的所有PDF文件。
    
    INPUT_DIR: 包含PDF文件的输入目录
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 获取所有PDF文件
        pdf_files = get_pdf_files_in_directory(input_dir)
        
        if not pdf_files:
            click.echo(f"在目录 {input_dir} 中没有找到PDF文件")
            return
        
        # 限制处理文件数量（用于测试）
        if max_files:
            pdf_files = pdf_files[:max_files]
        
        click.echo(f"找到 {len(pdf_files)} 个PDF文件")
        click.echo(f"输出目录: {output_dir}")
        click.echo(f"输出格式: {format}")
        
        # 统计信息
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 批量处理
        with click.progressbar(pdf_files, label='批量处理进度') as bar:
            for pdf_file in bar:
                try:
                    # 检查输出文件是否已存在
                    from tdt.utils.file_utils import get_output_filename
                    output_filename = get_output_filename(pdf_file, format)
                    output_file = output_dir / output_filename
                    
                    if output_file.exists() and not force:
                        skipped_count += 1
                        click.echo(f"\n⏭️  跳过已存在的文件: {pdf_file.name}")
                        continue
                    
                    # 处理文件
                    result_path = extract_claims_from_pdf(
                        str(pdf_file),
                        str(output_dir),
                        format
                    )
                    
                    if result_path:
                        success_count += 1
                        click.echo(f"\n✅ 成功处理: {pdf_file.name}")
                    else:
                        failed_count += 1
                        click.echo(f"\n⚠️  未找到权利要求书: {pdf_file.name}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"处理文件 {pdf_file} 失败: {e}")
                    click.echo(f"\n❌ 处理失败: {pdf_file.name} - {e}")
        
        # 显示最终统计
        click.echo(f"\n📊 处理完成:")
        click.echo(f"  成功: {success_count}")
        click.echo(f"  失败: {failed_count}")
        click.echo(f"  跳过: {skipped_count}")
        click.echo(f"  总计: {len(pdf_files)}")
        
    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        click.echo(f"❌ 错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
def info(pdf_path: Path) -> None:
    """
    显示PDF文件的结构信息，用于调试和分析。
    
    PDF_PATH: 要分析的PDF文件路径
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 验证PDF文件
        pdf_path = validate_pdf_file(pdf_path)
        
        click.echo(f"正在分析PDF文件: {pdf_path}")
        
        # 解析PDF
        parser = PDFParser()
        pages_data = parser.parse_pdf(str(pdf_path))
        
        click.echo(f"\n📄 PDF文件信息:")
        click.echo(f"  文件名: {pdf_path.name}")
        click.echo(f"  总页数: {len(pages_data)}")
        
        # 显示页面信息
        click.echo(f"\n📑 页面结构:")
        for i, page_data in enumerate(pages_data[:10]):  # 只显示前10页
            page_num = page_data['page_number']
            header = page_data['header_text'][:50] + '...' if len(page_data['header_text']) > 50 else page_data['header_text']
            content_preview = page_data['content'][:100] + '...' if len(page_data['content']) > 100 else page_data['content']
            
            click.echo(f"  第{page_num}页:")
            click.echo(f"    页眉: {header or '(无)'}")
            click.echo(f"    内容预览: {content_preview or '(无)'}")
        
        if len(pages_data) > 10:
            click.echo(f"  ... 还有 {len(pages_data) - 10} 页")
        
        # 尝试识别权利要求书章节
        extractor = ClaimsExtractor()
        claims_content = extractor.extract_claims(pages_data)
        
        if claims_content:
            click.echo(f"\n✅ 发现权利要求书内容")
            click.echo(f"  内容长度: {len(claims_content)} 字符")
            
            # 提取权利要求编号
            from tdt.utils.text_utils import extract_claim_numbers
            claim_numbers = extract_claim_numbers(claims_content)
            if claim_numbers:
                click.echo(f"  权利要求编号: {claim_numbers}")
        else:
            click.echo(f"\n❌ 未找到权利要求书内容")
            
    except Exception as e:
        logger.error(f"分析PDF文件失败: {e}")
        click.echo(f"❌ 错误: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """主函数入口点"""
    cli()


if __name__ == '__main__':
    main()
