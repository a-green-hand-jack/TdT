"""
文件处理工具模块

提供文件和目录操作的辅助功能。
"""
import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def ensure_output_dir(output_dir: Union[str, Path]) -> Path:
    """
    确保输出目录存在，如果不存在则创建。
    
    Args:
        output_dir: 输出目录路径
        
    Returns:
        Path对象表示的输出目录
        
    Raises:
        OSError: 创建目录失败
    """
    output_path = Path(output_dir)
    
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"确保输出目录存在: {output_path}")
        return output_path
    except OSError as e:
        logger.error(f"创建输出目录失败: {output_path}, 错误: {e}")
        raise


def get_output_filename(pdf_path: Union[str, Path], output_format: str) -> str:
    """
    根据原PDF文件路径和输出格式生成输出文件名。
    
    Args:
        pdf_path: 原PDF文件路径
        output_format: 输出格式 ('markdown' 或 'text')
        
    Returns:
        输出文件名
        
    Raises:
        ValueError: 不支持的输出格式
    """
    pdf_path = Path(pdf_path)
    base_name = pdf_path.stem  # 不包含扩展名的文件名
    
    if output_format == "markdown":
        extension = ".md"
    elif output_format == "text":
        extension = ".txt"
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")
    
    output_filename = f"{base_name}_claims{extension}"
    logger.debug(f"生成输出文件名: {output_filename}")
    
    return output_filename


def validate_pdf_file(pdf_path: Union[str, Path]) -> Path:
    """
    验证PDF文件是否存在且可读。
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        验证后的Path对象
        
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件不是PDF格式
        PermissionError: 文件无法读取
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    if not pdf_path.is_file():
        raise ValueError(f"路径不是文件: {pdf_path}")
    
    if pdf_path.suffix.lower() != '.pdf':
        raise ValueError(f"文件不是PDF格式: {pdf_path}")
    
    # 检查文件权限
    try:
        with open(pdf_path, 'rb') as f:
            pass  # 尝试打开文件检查权限
    except PermissionError:
        raise PermissionError(f"无法读取PDF文件: {pdf_path}")
    
    logger.debug(f"PDF文件验证通过: {pdf_path}")
    return pdf_path


def get_pdf_files_in_directory(directory: Union[str, Path]) -> list[Path]:
    """
    获取目录中的所有PDF文件。
    
    Args:
        directory: 目录路径
        
    Returns:
        PDF文件路径列表
        
    Raises:
        NotADirectoryError: 路径不是目录
    """
    directory = Path(directory)
    
    if not directory.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")
    
    if not directory.is_dir():
        raise NotADirectoryError(f"路径不是目录: {directory}")
    
    pdf_files = list(directory.glob("*.pdf"))
    pdf_files.extend(directory.glob("*.PDF"))  # 处理大写扩展名
    
    # 排序以确保一致的处理顺序
    pdf_files.sort()
    
    logger.info(f"在目录 {directory} 中找到 {len(pdf_files)} 个PDF文件")
    return pdf_files


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名，移除或替换特殊字符。
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    # 移除或替换不安全的字符
    unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    safe_name = filename
    
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    
    # 移除多余的空格和点
    safe_name = safe_name.strip('. ')
    
    # 确保文件名不为空
    if not safe_name:
        safe_name = "untitled"
    
    logger.debug(f"文件名安全化: {filename} -> {safe_name}")
    return safe_name
