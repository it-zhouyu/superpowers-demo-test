"""
Step 4: Conversation Memory
演示 ChatMessageHistory、RunnableWithMessageHistory、trim_messages 的用法
"""

from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import trim_messages, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_deepseek import ChatDeepSeek

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ==================================================
# Demo 1: ChatMessageHistory 基本用法
# ==================================================
def demo1_basic_history():
    print("=" * 50)
    print("Demo 1: ChatMessageHistory 基本用法")
    print("=" * 50)

    # 创建一个内存中的聊天历史记录
    history = ChatMessageHistory()

    # 添加消息（支持 HumanMessage、AIMessage 等类型）
    history.add_user_message("你好，我想学习 Python")
    history.add_ai_message("你好！Python 是一门非常适合入门的编程语言。")
    history.add_user_message("从哪里开始学比较好？")
    history.add_ai_message("建议从基础语法开始，比如变量、循环、函数。")

    # 查看所有消息
    messages = history.messages
    print(f"历史消息数量: {len(messages)}")
    for msg in messages:
        print(f"  [{msg.type}] {msg.content}")

    # 也可以用 ChatMessageHistory（非线程安全版本）
    chat_history = ChatMessageHistory()
    chat_history.add_user_message("测试消息")
    chat_history.add_ai_message("收到")
    print(f"\nChatMessageHistory 消息数: {len(chat_history.messages)}")

    # 按 session 管理多个历史记录（用字典存储）
    store = {}  # session_id -> ChatMessageHistory
    store["session_1"] = history
    store["session_2"] = ChatMessageHistory()
    store["session_2"].add_user_message("这是第二个会话")

    print(f"\n会话 session_1 消息数: {len(store['session_1'].messages)}")
    print(f"会话 session_2 消息数: {len(store['session_2'].messages)}")


# ==================================================
# Demo 2: RunnableWithMessageHistory 包装 Chain
# ==================================================
def demo2_runnable_with_history():
    print("\n" + "=" * 50)
    print("Demo 2: RunnableWithMessageHistory 包装 Chain")
    print("=" * 50)

    # 创建 LLM
    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 创建带 history 占位符的 prompt
    # MessagesPlaceholder("history") 会在运行时被实际的历史消息替换
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个友好的编程助手，用中文回答问题。回答要简洁。"),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ])

    # 构建 chain: prompt -> llm -> 输出解析
    chain = prompt | llm | StrOutputParser()

    # 用字典管理多个会话的历史记录
    store = {}

    def get_session_history(session_id: str) -> ChatMessageHistory:
        """根据 session_id 获取或创建对应的聊天历史"""
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

    # 用 RunnableWithMessageHistory 包装 chain
    # - input_messages_key: 用户输入在 chain invoke 参数中的 key
    # - history_messages_key: 历史消息在 prompt 中的占位符 key
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )

    # 多轮对话 - 第一轮
    print("\n--- 第一轮对话 (session_abc) ---")
    response1 = chain_with_history.invoke(
        {"input": "我叫小明，我想学 Java"},
        config={"configurable": {"session_id": "session_abc"}},
    )
    print(f"AI: {response1}")

    # 第二轮 - AI 应该记得"小明"和"Java"
    print("\n--- 第二轮对话 (session_abc) ---")
    response2 = chain_with_history.invoke(
        {"input": "你还记得我的名字吗？我想学什么语言？"},
        config={"configurable": {"session_id": "session_abc"}},
    )
    print(f"AI: {response2}")

    # 查看当前 session 的历史记录
    print(f"\n--- session_abc 历史记录 ---")
    for msg in store["session_abc"].messages:
        print(f"  [{msg.type}] {msg.content}")

    # 用不同 session_id 开启新对话 - AI 不会记得之前的内容
    print("\n--- 新会话 (session_xyz) ---")
    response3 = chain_with_history.invoke(
        {"input": "你知道我是谁吗？"},
        config={"configurable": {"session_id": "session_xyz"}},
    )
    print(f"AI: {response3}")


