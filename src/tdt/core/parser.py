"""
PDF解析模块

负责从PDF文件中提取文本内容，专注于文本和数学公式，忽略图片。
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber
from pdfplumber.page import Page

logger = logging.getLogger(__name__)


class PDFParser:
    """
    PDF文件解析器
    
    专门用于解析专利PDF文件，提取文本内容并识别页眉信息。
    """
    
    def __init__(self):
        """初始化PDF解析器"""
        self.pages_data: List[Dict] = []
    
    def parse_pdf(self, pdf_path: str) -> List[Dict]:
        """
        解析PDF文件，提取所有页面的文本内容和结构信息。
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            包含每页信息的字典列表，每个字典包含：
            - page_number: 页码
            - header_text: 页眉文本
            - content: 页面主要内容
            - bbox_info: 文本框位置信息
            
        Raises:
            FileNotFoundError: PDF文件不存在
            ValueError: PDF文件无法解析
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        logger.info(f"开始解析PDF文件: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                self.pages_data = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_data = self._extract_page_content(page, page_num)
                    self.pages_data.append(page_data)
                    
                logger.info(f"成功解析PDF文件，共 {len(self.pages_data)} 页")
                return self.pages_data
                
        except Exception as e:
            logger.error(f"解析PDF文件失败: {e}")
            raise ValueError(f"无法解析PDF文件: {e}")
    
    def _extract_page_content(self, page: Page, page_number: int) -> Dict:
        """
        从单个页面提取内容和结构信息。
        
        Args:
            page: pdfplumber页面对象
            page_number: 页码
            
        Returns:
            包含页面信息的字典
        """
        # 获取页面尺寸
        page_height = page.height
        
        # 提取所有文本及其位置信息
        chars = page.chars
        
        # 识别页眉（通常在页面顶部）
        header_text = self._extract_header(chars, page_height)
        
        # 提取主要内容
        content_text = page.extract_text()
        
        # 获取文本框信息
        bbox_info = self._get_text_bboxes(chars)
        
        return {
            "page_number": page_number,
            "header_text": header_text,
            "content": content_text or "",
            "bbox_info": bbox_info,
            "page_height": page_height,
            "page_width": page.width,
        }
    
    def _extract_header(self, chars: List[Dict], page_height: float) -> str:
        """
        从字符列表中提取页眉文本。
        
        Args:
            chars: 页面字符列表
            page_height: 页面高度
            
        Returns:
            页眉文本
        """
        if not chars:
            return ""
        
        # 定义页眉区域（页面顶部10%的区域）
        header_threshold = page_height * 0.9  # y坐标从底部开始计算
        
        header_chars = [
            char for char in chars 
            if char.get('y0', 0) >= header_threshold
        ]
        
        if not header_chars:
            return ""
        
        # 按位置排序并组合文本
        header_chars.sort(key=lambda x: (x.get('y1', 0), x.get('x0', 0)), reverse=True)
        header_text = ''.join(char.get('text', '') for char in header_chars)
        
        return header_text.strip()
    
    def _get_text_bboxes(self, chars: List[Dict]) -> List[Dict]:
        """
        获取文本框的边界信息。
        
        Args:
            chars: 页面字符列表
            
        Returns:
            文本框信息列表
        """
        bbox_info = []
        
        for char in chars:
            bbox_info.append({
                'text': char.get('text', ''),
                'x0': char.get('x0', 0),
                'y0': char.get('y0', 0),
                'x1': char.get('x1', 0),
                'y1': char.get('y1', 0),
                'fontname': char.get('fontname', ''),
                'size': char.get('size', 0),
            })
        
        return bbox_info
    
    def find_section_boundaries(
        self, 
        section_keywords: List[str] = None
    ) -> List[Tuple[int, int]]:
        """
        查找特定章节的边界。
        
        Args:
            section_keywords: 章节关键词列表，默认为权利要求书相关关键词
            
        Returns:
            章节边界列表，每个元素为 (开始页码, 结束页码) 的元组
        """
        if section_keywords is None:
            section_keywords = [
                "权利要求书", "权利要求", "Claims", "CLAIMS",
                "权　利　要　求　书", "权　利　要　求"
            ]
        
        section_boundaries = []
        start_page = None
        
        for page_data in self.pages_data:
            page_num = page_data["page_number"]
            header_text = page_data["header_text"]
            content = page_data["content"]
            
            # 检查页眉或内容中是否包含关键词
            text_to_check = f"{header_text} {content[:200]}"  # 只检查内容开头
            
            has_keyword = any(
                keyword in text_to_check 
                for keyword in section_keywords
            )
            
            if has_keyword and start_page is None:
                start_page = page_num
                logger.debug(f"发现章节开始页: {page_num}")
            elif not has_keyword and start_page is not None:
                # 章节结束
                section_boundaries.append((start_page, page_num - 1))
                logger.debug(f"章节结束页: {page_num - 1}")
                start_page = None
        
        # 如果章节一直持续到最后一页
        if start_page is not None:
            section_boundaries.append((start_page, self.pages_data[-1]["page_number"]))
        
        logger.info(f"找到 {len(section_boundaries)} 个目标章节")
        return section_boundaries
