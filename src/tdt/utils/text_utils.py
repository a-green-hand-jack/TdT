"""
文本处理工具模块

提供文本清理、标准化和格式化功能。
"""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    清理文本，移除多余的空白字符和特殊字符。
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return ""
    
    # 移除PDF提取常见的噪音字符
    cleaned = text.replace('\x00', '')  # 移除null字符
    cleaned = re.sub(r'\s+', ' ', cleaned)  # 多个空白字符合并为单个空格
    cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)  # 多个换行符合并为双换行
    
    # 移除行首行尾空白
    lines = []
    for line in cleaned.split('\n'):
        lines.append(line.strip())
    
    cleaned = '\n'.join(lines)
    
    logger.debug("文本清理完成")
    return cleaned.strip()


def normalize_text(text: str) -> str:
    """
    标准化文本，统一标点符号和格式。
    
    Args:
        text: 清理后的文本
        
    Returns:
        标准化后的文本
    """
    if not text:
        return ""
    
    normalized = text
    
    # 统一中文标点符号
    punct_map = {
        '（': '(',
        '）': ')',
        '，': ',',
        '。': '.',
        '；': ';',
        '：': ':',
        '？': '?',
        '！': '!',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
    }
    
    for chinese_punct, english_punct in punct_map.items():
        normalized = normalized.replace(chinese_punct, english_punct)
    
    # 统一数字格式
    normalized = re.sub(r'(\d+)\.(\d+)', r'\1.\2', normalized)  # 确保小数点格式
    
    # 统一权利要求条目格式
    normalized = re.sub(r'(\d+)\s*[.．]\s*', r'\1. ', normalized)
    
    logger.debug("文本标准化完成")
    return normalized


def extract_claim_numbers(text: str) -> List[int]:
    """
    从文本中提取权利要求编号。
    
    Args:
        text: 文本内容
        
    Returns:
        权利要求编号列表
    """
    claim_numbers = []
    
    # 匹配权利要求编号格式
    patterns = [
        r'(\d+)\.\s*',  # "1. ", "2. " 等
        r'权利要求\s*(\d+)',  # "权利要求1", "权利要求 2" 等
        r'claim\s*(\d+)',  # "claim 1", "claim2" 等 (忽略大小写)
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                claim_num = int(match.group(1))
                if claim_num not in claim_numbers:
                    claim_numbers.append(claim_num)
            except ValueError:
                continue
    
    claim_numbers.sort()
    logger.debug(f"提取到权利要求编号: {claim_numbers}")
    return claim_numbers


def split_into_claims(text: str) -> List[str]:
    """
    将权利要求书文本拆分为独立的权利要求条目。
    
    Args:
        text: 权利要求书文本
        
    Returns:
        权利要求条目列表
    """
    if not text:
        return []
    
    # 使用权利要求编号分割文本
    # 匹配 "数字." 开头的行
    claim_pattern = r'^(\d+)\.\s*(.+?)(?=^\d+\.|$)'
    matches = re.finditer(claim_pattern, text, re.MULTILINE | re.DOTALL)
    
    claims = []
    for match in matches:
        claim_num = match.group(1)
        claim_content = match.group(2).strip()
        
        if claim_content:
            formatted_claim = f"{claim_num}. {claim_content}"
            claims.append(formatted_claim)
    
    logger.debug(f"拆分出 {len(claims)} 个权利要求条目")
    return claims


def is_claims_related_text(text: str) -> bool:
    """
    判断文本是否与权利要求书相关。
    
    Args:
        text: 待检查的文本
        
    Returns:
        是否与权利要求书相关
    """
    if not text:
        return False
    
    # 权利要求书相关关键词
    keywords = [
        "权利要求", "claims", "claim",
        "独立权利要求", "从属权利要求",
        "所述", "其特征在于", "其中",
        "根据权利要求", "according to claim",
        "characterized in that", "wherein"
    ]
    
    text_lower = text.lower()
    
    # 检查关键词
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    
    # 检查权利要求编号格式
    if re.search(r'\d+\.\s+', text):
        return True
    
    return False


def format_for_llm(text: str) -> str:
    """
    格式化文本以便LLM更好地理解。
    
    Args:
        text: 原始文本
        
    Returns:
        格式化后的文本
    """
    if not text:
        return ""
    
    formatted = text
    
    # 为权利要求条目添加清晰的分隔
    formatted = re.sub(
        r'^(\d+)\.\s*',
        r'\n**权利要求 \1:**\n\n',
        formatted,
        flags=re.MULTILINE
    )
    
    # 为从属权利要求添加标记
    formatted = re.sub(
        r'根据权利要求(\d+)',
        r'*[依据权利要求 \1]*',
        formatted
    )
    
    # 突出特征性部分
    formatted = re.sub(
        r'其特征在于[：:]?',
        r'\n\n**其特征在于：**\n',
        formatted
    )
    
    # 添加结构化标记
    formatted = re.sub(
        r'所述(.{1,20}?)包括[：:]?',
        r'\n\n所述**\1**包括：\n',
        formatted
    )
    
    logger.debug("LLM格式化完成")
    return formatted.strip()
