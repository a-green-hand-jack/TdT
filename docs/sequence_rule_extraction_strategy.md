<!--
这个文档记录了从TDT专利序列和权利要求中提炼规则的策略设计、讨论和实现过程。

作为一名经验丰富、代码风格严谨的Python技术专家和架构师，基于已有的专利权利要求书提取工具和现有的规则Excel文件，
设计并实现一个智能化的序列规则提炼系统。该系统需要能够：

1. **数据解析**：将Excel规则文件转换为结构化数据，便于分析和处理
2. **序列分析**：从FASTA和CSV序列文件中提取关键信息
3. **规则匹配**：将权利要求书中的序列保护描述与实际序列进行关联
4. **规则生成**：基于复杂度分析，生成简洁或详细的保护规则
5. **输出管理**：提供Excel和Markdown格式的规则输出

请确保实现高效、可扩展且易于维护的解决方案。
-->

# 序列规则提炼策略设计与实现

本文档记录了TDT酶专利序列规则提炼系统的设计讨论和实现过程。

## 目录
- [需求分析](#需求分析)
- [现有数据分析](#现有数据分析)
- [技术方案设计](#技术方案设计)
- [实现计划](#实现计划)
- [任务清单](#任务清单)
- [执行记录](#执行记录)

## 需求分析

### 核心目标
基于现有的PDF权利要求书提取工具，开发一个智能序列规则提炼系统，能够：
- 从专利权利要求书中识别序列保护模式
- 将复杂的法律描述转换为可操作的技术规则
- 根据规则复杂度选择适当的表达方式
- 生成标准化的规则文档

### 输入数据
1. **权利要求书文件** (examples/md/*.md)
   - 结构化的Markdown格式专利权利要求
   - 包含SEQ ID NO引用和氨基酸位置信息
   - 详细的突变位点和组合描述

2. **序列文件** (examples/seq/*.{FASTA,csv})
   - FASTA格式：蛋白质序列数据
   - CSV格式：包含序列ID、长度、类型和完整序列

3. **现有规则文件** (Patents/patent rules.xlsx)
   - 前人手工提取的规则模式
   - 包含分组、专利号、野生型、突变体等信息

### 预期输出
1. **规则JSON文件**：标准化的保护规则JSON格式，便于程序和LLM处理
2. **规则摘要文档**：便于理解的Markdown格式说明
3. **规则生成报告**：LLM分析结果和规则生成过程记录

## 现有数据分析

### Excel规则文件结构
基于`Patents/patent rules.xlsx`的分析：

```
列结构：
├── Group (A列)           # 分组编号 (1, 2, ...)
├── Patent Number (B列)   # 专利号 (CN107236717B/EP343825B1)
├── Wild-Type (C列)       # 野生型序列 (QSEPELKLESVVIVSF)
├── Mutant (D列)          # 突变体信息 (W46E/Q62W/G70E/A73P/...)
├── Mutation (E列)        # 突变描述
├── Statement (F列)       # 包含SEQ ID NO的声明
├── Rule (G列)            # 规则类型 (identical, identity>70)
└── Comment (H列)         # 中文备注和详细描述
```

### 规则模式分析
1. **序列同一性规则**
   - `identical`: 完全相同的序列
   - `identity>70`: 70%以上同一性的序列

2. **突变位点模式**
   - 单点突变：W46E, Q62W, G70E
   - 组合突变：W46E/Q62W/G70E/A73P/K75C/S80P
   - 位置范围：涉及多个氨基酸位置的复合突变

3. **SEQ ID NO引用**
   - 明确的序列标识符引用
   - 与具体突变位点的对应关系

### 权利要求书内容模式
基于已提取的权利要求书分析：

1. **CN118284690A模式**（复杂型）
   - 包含大量SEQ ID NO引用（2-5636）
   - 详细的氨基酸位置列表
   - 多重组合突变描述
   - 适合：详细规则列表或复杂度描述

2. **CN202210107337模式**（简洁型）
   - 明确的位点列表（Y178, F186, I210等）
   - 清晰的突变组合（Y178A/F186R）
   - 半保守区域定义
   - 适合：直接规则提取

## 技术方案设计

### 方案架构

```
数据流设计：
Excel规则文件 ──→ JSON结构化数据 ──→ 规则模式分析
     ↓                                    ↓
权利要求书 ────→ 序列信息提取 ────→ LLM规则生成Agent
     ↓                                    ↓
序列文件 ──────→ 序列数据解析 ────→ 智能规则生成器
                                         ↓
                                   JSON/MD输出
```

### 核心组件设计

#### 1. Excel转JSON转换器
```python
class ExcelToJsonConverter:
    """Excel专利规则文件转JSON转换器"""
    
    def convert(self, excel_path: str) -> Dict[str, Any]:
        """转换Excel文件为结构化JSON"""
        
    def validate_structure(self, data: Dict) -> bool:
        """验证数据结构完整性"""
        
    def export_json(self, data: Dict, output_path: str) -> None:
        """导出JSON文件"""
```

#### 2. 序列信息提取器
```python
class SequenceExtractor:
    """从权利要求书和序列文件中提取信息"""
    
    def extract_from_claims(self, md_path: str) -> ClaimsData:
        """从权利要求书提取序列引用"""
        
    def extract_from_sequences(self, seq_path: str) -> SequenceData:
        """从序列文件提取序列信息"""
        
    def identify_mutation_patterns(self, text: str) -> List[MutationPattern]:
        """识别突变模式"""
```

#### 3. LLM规则生成Agent
```python
class LLMRuleAgent:
    """基于大语言模型的规则生成智能体"""
    
    def analyze_patent_claims(self, claims_text: str, existing_rules: List[Dict]) -> AnalysisResult:
        """分析权利要求书内容，识别保护模式"""
        
    def extract_sequence_rules(self, analysis: AnalysisResult, 
                              sequences: SequenceData) -> RuleExtractions:
        """基于分析结果提取序列保护规则"""
        
    def generate_rule_json(self, extractions: RuleExtractions) -> Dict[str, Any]:
        """生成标准化的JSON格式规则"""
        
    def evaluate_rule_complexity(self, rules: Dict) -> ComplexityReport:
        """评估规则复杂度并提供表达建议"""
```

#### 4. 智能规则生成器
```python
class IntelligentRuleGenerator:
    """智能规则生成和输出管理器"""
    
    def __init__(self, llm_agent: LLMRuleAgent):
        """初始化，注入LLM Agent"""
        
    def generate_rules_from_patent(self, patent_data: PatentData) -> GeneratedRules:
        """从专利数据生成完整的保护规则"""
        
    def export_to_json(self, rules: GeneratedRules, path: str) -> None:
        """导出JSON格式规则文件"""
        
    def export_to_markdown(self, rules: GeneratedRules, path: str) -> None:
        """导出Markdown格式说明文档"""
        
    def generate_analysis_report(self, rules: GeneratedRules) -> str:
        """生成规则分析报告"""
```

### 技术选型

**核心依赖：**
- **Excel处理**：`openpyxl` - 强大的Excel读写能力
- **数据处理**：`pandas` - 高效的数据分析和转换
- **序列分析**：`biopython` - 专业的生物序列处理
- **LLM集成**：`openai` / `anthropic` - 大语言模型API调用
- **文本处理**：`re` - 正则表达式模式匹配
- **JSON处理**：`json` - 标准库JSON支持
- **提示工程**：`langchain` - LLM应用开发框架（可选）

**项目结构：**
```
src/tdt/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── excel_converter.py    # Excel转JSON转换器
│   ├── sequence_extractor.py # 序列信息提取器
│   ├── llm_agent.py          # LLM规则生成Agent
│   └── rule_generator.py     # 智能规则生成器
├── agents/
│   ├── __init__.py
│   ├── prompts.py            # LLM提示模板
│   ├── rule_analyzer.py      # 规则分析Agent
│   └── pattern_extractor.py  # 模式提取Agent
├── utils/
│   ├── __init__.py
│   ├── data_structures.py    # 数据结构定义
│   ├── validation.py         # 数据验证工具
│   └── llm_utils.py          # LLM工具函数
└── cli_rules.py              # 规则提炼命令行工具
```

## 实现计划

### 第一阶段：数据转换基础设施
1. 实现Excel到JSON的转换工具
2. 建立标准化的数据结构
3. 验证现有Excel文件的转换效果

### 第二阶段：序列信息提取
1. 开发权利要求书文本解析器
2. 实现FASTA/CSV序列文件解析
3. 构建突变模式识别算法

### 第三阶段：LLM Agent开发
1. 设计专利规则分析的提示模板
2. 实现LLM规则生成Agent
3. 开发规则复杂度评估算法
4. 建立JSON格式输出标准

### 第四阶段：智能规则生成系统
1. 集成LLM Agent到规则生成器
2. 实现JSON和Markdown输出功能
3. 添加详细的日志和进度反馈
4. 构建规则质量验证机制

### 第五阶段：测试和优化
1. 使用现有专利数据进行全面测试
2. 优化算法性能和准确性
3. 完善错误处理和异常情况

## 任务清单

### 数据转换
- [x] 实现Excel到JSON转换工具
- [x] 定义标准化数据结构
- [x] 验证现有Excel文件解析
- [x] 建立数据验证机制

### 序列分析
- [ ] 开发权利要求书解析器
- [ ] 实现FASTA文件解析
- [ ] 实现CSV序列文件解析
- [ ] 构建突变模式识别

### LLM Agent开发
- [ ] 设计专利分析提示模板
- [ ] 实现LLM规则生成Agent
- [ ] 开发规则复杂度评估
- [ ] 建立JSON输出标准
- [ ] 实现规则质量验证

### 智能规则生成
- [ ] 集成LLM Agent
- [ ] 实现JSON格式输出
- [ ] 实现Markdown格式输出
- [ ] 添加进度反馈
- [ ] 完善错误处理

### 测试验证
- [ ] 单元测试编写
- [ ] 集成测试设计
- [ ] 真实数据验证
- [ ] 性能优化

## 执行记录

### 2025-01-07 策略设计阶段
- [x] 分析Excel规则文件结构
- [x] 研究权利要求书内容模式
- [x] 设计技术方案架构
- [x] 制定详细实现计划
- [x] 实现Excel到JSON转换工具
- [x] 验证转换工具功能并分析数据模式

### 第一阶段完成情况
✅ **Excel转JSON转换工具完成**
- 成功解析了207条专利规则记录
- 涵盖51个不同专利，44个分组
- 识别出179种独特的突变模式
- 主要规则类型：88.9% identical，其余为identity阈值规则

✅ **数据模式分析完成**
- 发现规则复杂度差异很大：从简单的单点突变到复杂的多位点组合
- 专利保护范围分为封闭式（identical）和开放式（identity>X%）
- 需要处理的核心挑战：突变位点模式识别和复杂度评估

### 下一步计划
1. 实现Excel到JSON转换工具
2. 测试现有数据的转换效果
3. 建立标准化的数据结构
4. 为后续阶段做好基础设施准备

### 预期挑战
1. **文本解析复杂性**：权利要求书中的技术术语和格式多样
2. **规则复杂度判断**：需要智能判断何时使用简化表达
3. **序列匹配准确性**：确保SEQ ID NO与实际序列的正确对应
4. **输出格式标准化**：保持与现有Excel文件的兼容性

## JSON输出格式设计

### 标准化规则JSON结构
```json
{
  "metadata": {
    "patent_number": "CN118284690A",
    "extraction_timestamp": "2025-01-07T13:30:00Z",
    "source_files": {
      "claims": "examples/md/CN118284690A_claims.md",
      "sequences": "examples/seq/CN118284690A.csv"
    },
    "llm_model": "gpt-4",
    "analysis_confidence": 0.92
  },
  "rules": [
    {
      "rule_id": "R001",
      "rule_type": "sequence_identity",
      "protection_scope": "identical",
      "target_sequences": ["SEQ_ID_NO_2", "SEQ_ID_NO_4"],
      "mutation_patterns": [
        {
          "positions": [20, 21, 68, 103, 200],
          "mutations": ["W20E", "Q21W", "G68E", "A103P", "K200C"],
          "pattern_type": "combinatorial"
        }
      ],
      "complexity_score": 3.5,
      "representation_suggestion": "detailed_list",
      "avoidance_strategy": {
        "type": "exact_match_avoidance",
        "description": "避免与指定序列完全相同的突变组合"
      }
    }
  ],
  "analysis_summary": {
    "total_protected_sequences": 156,
    "complexity_distribution": {
      "simple": 45,
      "moderate": 87,
      "complex": 24
    },
    "recommended_strategies": [
      "focus_on_key_positions",
      "alternative_mutation_paths"
    ]
  }
}
```

### LLM Agent工作流程
1. **专利文本理解**：分析权利要求书的法律语言和技术描述
2. **序列模式识别**：识别SEQ ID NO引用和突变位点描述
3. **规则复杂度评估**：判断规则的复杂程度和表达难度
4. **回避策略生成**：基于理解生成具体的技术回避建议
5. **JSON格式输出**：将所有分析结果结构化为标准JSON

### 成功标准
1. 能够准确转换现有Excel规则文件
2. LLM Agent能够理解90%以上的专利权利要求内容
3. 生成的JSON规则与专家分析一致性达到85%以上
4. 系统处理速度满足实际使用需求
5. JSON输出格式便于程序和LLM进一步处理
