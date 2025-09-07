# TDT 酶专利序列提取项目

## 项目目的

本项目旨在从 TDT 酶相关的专利文件中提取受保护的序列，并将这些序列以规则的形式记录在 Excel 文件中。如果规则过于复杂，则使用文字描述；如果规则复杂但受保护的序列较少，则直接罗列这些序列。

## 工作方法

1. **专利文件解析**：
   - 从专利PDF文件中提取权利要求书内容
   - 使用轻量化PDF解析工具，专注文本内容提取
   - 生成便于LLM处理的结构化文本

2. **命令行工具**：
   - `tdt-extract info` - 分析PDF文件结构
   - `tdt-extract extract` - 提取单个PDF的权利要求书
   - `tdt-extract batch` - 批量处理目录中的PDF文件

3. **输出格式**：
   - 支持Markdown和纯文本格式
   - 保留原文件名，便于追溯
   - 结构化内容，便于后续分析

4. **技术栈**：
   - Python 3.10+ 
   - uv 包管理
   - pdfplumber 文本提取
   - Click 命令行框架

## 安装和使用

### 安装依赖
```bash
# 安装项目依赖
uv add pdfplumber click

# 开发模式安装
uv pip install -e .
```

### 使用示例
```bash
# 分析PDF文件结构
uv run tdt-extract info Patents/example.pdf

# 提取权利要求书内容
uv run tdt-extract extract Patents/example.pdf -o output -f markdown

# 批量处理
uv run tdt-extract batch Patents/ -o output -f markdown
```
