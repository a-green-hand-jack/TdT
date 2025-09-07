# Agent系统改进需求分析

## 问题概述

当前的Agent系统虽然能够成功分析专利并生成结果，但在实际使用中存在一些需要改进的问题。本文档整理了用户提出的具体改进需求，并分析解决方案。

## 具体问题

### 1. 文件自动生成问题

**现状**: 
- 当前JSON和Markdown文件需要手动创建
- 程序运行时由于JSON解析错误导致文件生成失败
- 用户期望程序运行结束后自动生成两类文件

**问题根因**:
- LLM响应的JSON格式包含markdown代码块标记(````json`)
- JSON解析器无法处理带有代码块标记的响应
- 异常处理不够完善，导致文件生成中断

**期望目标**:
- 程序运行结束后自动生成JSON和Markdown文件
- 即使LLM响应格式有问题，也要能保存可用的结果
- 提供稳定可靠的文件输出机制

### 2. 规则输出格式简化与结构化

**现状**: 
Agent当前生成的规则格式复杂，包含大量详细信息：
```json
{
  "rule_id": "R001",
  "rule_type": "mutation_pattern", 
  "protection_scope": "identical",
  "target_sequences": ["SEQ ID NO:1"],
  "mutation_combinations": [...],
  "identity_threshold": 0.95,
  "complexity_score": 8.0,
  "legal_description": "包含选自Y178A/F186R...",
  "technical_description": "该规则保护了TdT变体..."
}
```

**期望目标**:
基于专利保护的逻辑结构，采用简洁且结构化的格式：

#### 数据结构逻辑：
- **Group**: 每个group对应一个专利的完整保护范围
- **Patent**: 每个专利有唯一的patent_number  
- **Wild_type**: 每个专利通常有一种（偶尔多种）野生型序列
- **Mutant**: 每个专利通常有多种突变序列
- **Rule**: 使用逻辑表达式描述突变规则，而非穷举所有序列

#### 参考现有格式：
```json
{
  "group": 1,
  "patent_number": "CN107236717B / EP3438253B1", 
  "wild_type": "QSEPELKLESVVIVSRHGVRAPTKAT...",
  "mutant": "QSEPELKLESVVIVSRHGVRAPTKAT...",
  "mutation": "W46E/Q62W/G70E/A73P/K75C/S80P...",
  "statement": "SEQ ID NO:5与野生型序列一致性为95.61%...",
  "rule": "identical",
  "comment": "中国专利的权利要求为封闭式限定..."
}
```

#### 逻辑规则表达方式：
为了便于程序和LLM处理，采用数学逻辑表达式：

**基本逻辑操作符**：
- `AND` / `&` : 同时满足多个条件
- `OR` / `|` : 满足任一条件  
- `NOT` / `!` : 排除某些条件
- `()` : 逻辑分组

**示例规则表达**：
```json
{
  "rule": "identical",
  "mutation_logic": "(Y178A & F186R) | (I210L & I228L)",
  "identity_logic": "seq_identity >= 95%",
  "protection_logic": "mutation_logic AND identity_logic"
}
```

**复杂规则示例**：
```json
{
  "rule": "identity>80 & mutation_pattern",
  "mutation_logic": "((Y178A | Y178F) & (F186R | F186K)) | (position_330_343_conserved & position_449_460_conserved)",
  "identity_logic": "seq_identity >= 80%", 
  "protection_logic": "(mutation_logic | seq_identity >= 95%) AND NOT excluded_mutations"
}
```

**关键设计原则**:
- 使用逻辑表达式而非序列穷举
- 简洁的字段结构，避免冗余信息
- 明确的规则类型 (identical, identity>X%, conditional等)
- 结构化的突变位点表示
- 便于程序解析的逻辑语法

### 3. Agent功能聚焦问题

**现状**:
Agent当前生成大量内容：
- 复杂度分析
- 回避策略生成  
- 技术建议
- 风险评估
- 详细的法律和技术描述

**期望目标**:
- Agent应该专注于核心任务：**识别专利对序列的保护范围**
- 使用最简洁的语言描述保护内容
- 避免生成回避策略等无关内容
- 输出格式应该直接、实用

**核心需求**:
用户希望Agent回答的核心问题是：
> "这个专利对哪些序列提供了什么样的保护？"

而不是：
- 如何规避这个专利
- 专利的复杂度评估
- 详细的技术分析

## 解决方案设计

### 方案1: JSON解析容错机制

**技术实现**:
1. 在`llm_agent.py`中改进`_parse_analysis_response`方法
2. 添加对markdown代码块的处理
3. 实现备用解析机制
4. 确保即使解析失败也能保存原始响应

**代码改进点**:
```python
def _parse_analysis_response(self, response, patent_number):
    # 1. 尝试清理markdown标记
    # 2. 多种解析策略
    # 3. 失败时保存原始响应
    # 4. 返回部分可用结果
```

### 方案2: 结构化逻辑规则输出格式

**设计理念**:
1. 每个group对应一个专利的完整保护范围
2. 使用逻辑表达式描述保护规则，避免序列穷举
3. 采用数学逻辑操作符，便于程序和LLM处理
4. 简洁明确的字段结构

**新的输出格式设计**:

#### 基础格式（与现有JSON兼容）：
```json
{
  "group": 1,
  "patent_number": "CN 116555216 A",
  "wild_type": "SEQ_ID_NO_1的完整序列或标识",
  "rule": "identity>80 & mutation_pattern",
  "mutation": "Y178A/F186R/I210L/I228L",
  "statement": "包含特定突变组合且序列同一性≥80%的TdT变体",
  "comment": "专利采用混合保护策略：特定突变+同一性阈值"
}
```

#### 扩展格式（支持逻辑表达式）：
```json
{
  "group": 1,
  "patent_number": "CN 116555216 A",
  "wild_type": "SEQ_ID_NO_1",
  "rule": "conditional_protection",
  "mutation_logic": "(Y178A & F186R) | (I210L & I228L) | (R335A & K337G)",
  "identity_logic": "seq_identity >= 80%",
  "protection_logic": "mutation_logic AND identity_logic",
  "excluded_mutations": "NOT (Y178F & F186K)",
  "statement": "保护包含指定突变组合且序列同一性≥80%的变体",
  "comment": "双点组合突变的OR逻辑保护，排除特定组合"
}
```

#### 复杂专利的多规则表示：
```json
[
  {
    "group": 1,
    "patent_number": "CN 116555216 A", 
    "wild_type": "SEQ_ID_NO_1",
    "rule": "identical",
    "mutation": "Y178A/F186R/I210L/I228L",
    "statement": "与特定突变序列完全相同",
    "comment": "封闭式保护：精确突变组合"
  },
  {
    "group": 1,
    "patent_number": "CN 116555216 A",
    "wild_type": "SEQ_ID_NO_1", 
    "rule": "identity>80",
    "mutation_logic": "conserved_region_330_343 | conserved_region_449_460",
    "identity_logic": "seq_identity >= 80%",
    "statement": "包含保守区域突变且序列同一性≥80%",
    "comment": "开放式保护：保守区域+同一性阈值"
  }
]
```

**逻辑表达式语法规范**:
- 突变位点：`Y178A`, `F186R` (标准格式：原氨基酸+位置+新氨基酸)
- 逻辑AND：`&` 或 `AND`
- 逻辑OR：`|` 或 `OR`  
- 逻辑NOT：`!` 或 `NOT`
- 分组：`()` 
- 区域标识：`position_X_Y_conserved`, `conserved_region_X_Y`
- 同一性：`seq_identity >= X%`

### 方案3: Agent功能重新聚焦

**提示模板简化**:
1. 移除复杂度分析相关内容
2. 移除回避策略生成
3. 专注于保护范围识别
4. 使用直接、简洁的语言

**新的系统提示**:
```
你是专利序列保护分析专家。你的任务是识别专利权利要求对序列的保护范围，并使用结构化的逻辑表达式描述保护规则。

核心任务：
1. 识别专利保护的野生型序列（wild_type）
2. 识别专利保护的突变模式（mutation patterns）
3. 将复杂的保护条件转化为逻辑表达式
4. 确定保护规则类型（identical, identity>X%, conditional等）

输出要求：
1. 仅关注保护内容，不提供回避建议或复杂度分析
2. 使用逻辑操作符（&, |, !, ()）表达复杂规则
3. 按照group-patent-rule的层次结构组织信息
4. 使用简洁明确的语言，避免冗余信息

逻辑表达规范：
- 突变位点格式：Y178A（原氨基酸+位置+新氨基酸）
- 组合突变：(Y178A & F186R) 表示同时突变
- 可选突变：(Y178A | Y178F) 表示任一突变
- 复合条件：mutation_logic AND identity_logic
- 排除条件：NOT excluded_mutations
```

## 实施计划

### 阶段1: 修复文件生成机制
- [ ] 改进JSON解析的容错处理
- [ ] 确保文件始终能够生成
- [ ] 添加错误恢复机制

### 阶段2: 简化输出格式  
- [ ] 设计新的简洁JSON schema
- [ ] 修改提示模板
- [ ] 更新数据模型

### 阶段3: 重新聚焦Agent功能
- [ ] 简化系统提示
- [ ] 移除不必要的分析内容
- [ ] 测试新的输出效果

## 成功标准

1. **稳定性**: 程序每次运行都能生成JSON和Markdown文件
2. **简洁性**: 输出格式与现有规则JSON格式保持一致
3. **聚焦性**: Agent输出专注于保护范围识别，避免无关内容

## 设计细节说明

### 数据结构层次关系

```
Group (专利保护范围)
├── Patent_number (唯一专利标识)
├── Wild_type (野生型序列，通常1种，偶尔多种)
├── Mutants (突变序列，通常多种)
├── Rules (保护规则，用逻辑表达式描述)
│   ├── mutation_logic (突变逻辑)
│   ├── identity_logic (同一性逻辑)  
│   └── protection_logic (完整保护逻辑)
└── Comments (简洁的保护策略说明)
```

### 逻辑规则设计原则

1. **避免序列穷举**：使用逻辑表达式而非列举所有可能的突变序列
2. **数学逻辑操作**：采用标准的AND、OR、NOT操作符
3. **程序友好**：便于后续程序解析和LLM理解
4. **简洁表达**：用最少的字符表达最复杂的保护条件

### 典型保护模式示例

**模式1：封闭式精确保护**
```json
{
  "rule": "identical",
  "mutation": "Y178A/F186R/I210L/I228L",
  "comment": "必须与指定序列完全相同"
}
```

**模式2：开放式同一性保护**  
```json
{
  "rule": "identity>80",
  "identity_logic": "seq_identity >= 80%",
  "comment": "与野生型具有80%以上同一性即可"
}
```

**模式3：条件组合保护**
```json
{
  "rule": "conditional_protection", 
  "mutation_logic": "(Y178A & F186R) | (I210L & I228L)",
  "identity_logic": "seq_identity >= 95%",
  "protection_logic": "mutation_logic AND identity_logic",
  "comment": "特定突变组合+高同一性的混合保护"
}
```

**模式4：保守区域保护**
```json
{
  "rule": "conserved_region_protection",
  "mutation_logic": "conserved_region_330_343 | conserved_region_449_460", 
  "identity_logic": "seq_identity >= 90%",
  "comment": "保守区域突变+同一性阈值保护"
}
```

## 技术实施要求

### Agent输出聚焦
Agent应该回答且仅回答：
- **Wild_type**: 这个专利保护哪个（些）野生型序列？
- **Protection_scope**: 保护范围是什么（identical/identity>X%/conditional）？
- **Mutation_rules**: 突变规则是什么（用逻辑表达式）？
- **Key_conditions**: 关键保护条件是什么？

### 避免输出内容
- 回避策略建议
- 复杂度评估分析  
- 技术实施细节
- 风险评估报告
- 详细的法律分析

---

*待讨论确认后实施具体的代码修改*
