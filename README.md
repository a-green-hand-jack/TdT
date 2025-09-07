# TDT 酶专利序列提取项目

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Completed-brightgreen.svg)](README.md)

## 🎯 项目目的

本项目旨在从 TDT 酶相关的专利文件中提取受保护的序列，并将这些序列以规则的形式记录在 Excel 文件中。如果规则过于复杂，则使用文字描述；如果规则复杂但受保护的序列较少，则直接罗列这些序列。

**当前状态：✅ 权利要求书提取工具已完成开发**

## 🚀 核心功能

### 1. **PDF权利要求书提取**
- 🔍 智能识别PDF中的权利要求书章节
- 🧹 自动清理页眉页脚信息，保持内容纯净
- 📄 支持多种PDF格式和编码
- 🔢 准确提取专利申请公布号

### 2. **命令行工具**
```bash
tdt-extract info     # 分析PDF文件结构
tdt-extract extract  # 提取单个PDF的权利要求书
tdt-extract batch    # 批量处理目录中的PDF文件
```

### 3. **输出格式**
- 📝 **Markdown格式**：结构化，便于LLM处理
- 📄 **纯文本格式**：简洁，便于人工阅读
- 🏷️ **文件信息**：保留原文件名、专利号、提取时间
- 🎯 **LLM友好**：优化格式，便于后续AI分析

### 4. **技术特性**
- ⚡ **轻量化实现**：专注文本提取，无图像处理
- 🔧 **uv包管理**：现代Python依赖管理
- 🏗️ **模块化设计**：核心解析器与CLI分离
- 🧪 **健壮性**：全面的错误处理和日志记录

## 📦 安装和使用

### 环境要求
- Python 3.10+
- uv 包管理器

### 安装依赖
```bash
# 克隆项目
git clone git@github.com:a-green-hand-jack/TdT.git
cd TdT

# 安装项目依赖
uv sync

# 开发模式安装
uv pip install -e .
```

### 使用示例

#### 基本用法
```bash
# 分析PDF文件结构
uv run tdt-extract info examples/pdf/CN118284690A.pdf

# 提取单个PDF的权利要求书
uv run tdt-extract extract examples/pdf/CN118284690A.pdf -o examples/md -f markdown

# 批量处理目录中的所有PDF
uv run tdt-extract batch examples/pdf/ -o examples/md -f markdown

# 强制覆盖已存在的输出文件
uv run tdt-extract extract examples/pdf/CN118284690A.pdf -o examples/md -f markdown --force
```

#### 输出示例
```markdown
# 权利要求书

## 文档信息

**源文件：** `CN118284690A.pdf`  
**专利申请公布号：** CN 118284690 A  
**提取页面：** 第2-30页  
**提取时间：** 2025-09-07 11:31:11  

---

1. 一种工程化末端脱氧核苷酸转移酶,包含与SEQ ID NO:2、4、580...
   [权利要求书内容]

---

*此文档由 TDT 专利序列提取工具自动生成*
```

## 📈 项目进展时间线

### Phase 1: 项目初始化 (2025-09-07 上午)
- ✅ Git仓库初始化和基本项目结构搭建
- ✅ README文档创建和项目目标明确
- ✅ .gitignore配置，排除ZIP文件和临时文件
- ✅ docs目录建立，PDF解析讨论文档创建

### Phase 2: 核心功能开发 (2025-09-07 上午-中午)
- ✅ uv依赖管理配置和pyproject.toml设置
- ✅ PDF解析核心模块 (`tdt.core.parser`) 实现
- ✅ 权利要求书提取器 (`tdt.core.extractor`) 开发
- ✅ 命令行接口 (`tdt.cli`) 完整实现
- ✅ 支持info/extract/batch三个子命令

### Phase 3: 问题修复和优化 (2025-09-07 中午)
- ✅ **页眉页脚清理问题修复**
  - 解决页眉信息（如"权利要求书 CN 118284690 A 1/29 页"）嵌入内容
  - 实现`_light_clean_headers`函数优化清理逻辑
  - 添加`_final_cleanup_footers`函数处理数字页脚

- ✅ **专利号识别功能完善**
  - 新增`_extract_patent_number_from_pages`函数
  - 从页面数据（页眉）中准确提取专利申请公布号
  - 支持多种专利号格式：CN118284690A、CN202210107337等

### Phase 4: 测试验证 (2025-09-07 中午)
- ✅ **测试文件验证**
  - CN118284690A.pdf → 专利号: "CN 118284690 A" ✓
  - CN202210107337.pdf → 专利号: "CN 116555216 A" ✓
- ✅ **功能完整性测试**
  - 页脚清理：成功移除`3300`、`33`等数字页脚 ✓
  - 页眉清理：智能移除页眉信息，保持正文完整 ✓
  - 格式化输出：结构化Markdown，LLM友好 ✓

## 🛠️ 技术架构

```
src/tdt/
├── __init__.py          # 包初始化
├── cli.py              # 命令行接口
└── core/
    ├── parser.py       # PDF解析核心
    ├── extractor.py    # 权利要求书提取器
    └── utils.py        # 工具函数
```

### 核心组件

1. **PDFParser** (`core.parser`)
   - 基于pdfplumber的PDF文本提取
   - 页面级别的内容和元数据解析
   - 支持多种编码和格式

2. **PDFClaimsExtractor** (`core.extractor`)
   - 智能识别权利要求书章节
   - 多层次的内容清理和格式化
   - 专利信息提取和结构化输出

3. **CLI接口** (`cli.py`)
   - Click框架的现代命令行界面
   - 进度条和详细日志输出
   - 灵活的参数配置

## 🔍 技术细节

### 权利要求书识别算法
- 关键词匹配：支持"权利要求书"、"Claims"等多种变体
- 位置验证：检查页眉位置确认章节开始
- 内容连续性：智能处理跨页内容合并

### 页眉页脚清理策略
1. **页眉清理**：移除专利号、页数等页眉信息
2. **页脚清理**：识别并移除2-6位数字页脚
3. **行内清理**：处理嵌入在内容中的页眉信息

### 专利号提取逻辑
- 优先从页面数据（页眉）提取
- 支持多种格式：CN118284690A、CN 118284690 A、CN202210107337
- 备用方案：从正文内容中提取

## 📋 下一步计划

1. **序列提取模块**：开发从权利要求书中提取具体序列的逻辑
2. **Excel输出功能**：将提取的序列和规则整理到Excel文件
3. **规则分析引擎**：智能分析序列保护规则的复杂度
4. **批量处理优化**：提升大量文件处理的性能
