"""
权利要求书内容提取模块

负责从解析后的PDF页面中提取并格式化权利要求书内容。
"""
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.file_utils import ensure_output_dir, get_output_filename
from ..utils.text_utils import clean_text, normalize_text

logger = logging.getLogger(__name__)


class ClaimsExtractor:
    """
    权利要求书内容提取器
    
    从PDF页面数据中提取权利要求书部分，并格式化输出。
    """
    
    def __init__(self):
        """初始化提取器"""
        self.claims_keywords = [
            "权利要求书", "权利要求", "Claims", "CLAIMS",
            "权　利　要　求　书", "权　利　要　求", 
            "书　求　要　利　权", "求　要　利　权"  # 处理页眉中可能的倒序文本
        ]
    
    def extract_claims(self, pages_data: List[Dict]) -> Optional[str]:
        """
        从页面数据中提取权利要求书内容。
        
        Args:
            pages_data: PDF页面数据列表
            
        Returns:
            权利要求书内容文本，如果未找到则返回 None
        """
        if not pages_data:
            logger.warning("页面数据为空")
            return None
        
        # 找到权利要求书章节
        claims_pages = self._find_claims_pages(pages_data)
        
        if not claims_pages:
            logger.warning("未找到权利要求书章节")
            return None
        
        # 提取并合并内容
        claims_content = self._merge_claims_content(claims_pages)
        
        # 清理和格式化文本
        formatted_content = self._format_claims_content(claims_content)
        
        logger.info(f"成功提取权利要求书内容，共 {len(claims_pages)} 页")
        return formatted_content
    
    def _find_claims_pages(self, pages_data: List[Dict]) -> List[Dict]:
        """
        查找包含权利要求书的页面。
        
        Args:
            pages_data: PDF页面数据列表
            
        Returns:
            权利要求书页面数据列表
        """
        claims_pages = []
        in_claims_section = False
        
        for page_data in pages_data:
            header_text = page_data.get("header_text", "")
            content = page_data.get("content", "")
            
            # 检查是否进入权利要求书章节
            text_to_check = f"{header_text} {content[:300]}"
            
            # 检查页眉中是否包含权利要求书关键词
            header_has_claims = any(
                keyword in header_text 
                for keyword in self.claims_keywords
            )
            
            # 检查内容开头是否包含权利要求书关键词
            content_has_claims = any(
                keyword in content[:300] 
                for keyword in self.claims_keywords
            )
            
            has_claims_keyword = header_has_claims or content_has_claims
            
            if has_claims_keyword:
                in_claims_section = True
                claims_pages.append(page_data)
                logger.debug(f"找到权利要求书页面: {page_data['page_number']}")
            elif in_claims_section:
                # 检查是否仍在权利要求书章节内
                if self._is_still_in_claims(page_data):
                    claims_pages.append(page_data)
                    logger.debug(f"继续权利要求书页面: {page_data['page_number']}")
                else:
                    # 章节结束
                    logger.debug(f"权利要求书章节结束于页面: {page_data['page_number'] - 1}")
                    break
        
        return claims_pages
    
    def _is_still_in_claims(self, page_data: Dict) -> bool:
        """
        判断当前页面是否仍在权利要求书章节内。
        
        Args:
            page_data: 页面数据
            
        Returns:
            是否仍在权利要求书章节
        """
        header_text = page_data.get("header_text", "")
        content = page_data.get("content", "")
        
        # 如果页眉仍包含权利要求书关键词，认为仍在章节内
        if any(keyword in header_text for keyword in self.claims_keywords):
            return True
        
        # 如果页眉包含其他章节关键词，认为已离开权利要求书章节
        other_section_keywords = [
            "说明书", "摘要", "附图", "说明书摘要", "背景技术",
            "发明内容", "具体实施方式", "实施例", "Description",
            "Abstract", "Background", "Summary", "Detailed Description"
        ]
        
        if any(keyword in header_text for keyword in other_section_keywords):
            return False
        
        # 检查内容开头是否包含权利要求相关内容
        content_start = content[:500]
        if any(keyword in content_start for keyword in self.claims_keywords):
            return True
        
        # 检查是否包含权利要求条目格式（如"1. "、"2. "等）
        lines = content_start.split('\n')[:10]  # 检查前10行
        for line in lines:
            line = line.strip()
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                return True
        
        return False
    
    def _merge_claims_content(self, claims_pages: List[Dict]) -> str:
        """
        合并权利要求书页面内容。
        
        Args:
            claims_pages: 权利要求书页面数据列表
            
        Returns:
            合并后的内容文本
        """
        merged_content = []
        
        for page_data in claims_pages:
            page_num = page_data.get("page_number", 0)
            content = page_data.get("content", "")
            
            # 添加页面分隔符
            merged_content.append(f"\n<!-- 第 {page_num} 页 -->\n")
            merged_content.append(content)
        
        return '\n'.join(merged_content)
    
    def _format_claims_content(self, raw_content: str) -> str:
        """
        格式化权利要求书内容，便于人类阅读和内容对比。
        
        Args:
            raw_content: 原始内容文本
            
        Returns:
            格式化后的内容
        """
        # 清理文本
        cleaned_content = clean_text(raw_content)
        
        # 标准化文本
        normalized_content = normalize_text(cleaned_content)
        
        # 添加结构化标记和格式化
        formatted_content = self._format_for_readability(normalized_content)
        
        return formatted_content
    
    def _format_for_readability(self, content: str) -> str:
        """
        格式化内容以便人类阅读和内容对比。
        
        Args:
            content: 内容文本
            
        Returns:
            格式化后的易读内容
        """
        # 首先处理页面标记
        content = re.sub(r'<!-- 第 (\d+) 页 -->', r'\n\n---\n### 第 \1 页\n\n', content)
        
        # 预处理：在权利要求编号前插入换行符，以便正确分离
        # 这里要处理可能出现在行中间的权利要求编号
        content = re.sub(r'(\s+)(\d+)\.\s+', r'\1\n\n\2. ', content)
        
        # 现在按行处理
        lines = content.split('\n')
        formatted_lines = []
        current_claim_content = []
        current_claim_num = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是权利要求编号开始（现在应该在独立行了）
            claim_match = re.match(r'^(\d+)\.\s*(.*)$', line)
            if claim_match:
                # 如果有之前的权利要求，先处理完
                if current_claim_num and current_claim_content:
                    formatted_lines.append(f"\n## 权利要求 {current_claim_num}\n")
                    formatted_lines.append(self._format_claim_content('\n'.join(current_claim_content)))
                
                # 开始新的权利要求
                current_claim_num = claim_match.group(1)
                remaining_content = claim_match.group(2).strip()
                current_claim_content = [remaining_content] if remaining_content else []
            elif current_claim_num:
                # 继续当前权利要求的内容
                current_claim_content.append(line)
            else:
                # 不属于任何权利要求的内容（如页眉）
                formatted_lines.append(line)
        
        # 处理最后一个权利要求
        if current_claim_num and current_claim_content:
            formatted_lines.append(f"\n## 权利要求 {current_claim_num}\n")
            formatted_lines.append(self._format_claim_content('\n'.join(current_claim_content)))
        
        # 合并结果并清理
        result = '\n'.join(formatted_lines)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()
    
    def _format_claim_content(self, claim_text: str) -> str:
        """
        格式化单个权利要求的内容。
        
        Args:
            claim_text: 权利要求文本
            
        Returns:
            格式化后的权利要求内容
        """
        if not claim_text:
            return ""
        
        lines = claim_text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是从属权利要求的引用
            if '根据权利要求' in line:
                formatted_lines.append(f"**依据：** {line}")
            # 检查是否包含特征描述
            elif '其特征在于' in line:
                formatted_lines.append(f"**特征：** {line}")
            # 检查是否是选择性描述
            elif line.startswith(('优选地', '更优选地', '特别地', '进一步地')):
                formatted_lines.append(f"*{line}*")
            # 检查是否是技术参数或序列信息
            elif any(param in line for param in ['X1', 'X2', 'X3', 'X4', 'X5', 'SEQ ID', '表示选自']):
                formatted_lines.append(f"- {line}")
            # 检查是否是氨基酸位点信息
            elif re.search(r'[A-Z]\d+[A-Z]?', line) and any(char in line for char in ['、', ',']):
                formatted_lines.append(f"**位点：** {line}")
            else:
                formatted_lines.append(line)
        
        return '\n\n'.join(formatted_lines)
    
    def save_claims(
        self,
        claims_content: str,
        original_pdf_path: str,
        output_dir: str,
        output_format: str = "markdown"
    ) -> str:
        """
        保存权利要求书内容到文件。
        
        Args:
            claims_content: 权利要求书内容
            original_pdf_path: 原PDF文件路径
            output_dir: 输出目录
            output_format: 输出格式 ('markdown' 或 'text')
            
        Returns:
            输出文件路径
            
        Raises:
            ValueError: 不支持的输出格式
        """
        if output_format not in ["markdown", "text"]:
            raise ValueError(f"不支持的输出格式: {output_format}")
        
        # 确保输出目录存在
        ensure_output_dir(output_dir)
        
        # 获取输出文件名
        output_filename = get_output_filename(original_pdf_path, output_format)
        output_path = Path(output_dir) / output_filename
        
        # 准备最终内容
        if output_format == "markdown":
            final_content = self._prepare_markdown_content(claims_content, original_pdf_path)
        else:
            final_content = self._prepare_text_content(claims_content, original_pdf_path)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        logger.info(f"权利要求书内容已保存到: {output_path}")
        return str(output_path)
    
    def _prepare_markdown_content(self, content: str, pdf_path: str) -> str:
        """
        准备Markdown格式的内容。
        
        Args:
            content: 权利要求书内容
            pdf_path: 原PDF文件路径
            
        Returns:
            Markdown格式的内容
        """
        pdf_name = Path(pdf_path).name
        
        markdown_content = f"""# 权利要求书 - {pdf_name}

> 从专利文件 `{pdf_name}` 中提取的权利要求书内容

---

{content}

---

*此文档由 TDT 专利序列提取工具自动生成*
"""
        return markdown_content
    
    def _prepare_text_content(self, content: str, pdf_path: str) -> str:
        """
        准备纯文本格式的内容。
        
        Args:
            content: 权利要求书内容
            pdf_path: 原PDF文件路径
            
        Returns:
            纯文本格式的内容
        """
        pdf_name = Path(pdf_path).name
        
        text_content = f"""权利要求书 - {pdf_name}

从专利文件 {pdf_name} 中提取的权利要求书内容

{'='*50}

{content}

{'='*50}

此文档由 TDT 专利序列提取工具自动生成
"""
        return text_content
