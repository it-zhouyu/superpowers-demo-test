"""
LangGraph 教程 - Step 7: Persistence（持久化）

演示状态持久化与状态管理：
1. MemorySaver 基本用法 - 跨调用保持状态
2. 多线程隔离 - 不同对话互不干扰
3. 状态检查 - get_state / get_state_history
4. 状态修改 - update_state
5. 部署方式概述
"""

import uuid
from typing import TypedDict, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_deepseek import ChatDeepSeek
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 定义状态和 LLM
# ============================================================

class ChatState(TypedDict):
    """聊天状态"""
    messages: Annotated[list[BaseMessage], add_messages]


llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    api_base=DEEPSEEK_BASE_URL,
)


def chatbot_node(state: ChatState) -> dict:
    """聊天节点"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def build_chatbot(checkpointer=None):
    """构建聊天机器人图"""
    graph = StateGraph(ChatState)
    graph.add_node("chatbot", chatbot_node)
    graph.add_edge(START, "chatbot")
    graph.add_edge("chatbot", END)
    return graph.compile(checkpointer=checkpointer)


# ============================================================
# Demo 1: MemorySaver 基本用法
# ============================================================

def demo1_memory_saver():
    """Demo 1: 使用 MemorySaver 保持跨调用的状态"""
    print("=" * 50)
    print("Demo 1: MemorySaver 基本用法")
    print("=" * 50)

    checkpointer = MemorySaver()
    app = build_chatbot(checkpointer)

    thread_id = f"chat-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    # 第一轮对话
    print(f"\n--- 第一轮（thread_id={thread_id}）---")
    result = app.invoke(
        {"messages": [HumanMessage(content="我叫小明，记住我的名字。")]},
        config,
    )
    print(f"AI: {result['messages'][-1].content}")

    # 第二轮对话：验证记忆保持
    print(f"\n--- 第二轮（同 thread_id）---")
    result = app.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？")]},
        config,
    )
    print(f"AI: {result['messages'][-1].content}")

    # 第三轮对话：继续对话
    print(f"\n--- 第三轮（同 thread_id）---")
    result = app.invoke(
        {"messages": [HumanMessage(content="给我推荐一个 Python 学习资源。")]},
        config,
    )
    print(f"AI: {result['messages'][-1].content}")

    # 对比：没有 checkpointer 的情况
    print(f"\n--- 对比: 无 checkpointer ---")
    app_no_memory = build_chatbot()
    result = app_no_memory.invoke(
        {"messages": [HumanMessage(content="我叫什么名字？")]}
    )
    print(f"AI（无记忆）: {result['messages'][-1].content}")


# ============================================================
# Demo 2: 多线程隔离
# ============================================================

def demo2_multiple_threads():
    """Demo 2: 不同 thread_id 的对话完全隔离"""
    print("\n" + "=" * 50)
    print("Demo 2: 多线程隔离")
    print("=" * 50)

    checkpointer = MemorySaver()
    app = build_chatbot(checkpointer)

    # 线程 A: Python 对话
    thread_a = "thread-python"
    config_a = {"configurable": {"thread_id": thread_a}}

    print(f"\n--- 线程 A ({thread_a}): 聊 Python ---")
    result = app.invoke(
        {"messages": [HumanMessage(content="Python 最大的优势是什么？")]},
        config_a,
    )
    print(f"AI: {result['messages'][-1].content[:150]}...")

    # 线程 B: Java 对话
    thread_b = "thread-java"
    config_b = {"configurable": {"thread_id": thread_b}}

    print(f"\n--- 线程 B ({thread_b}): 聊 Java ---")
    result = app.invoke(
        {"messages": [HumanMessage(content="Java 最大的优势是什么？")]},
        config_b,
    )
    print(f"AI: {result['messages'][-1].content[:150]}...")

    # 回到线程 A 继续对话
    print(f"\n--- 回到线程 A: 继续 Python 对话 ---")
    result = app.invoke(
        {"messages": [HumanMessage(content="我之前问的是什么语言？")]},
        config_a,
    )
    print(f"AI: {result['messages'][-1].content}")

    # 在线程 B 中问同样的问题
    print(f"\n--- 线程 B: 问同样的问题 ---")
    result = app.invoke(
        {"messages": [HumanMessage(content="我之前问的是什么语言？")]},
        config_b,
    )
    print(f"AI: {result['messages'][-1].content}")


# ============================================================
# Demo 3: 状态检查
# ============================================================

def demo3_state_inspection():
    """Demo 3: 使用 get_state 和 get_state_history 检查状态"""
    print("\n" + "=" * 50)
    print("Demo 3: 状态检查")
    print("=" * 50)

    checkpointer = MemorySaver()
    app = build_chatbot(checkpointer)

    thread_id = f"inspect-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    # 执行几轮对话
    print(f"\n--- 执行 3 轮对话（thread_id={thread_id}）---")
    app.invoke({"messages": [HumanMessage(content="第一轮：你好")]}, config)
    app.invoke({"messages": [HumanMessage(content="第二轮：介绍一下自己")]}, config)
    result = app.invoke({"messages": [HumanMessage(content="第三轮：今天天气怎么样")]}, config)

    # 查看当前状态
    print(f"\n--- get_state(): 当前状态 ---")
    state = app.get_state(config)
    print(f"待执行节点: {state.next}")
    print(f"消息总数: {len(state.values.get('messages', []))}")
    print(f"创建时间: {state.created_at}")
    print(f"父配置: {state.parent_config}")

    # 查看所有消息
    print(f"\n--- 当前状态中的消息 ---")
    for i, msg in enumerate(state.values.get("messages", [])):
        role = "Human" if isinstance(msg, HumanMessage) else "AI"
        content = msg.content[:80] if len(msg.content) > 80 else msg.content
        print(f"  [{i}] {role}: {content}")

    # 查看状态历史
    print(f"\n--- get_state_history(): 状态历史 ---")
    history_count = 0
    for hist_state in app.get_state_history(config):
        history_count += 1
        msg_count = len(hist_state.values.get("messages", []))
        print(f"  历史 {history_count}: "
              f"next={hist_state.next}, "
              f"消息数={msg_count}, "
              f"时间={hist_state.created_at}")
        if history_count >= 10:
            print(f"  ... (只显示前 10 条)")
            break

    # 统计总历史数
    total = sum(1 for _ in app.get_state_history(config))
    print(f"\n  共 {total} 个历史状态")


# ============================================================
# Demo 4: 状态修改
# ============================================================

def demo4_state_modification():
    """Demo 4: 使用 update_state 手动修改状态"""
    print("\n" + "=" * 50)
    print("Demo 4: 状态修改")
    print("=" * 50)

    checkpointer = MemorySaver()
    app = build_chatbot(checkpointer)

    thread_id = f"modify-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    # 初始对话
    print(f"\n--- 初始对话 ---")
    app.invoke({"messages": [HumanMessage(content="我住在上海")]}, config)
    result = app.invoke({"messages": [HumanMessage(content="推荐一下附近好玩的地方")]}, config)
    print(f"AI: {result['messages'][-1].content[:150]}...")

    # 查看修改前的状态
    print(f"\n--- 修改前状态 ---")
    state = app.get_state(config)
    msg_count = len(state.values.get("messages", []))
    print(f"消息数: {msg_count}")

    # 注入一条系统提示，纠正上下文
    print(f"\n--- update_state: 注入额外上下文 ---")
    app.update_state(
        config,
        {"messages": [HumanMessage(content="补充信息：我说的上海是指上海的浦东新区")]},
        as_node="chatbot",
    )

    # 查看修改后的状态
    state = app.get_state(config)
    new_msg_count = len(state.values.get("messages", []))
    print(f"修改后消息数: {new_msg_count}")

    # 基于修改后的状态继续对话
    print(f"\n--- 修改后继续对话 ---")
    result = app.invoke(
        {"messages": [HumanMessage(content="基于我补充的信息，再推荐一下附近好玩的地方")]},
        config,
    )
    print(f"AI: {result['messages'][-1].content[:200]}...")


# ============================================================
# Demo 5: 部署概述
# ============================================================

def demo5_deployment_overview():
    """Demo 5: 部署方式概述（仅打印说明）"""
    print("\n" + "=" * 50)
    print("Demo 5: 部署概述")
    print("=" * 50)

    print("""
