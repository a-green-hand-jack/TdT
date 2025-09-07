"""
TDT酶专利序列提取工具

本包提供从专利PDF文件中提取权利要求书内容的功能。
"""
from typing import List, Optional

from .core.parser import PDFParser
from .core.extractor import ClaimsExtractor

__version__ = "0.1.0"
__author__ = "Jieke"

__all__ = [
    "PDFParser",
    "ClaimsExtractor",
]


def extract_claims_from_pdf(
    pdf_path: str,
    output_dir: str,
    output_format: str = "markdown"
) -> Optional[str]:
    """
    从PDF文件中提取权利要求书内容的便捷函数。

    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录路径
        output_format: 输出格式，支持 'markdown' 或 'text'

    Returns:
        成功时返回输出文件路径，失败时返回 None

    Raises:
        FileNotFoundError: 当PDF文件不存在时
        ValueError: 当输出格式不支持时
    """
    parser = PDFParser()
    extractor = ClaimsExtractor()
    
    # 解析PDF文件
    pages = parser.parse_pdf(pdf_path)
    
    # 提取权利要求书内容
    claims_content = extractor.extract_claims(pages)
    
    if claims_content:
        # 保存结果
        output_path = extractor.save_claims(
            claims_content, 
            pdf_path, 
            output_dir, 
            output_format
        )
        return output_path
    
    return None