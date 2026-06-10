"""
Step 2: LCEL 与 Prompt Template 深入

本文件演示：
- ChatPromptTemplate 的多种用法（system/human/ai 角色）
- MessagesPlaceholder 注入对话历史
- JsonOutputParser 配合 Pydantic 模型输出结构化数据
- RunnablePassthrough.assign() 给输入添加字段
- RunnableParallel 并行执行多条链
- RunnableBranch 条件分支
"""

from pydantic import BaseModel, Field
from langchain_deepseek import ChatDeepSeek
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel, RunnableBranch
from langchain_core.messages import HumanMessage, AIMessage

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


def main():
    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0,
    )

    # ============================================================
    # Demo 1: ChatPromptTemplate.from_messages — 多角色消息模板
    # ============================================================
    print("=" * 50)
    print("Demo 1: ChatPromptTemplate 多角色模板")
    print("=" * 50)

    # from_messages 支持三种角色：system、human、ai
    # 可以在模板中混合多种角色，构建多轮对话的 prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个{style}风格的翻译官。"),
        ("human", "请把以下内容翻译成英文：{text}"),
    ])

    # .invoke() 只做模板填充，不调用模型
    # 返回的是 ChatPromptValue，可以 .to_messages() 查看生成的消息列表
    formatted = prompt.invoke({
        "style": "幽默",
        "text": "今天天气真好",
    })
    print(f"\n[模板填充结果] 类型: {type(formatted).__name__}")
    for msg in formatted.to_messages():
        print(f"  {msg.type}: {msg.content}")

    # ============================================================
    # Demo 2: MessagesPlaceholder — 注入对话历史
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 2: MessagesPlaceholder 注入对话历史")
    print("=" * 50)

    # MessagesPlaceholder("history") 会在 invoke 时被一组消息替换
    # 这在实现多轮对话时非常有用
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个有帮助的AI助手。"),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ])

    # 模拟之前的对话历史
    history = [
        HumanMessage(content="LangChain 是什么？"),
        AIMessage(content="LangChain 是一个用于构建 LLM 应用的框架。"),
    ]

    formatted = prompt.invoke({
        "history": history,
        "input": "它有哪些核心模块？",
    })
    print(f"\n[带历史的消息列表]")
    for msg in formatted.to_messages():
        print(f"  {msg.type}: {msg.content}")

    # ============================================================
    # Demo 3: 完整 LCEL 链 — prompt | llm | parser
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 3: 完整 LCEL 链 prompt | llm | StrOutputParser")
    print("=" * 50)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是 Python 专家，回答要简洁，不超过 3 句话。"),
        ("human", "{question}"),
    ])
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({"question": "Python 的装饰器是什么？"})
    print(f"\n{result}")

    # ============================================================
    # Demo 4: JsonOutputParser + Pydantic — 结构化输出
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 4: JsonOutputParser + Pydantic 结构化输出")
    print("=" * 50)

    # 定义一个 Pydantic 模型来描述期望的输出结构
    class MovieReview(BaseModel):
        title: str = Field(description="电影名称")
        rating: float = Field(description="评分，1-10 分")
        summary: str = Field(description="一句话评价")

    # JsonOutputParser 会把 LLM 的输出解析成字典
    # get_format_instructions() 返回一段提示词，告诉模型按什么格式输出
    parser = JsonOutputParser(pydantic_object=MovieReview)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个电影评论家。{format_instructions}"),
        ("human", "请评价电影：{movie}"),
    ])

    # 用 partial 把 format_instructions 提前注入模板
    # 这样 invoke 时不需要每次都传 format_instructions
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    result = chain.invoke({"movie": "星际穿越"})
    print(f"\n[解析结果] 类型: {type(result).__name__}")
    print(f"  电影: {result['title']}")
    print(f"  评分: {result['rating']}")
    print(f"  评价: {result['summary']}")

    # ============================================================
    # Demo 5: RunnablePassthrough.assign() — 给输入添加字段
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 5: RunnablePassthrough.assign() 添加字段")
    print("=" * 50)

    # RunnablePassthrough.assign() 接收一个字典，
    # 字典的值可以是函数或 Runnable，用来计算新字段的值
    # 原始输入会原样保留，新字段追加进去
    enriched = RunnablePassthrough.assign(
        context=lambda x: f"用户正在问关于「{x['topic']}」的问题",
    )

    # 把 enrich 和链串起来
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{context}。请简洁回答。"),
        ("human", "{question}"),
    ])
    chain = enriched | prompt | llm | StrOutputParser()

    result = chain.invoke({
        "topic": "Python",
        "question": "列表推导式和 map 函数哪个更好？",
    })
    print(f"\n{result}")

    # ============================================================
    # Demo 6: RunnableParallel — 并行执行多条链
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 6: RunnableParallel 并行执行")
    print("=" * 50)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个有帮助的助手，用一句话回答。"),
        ("human", "{question}"),
    ])
    chain = prompt | llm | StrOutputParser()

    # RunnableParallel 同时运行多个 Runnable，各自独立，结果合并成一个字典
    # 这里的两条链共享同一个 llm，但 prompt 不同
    prompt_cn = ChatPromptTemplate.from_messages([
        ("system", "用中文回答，不超过一句话。"),
        ("human", "{question}"),
    ])
    prompt_en = ChatPromptTemplate.from_messages([
        ("system", "Answer in English, one sentence only."),
        ("human", "{question}"),
    ])

    parallel_chain = RunnableParallel(
        chinese=prompt_cn | llm | StrOutputParser(),
        english=prompt_en | llm | StrOutputParser(),
    )

    result = parallel_chain.invoke({"question": "什么是机器学习？"})
    print(f"\n[中文回答] {result['chinese']}")
    print(f"[英文回答] {result['english']}")

    # ============================================================
    # Demo 7: RunnableBranch — 条件分支
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 7: RunnableBranch 条件分支")
    print("=" * 50)

    # RunnableBranch 根据输入内容自动选择不同的处理链
    # 参数是一系列 (条件函数, Runnable) 元组，最后一个不加条件作为默认分支
    math_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个数学老师，只回答数学问题，给出计算过程。"),
        ("human", "{question}"),
    ])

    translate_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个翻译官，只做翻译，直接给出翻译结果。"),
        ("human", "{question}"),
    ])

    general_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个通用助手，简洁回答。"),
        ("human", "{question}"),
    ])

    def is_math(x):
        keywords = ["计算", "加", "减", "乘", "除", "数学", "等于"]
        return any(k in x["question"] for k in keywords)

    def is_translate(x):
        keywords = ["翻译", "translate", "英文", "中文"]
        return any(k in x["question"] for k in keywords)

    branch = RunnableBranch(
        (is_math, math_prompt | llm | StrOutputParser()),
        (is_translate, translate_prompt | llm | StrOutputParser()),
        general_prompt | llm | StrOutputParser(),  # 默认分支
    )

    # 测试数学问题
    result1 = branch.invoke({"question": "计算 123 乘以 456"})
    print(f"\n[数学问题] 计算 123 乘以 456")
    print(f"  回答: {result1}")

    # 测试翻译问题
    result2 = branch.invoke({"question": "把「今天天气真好」翻译成英文"})
    print(f"\n[翻译问题] 把「今天天气真好」翻译成英文")
    print(f"  回答: {result2}")

    # 测试通用问题
    result3 = branch.invoke({"question": "什么是 Python 的列表推导式？"})
    print(f"\n[通用问题] 什么是 Python 的列表推导式？")
    print(f"  回答: {result3}")


if __name__ == "__main__":
    main()
