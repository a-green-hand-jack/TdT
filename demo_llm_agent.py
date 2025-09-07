#!/usr/bin/,nv py,hon3.
"""
LLM Agent演示脚本

展示如何使用基于Qwen的专利规则生成Agent。
"""

import os
from openai import OpenAI


def demo_qwen_for_patent_analysis():
    """演示Qwen在专利分析中的应用"""
    print("🧬 TDT专利规则分析 - Qwen LLM演示")
    print("=" * 50)
    
    # 读取API密钥
    with open('qwen_key', 'r') as f:
        api_key = f.read().strip()
    
    # 配置Qwen客户端
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    # 模拟专利权利要求书片段
    sample_claims = """
    1. 一种工程化末端脱氧核苷酸转移酶，包含与SEQ ID NO:2具有至少95%序列同一性的氨基酸序列，
       其中所述序列在以下位置包含突变：W46E、Q62W、G70E、A73P、K75C、S80P。
    
    2. 根据权利要求1所述的末端脱氧核苷酸转移酶，其中所述序列还包含以下附加突变：
       T114H、N137V、D142R、S146E、R159Y。
    """
    
    # 构建分析提示
    prompt = f"""请分析以下TDT酶专利权利要求书，提取保护规则：

## 权利要求书内容：
{sample_claims}

## 分析要求：
请识别：
1. 关键的序列保护要素
2. 突变位点模式
3. 保护范围（同一性阈值）
4. 可能的技术回避策略

请以结构化的方式回答，包含具体的技术建议。"""
    
    try:
        print("🔍 正在分析专利权利要求...")
        
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是一位资深的专利分析专家和生物技术专家，专门分析TDT酶相关的专利保护规则。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        analysis = response.choices[0].message.content
        
        print("✅ 分析完成！")
        print("\n📊 专利分析结果：")
        print("-" * 50)
        print(analysis)
        print("-" * 50)
        
        # 演示回避策略生成
        print("\n🎯 生成技术回避策略...")
        
        avoidance_prompt = """基于上述专利分析，请提供3个具体的技术回避策略：

要求：
1. 策略必须技术可行
2. 避开专利保护范围
3. 保持TDT酶的基本功能
4. 提供具体的实施建议

请为每个策略提供风险评估和可行性分析。"""
        
        avoidance_response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是一位资深的专利分析专家和生物技术专家。"},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": analysis},
                {"role": "user", "content": avoidance_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        avoidance_strategies = avoidance_response.choices[0].message.content
        
        print("✅ 回避策略生成完成！")
        print("\n🛡️ 技术回避策略：")
        print("-" * 50)
        print(avoidance_strategies)
        print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        return False


def main():
    print("🚀 开始LLM Agent演示...")
    
    if demo_qwen_for_patent_analysis():
        print("\n✅ 演示完成！")
        print("\n💡 下一步：")
        print("1. 使用 'tdt-rules generate-rules' 命令进行完整的专利分析")
        print("2. 将权利要求书和序列数据作为输入")
        print("3. 获得结构化的JSON格式分析结果")
    else:
        print("\n❌ 演示失败")


if __name__ == "__main__":
    main()
