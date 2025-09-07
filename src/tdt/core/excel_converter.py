"""
Excel到JSON转换器模块

该模块负责将专利规则Excel文件转换为结构化的JSON数据，
为后续的序列规则分析提供标准化的数据基础。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from openpyxl import load_workbook

logger = logging.getLogger(__name__)


class ExcelStructureError(Exception):
    """Excel文件结构错误异常"""
    pass


class ExcelToJsonConverter:
    """Excel专利规则文件转JSON转换器
    
    将包含专利序列规则的Excel文件转换为标准化的JSON格式，
    便于后续的数据分析和规则提取处理。
    """
    
    # 预期的Excel列名映射
    EXPECTED_COLUMNS = {
        'Group': 'group',
        'Patent Number': 'patent_number', 
        'Wild-Type': 'wild_type',
        'Mutant': 'mutant',
        'Mutation': 'mutation',
        'Statement': 'statement',
        'Rule': 'rule',
        'Comment': 'comment'
    }
    
    def __init__(self):
        """初始化转换器"""
        self.data: Optional[Dict[str, Any]] = None
        
    def convert(self, excel_path: Union[str, Path]) -> Dict[str, Any]:
        """转换Excel文件为结构化JSON数据
        
        Args:
            excel_path: Excel文件路径
            
        Returns:
            包含转换结果的字典，结构如下：
            {
                "metadata": {
                    "source_file": "文件路径",
                    "total_rows": 行数,
                    "columns": ["列名列表"],
                    "conversion_timestamp": "转换时间"
                },
                "rules": [
                    {
                        "group": 分组,
                        "patent_number": "专利号",
                        "wild_type": "野生型序列",
                        "mutant": "突变体信息",
                        "mutation": "突变描述", 
                        "statement": "声明",
                        "rule": "规则类型",
                        "comment": "备注"
                    }
                ]
            }
            
        Raises:
            FileNotFoundError: 文件不存在
            ExcelStructureError: Excel文件结构不符合预期
        """
        excel_path = Path(excel_path)
        
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel文件不存在: {excel_path}")
        
        logger.info(f"开始转换Excel文件: {excel_path}")
        
        try:
            # 读取Excel文件
            df = pd.read_excel(excel_path)
            
            # 验证文件结构
            self._validate_structure(df)
            
            # 标准化列名
            df_normalized = self._normalize_columns(df)
            
            # 清理和处理数据
            df_cleaned = self._clean_data(df_normalized)
            
            # 构建JSON结构
            json_data = self._build_json_structure(df_cleaned, excel_path)
            
            self.data = json_data
            logger.info(f"Excel转换完成，共处理 {len(json_data['rules'])} 条规则")
            
            return json_data
            
        except Exception as e:
            logger.error(f"Excel转换过程中发生错误: {e}")
            raise
    
    def _validate_structure(self, df: pd.DataFrame) -> None:
        """验证Excel文件结构
        
        Args:
            df: pandas DataFrame
            
        Raises:
            ExcelStructureError: 结构验证失败
        """
        if df.empty:
            raise ExcelStructureError("Excel文件为空")
        
        # 检查必需的列
        required_columns = set(self.EXPECTED_COLUMNS.keys())
        actual_columns = set(df.columns)
        
        missing_columns = required_columns - actual_columns
        if missing_columns:
            raise ExcelStructureError(
                f"缺少必需的列: {', '.join(missing_columns)}\n"
                f"实际列: {', '.join(actual_columns)}"
            )
        
        logger.debug(f"Excel结构验证通过，列数: {len(df.columns)}, 行数: {len(df)}")
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名
        
        Args:
            df: 原始DataFrame
            
        Returns:
            列名标准化后的DataFrame
        """
        # 创建列名映射
        column_mapping = {}
        for actual_col in df.columns:
            for expected_col, standard_name in self.EXPECTED_COLUMNS.items():
                if actual_col.strip() == expected_col:
                    column_mapping[actual_col] = standard_name
                    break
        
        # 重命名列
        df_renamed = df.rename(columns=column_mapping)
        
        # 只保留标准列
        standard_columns = list(self.EXPECTED_COLUMNS.values())
        df_filtered = df_renamed[standard_columns]
        
        logger.debug(f"列名标准化完成: {list(df_filtered.columns)}")
        return df_filtered
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理和处理数据
        
        Args:
            df: 标准化后的DataFrame
            
        Returns:
            清理后的DataFrame
        """
        df_cleaned = df.copy()
        
        # 处理空值
        df_cleaned = df_cleaned.fillna('')
        
        # 清理字符串列的前后空格
        string_columns = ['patent_number', 'wild_type', 'mutant', 'mutation', 
                         'statement', 'rule', 'comment']
        for col in string_columns:
            if col in df_cleaned.columns:
                df_cleaned[col] = df_cleaned[col].astype(str).str.strip()
        
        # 处理分组列，确保为整数
        if 'group' in df_cleaned.columns:
            # 将空值或非数字值设为0
            df_cleaned['group'] = pd.to_numeric(df_cleaned['group'], errors='coerce').fillna(0).astype(int)
        
        logger.debug(f"数据清理完成，有效行数: {len(df_cleaned)}")
        return df_cleaned
    
    def _build_json_structure(self, df: pd.DataFrame, source_file: Path) -> Dict[str, Any]:
        """构建JSON数据结构
        
        Args:
            df: 清理后的DataFrame
            source_file: 源Excel文件路径
            
        Returns:
            标准化的JSON数据结构
        """
        from datetime import datetime
        
        # 构建元数据
        metadata = {
            "source_file": str(source_file),
            "total_rows": len(df),
            "columns": list(df.columns),
            "conversion_timestamp": datetime.now().isoformat()
        }
        
        # 转换规则数据
        rules = []
        for _, row in df.iterrows():
            rule_entry = {}
            for col in df.columns:
                value = row[col]
                # 处理特殊值
                if pd.isna(value) or value == '':
                    rule_entry[col] = None
                elif col == 'group':
                    rule_entry[col] = int(value) if value != 0 else None
                else:
                    rule_entry[col] = str(value)
            
            rules.append(rule_entry)
        
        json_structure = {
            "metadata": metadata,
            "rules": rules
        }
        
        return json_structure
    
    def export_json(self, output_path: Union[str, Path], 
                   indent: int = 2, ensure_ascii: bool = False) -> None:
        """导出JSON文件
        
        Args:
            output_path: 输出文件路径
            indent: JSON缩进空格数
            ensure_ascii: 是否确保ASCII编码
            
        Raises:
            ValueError: 未执行转换操作
        """
        if self.data is None:
            raise ValueError("请先执行convert()方法进行转换")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=indent, ensure_ascii=ensure_ascii)
        
        logger.info(f"JSON文件已导出至: {output_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取转换统计信息
        
        Returns:
            包含统计信息的字典
        """
        if self.data is None:
            return {}
        
        rules = self.data['rules']
        
        # 基本统计
        stats = {
            "total_rules": len(rules),
            "total_groups": len(set(r['group'] for r in rules if r['group'] is not None)),
            "patent_count": len(set(r['patent_number'] for r in rules if r['patent_number'])),
            "rule_types": {}
        }
        
        # 规则类型统计
        rule_type_counts = {}
        for rule in rules:
            rule_type = rule.get('rule', 'unknown')
            if rule_type:
                rule_type_counts[rule_type] = rule_type_counts.get(rule_type, 0) + 1
        
        stats["rule_types"] = rule_type_counts
        
        return stats


def main():
    """命令行入口点，用于测试转换器"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Excel专利规则文件转JSON工具')
    parser.add_argument('excel_file', help='输入的Excel文件路径')
    parser.add_argument('-o', '--output', help='输出JSON文件路径', 
                       default='patent_rules.json')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='启用详细日志输出')
    
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 执行转换
        converter = ExcelToJsonConverter()
        result = converter.convert(args.excel_file)
        
        # 导出JSON
        converter.export_json(args.output)
        
        # 显示统计信息
        stats = converter.get_statistics()
        print("\n转换统计信息:")
        print(f"  总规则数: {stats['total_rules']}")
        print(f"  分组数: {stats['total_groups']}")
        print(f"  专利数: {stats['patent_count']}")
        print(f"  规则类型: {stats['rule_types']}")
        
        print(f"\nJSON文件已保存至: {args.output}")
        
    except Exception as e:
        logger.error(f"转换失败: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