# ==================================================
# Demo 3: trim_messages 用法
# ==================================================
def demo3_trim_messages():
    print("\n" + "=" * 50)
    print("Demo 3: trim_messages 用法")
    print("=" * 50)

    # 模拟一段很长的对话历史
    messages = [
        SystemMessage(content="你是一个编程助手"),
        HumanMessage(content="什么是变量？"),
        AIMessage(content="变量是存储数据的容器。"),
        HumanMessage(content="什么是函数？"),
        AIMessage(content="函数是可复用的代码块。"),
        HumanMessage(content="什么是类？"),
        AIMessage(content="类是面向对象编程的基础。"),
        HumanMessage(content="什么是模块？"),
        AIMessage(content="模块是组织代码的方式。"),
        HumanMessage(content="什么是装饰器？"),
        AIMessage(content="装饰器是修改函数行为的语法糖。"),
    ]

    print(f"原始消息数量: {len(messages)}")
    for msg in messages:
        print(f"  [{msg.type}] {msg.content}")

    # trim_messages: 按 token 数量裁剪消息列表，保留最重要的消息
    # - max_tokens: 保留的最大 token 数
    # - strategy: "last" 表示保留最近的消息
    # - token_counter: 计数方式，"len" 用消息数量（简单演示）
    # - include_system: 是否始终保留 system 消息
    # - allow_partial: 是否允许截断单条消息
    trimmed = trim_messages(
        messages,
        max_tokens=5,       # 最多保留 5 条（这里用 len 做计数）
        strategy="last",    # 保留最近的
        token_counter=len,  # 用消息条数而非真实 token 数（生产环境可用 llm 作为 counter）
        include_system=True,  # 始终保留 system 消息
        allow_partial=False,
    )

    print(f"\n裁剪后消息数量: {len(trimmed)}")
    for msg in trimmed:
        print(f"  [{msg.type}] {msg.content}")

    # 也可以用 "first" 策略保留最早的消息（不常用）
    trimmed_first = trim_messages(
        messages,
        max_tokens=3,
        strategy="first",
        token_counter=len,
        include_system=False,
        allow_partial=False,
    )
    print(f"\nfirst 策略裁剪后: {len(trimmed_first)} 条")
    for msg in trimmed_first:
        print(f"  [{msg.type}] {msg.content}")


# ==================================================
# Demo 4: Chain + History + trim_messages 组合使用
# ==================================================
def demo4_chain_with_trim():
    print("\n" + "=" * 50)
    print("Demo 4: Chain + History + trim_messages 组合使用")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 在 chain 中加入 trim 逻辑，控制上下文长度
    # 思路: 在 get_session_history 返回消息前，先 trim 一下
    store = {}

    def get_trimmed_history(session_id: str) -> ChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()

        raw_history = store[session_id]
        if len(raw_history.messages) > 4:
            # 历史消息超过 4 条时，裁剪到只保留最近 4 条
            trimmed = trim_messages(
                raw_history.messages,
                max_tokens=4,
                strategy="last",
                token_counter=len,
                include_system=False,  # 这里没有 system 消息在 history 中
                allow_partial=False,
            )
            # 创建新的 history 对象，只包含裁剪后的消息
            new_history = ChatMessageHistory()
            for msg in trimmed:
                new_history.add_message(msg)
            return new_history

        return raw_history

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个编程助手，用中文简洁回答。"),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ])

    chain = prompt | llm | StrOutputParser()

    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_trimmed_history,
        input_messages_key="input",
        history_messages_key="history",
    )

    # 连续发 6 轮对话，观察 trim 效果
    questions = [
        "什么是 Python 的列表？",
        "什么是字典？",
        "什么是元组？",
        "什么是集合？",
        "什么是生成器？",
        "回顾一下：我前面问过列表和字典，你还记得吗？",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n--- 第 {i} 轮 ---")
        print(f"用户: {question}")
        response = chain_with_history.invoke(
            {"input": question},
            config={"configurable": {"session_id": "trim_demo"}},
        )
        print(f"AI: {response}")
        # 显示当前存储的历史消息数
        print(f"(历史消息数: {len(store['trim_demo'].messages)})")

    # 最终历史记录
    print(f"\n--- trim_demo 会话最终历史 ({len(store['trim_demo'].messages)} 条) ---")
    for msg in store["trim_demo"].messages:
        content = msg.content[:40] + "..." if len(msg.content) > 40 else msg.content
        print(f"  [{msg.type}] {content}")


# ==================================================
# Main
# ==================================================
if __name__ == "__main__":
    # Demo 1 不需要 API 调用，纯本地操作
    demo1_basic_history()

    # Demo 2 需要 API
    demo2_runnable_with_history()

    # Demo 3 不需要 API 调用，纯本地操作
    demo3_trim_messages()

    # Demo 4 需要 API
    demo4_chain_with_trim()