--- LangGraph 部署方式 ---

1. 本地开发（langgraph dev）
   - 命令: langgraph dev
   - 启动本地开发服务器，支持热重载
   - 自带 Web UI 用于测试和调试
   - 使用 MemorySaver 作为内存级别的 checkpointer

2. 云端部署（LangGraph Cloud / LangGraph Studio）
   - 命令: langgraph deploy
   - 部署到 LangGraph Cloud
   - 自动提供 API 接口、状态管理、并发处理
   - 支持水平扩展和负载均衡

3. 自托管部署（Self-hosted）
   - 使用 PostgreSQL 作为生产级 checkpointer
   - pip install langgraph-checkpoint-postgres
   - 适合需要数据私有化的企业场景

4. Checkpointer 选择:
   - MemorySaver: 内存存储，进程重启后丢失（开发用）
   - SqliteSaver: SQLite 文件存储（轻量级生产）
   - AsyncPostgresSaver: PostgreSQL 存储（生产推荐）

5. 生产环境推荐:
   - 持久化: PostgreSQL checkpointer
   - 部署: Docker 容器 + langgraph server
   - 监控: LangSmith 集成追踪和日志
""")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("LangGraph Step 7: Persistence（持久化）")
    print("状态管理与部署概述\n")

    # Demo 1: MemorySaver 基本用法
    demo1_memory_saver()

    # Demo 2: 多线程隔离
    demo2_multiple_threads()

    # Demo 3: 状态检查
    demo3_state_inspection()

    # Demo 4: 状态修改
    demo4_state_modification()

    # Demo 5: 部署概述
    demo5_deployment_overview()

    print("=" * 50)
    print("所有 Demo 执行完毕")
    print("=" * 50)
