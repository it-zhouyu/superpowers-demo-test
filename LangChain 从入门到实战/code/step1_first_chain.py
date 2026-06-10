"""
Step 1: 第一个 Chain — 认识 ChatDeepSeek 和 LCEL 基础

本文件演示：
- 如何创建 ChatDeepSeek 实例
- AIMessage 的结构（content、response_metadata、id）
- LCEL（LangChain Expression Language）管道的基本用法
- 结合 ChatPromptTemplate 构建完整的对话链
"""

from langchain_deepseek import ChatDeepSeek
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


def main():
    # 创建 LLM 实例
    # temperature=0 让输出更稳定，适合教程演示
    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0,
    )

    # ============================================================
    # Demo 1: 直接调用 LLM，观察 AIMessage 的结构
    # ============================================================
    print("=" * 50)
    print("Demo 1: 直接调用 llm.invoke()")
    print("=" * 50)

    ai_message = llm.invoke("你好")

    # AIMessage 是 LangChain 对模型回复的封装，包含三个关键字段：
    print(f"\n[content] 模型回复的文本内容：\n{ai_message.content}")
    print(f"\n[response_metadata] 模型返回的元信息：\n{ai_message.response_metadata}")
    print(f"\n[id] 本次回复的唯一标识：\n{ai_message.id}")

    # ============================================================
    # Demo 2: 第一个 LCEL Chain — 用管道符 | 连接组件
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 2: LCEL Chain = llm | StrOutputParser")
    print("=" * 50)

    # LCEL 的核心思想：用 | 把组件串成一条处理链
    # StrOutputParser 把 AIMessage 转成纯字符串，省去手动取 .content
    chain = llm | StrOutputParser()

    result = chain.invoke("用一句话介绍 LangChain")
    print(f"\n{result}")

    # ============================================================
    # Demo 3: 带 Prompt Template 的完整 Chain
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 3: prompt | llm | StrOutputParser")
    print("=" * 50)

    # ChatPromptTemplate.from_messages 接收一个消息列表
    # 每个元素是 (role, template_string) 元组
    # 模板中的 {role} 和 {input} 是占位变量，invoke 时传入
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是{role}，请用专业但易懂的方式回答问题。"),
        ("human", "{input}"),
    ])

    # 完整链路：模板填充 -> 调用模型 -> 提取文本
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({
        "role": "一位资深 Python 开发工程师",
        "input": "Python 的 GIL 是什么？为什么它在多线程场景下很重要？",
    })
    print(f"\n{result}")


if __name__ == "__main__":
    main()
