"""
核心功能模块

包含PDF解析和权利要求书提取的核心逻辑。
"""
from .parser import PDFParser
from .extractor import ClaimsExtractor

__all__ = ["PDFParser", "ClaimsExtractor"]
