"""
LangGraph 教程 - Step 1: StateGraph 基础
=========================================
演示如何用 StateGraph 构建第一个图：
- 定义状态（State）
- 定义节点函数
- 添加边（Edge）
- 编译和执行图
"""

from typing import Annotated
from typing_extensions import TypedDict

from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 1. 定义状态
# ============================================================
# State 是一个 TypedDict，描述图在节点之间传递的数据结构
# messages 字段使用 add_messages reducer：新消息追加到列表，而不是覆盖
class State(TypedDict):
    messages: Annotated[list, add_messages]


# ============================================================
# 2. 初始化 LLM
# ============================================================
llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)


# ============================================================
# 3. 定义节点函数
# ============================================================
# 每个节点函数接收当前 state，返回需要更新的字段
# 这里 chatbot 节点把 LLM 的回复追加到 messages 列表
def chatbot(state: State) -> dict:
    """聊天机器人节点：调用 LLM 并返回回复"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


# ============================================================
# 4. 构建图
# ============================================================
# StateGraph(State) 创建一个图，状态的类型由 State 定义
# add_node 添加节点，add_edge 添加边
# START 和 END 是特殊节点，分别代表图的入口和出口
graph = StateGraph(State)
graph.add_node("chatbot", chatbot)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

# ============================================================
# 5. 编译图
# ============================================================
# compile() 将图编译为可执行的对象
app = graph.compile()


# ============================================================
# 6. 演示
# ============================================================
def demo_simple_invoke():
    """Demo 1: 单轮对话"""
    print("=" * 50)
    print("Demo 1: 单轮对话")
    print("=" * 50)

    result = app.invoke({"messages": [("user", "你好，请用一句话介绍你自己")]})

    # result 是最终的 state，包含完整的消息列表
    print(f"消息数量: {len(result['messages'])}")
    print(f"用户消息: {result['messages'][0].content}")
    print(f"AI 回复: {result['messages'][1].content}")
    print()


def demo_multi_turn():
    """Demo 2: 多轮对话（手动传入历史）"""
    print("=" * 50)
    print("Demo 2: 多轮对话")
    print("=" * 50)

    # 第一次调用
    result1 = app.invoke({"messages": [("user", "我叫小明")]})
    print(f"第 1 轮 - AI 回复: {result1['messages'][1].content}")

    # 第二次调用，手动携带历史消息
    # LangGraph 本身不持久化状态，需要自己管理消息历史
    messages = result1["messages"]
    messages.append(("user", "我叫什么名字？"))
    result2 = app.invoke({"messages": messages})

    print(f"第 2 轮 - AI 回复: {result2['messages'][-1].content}")
    print()


def demo_graph_structure():
    """Demo 3: 查看图结构"""
    print("=" * 50)
    print("Demo 3: 图结构")
    print("=" * 50)

    # 获取图的 Mermaid 格式描述
    mermaid = app.get_graph().draw_mermaid()
    print("Mermaid 图描述:")
    print(mermaid)

    # 也可以直接查看节点和边的信息
    graph_data = app.get_graph()
    print("节点列表:")
    for node in graph_data.nodes:
        print(f"  - {node}")
    print("边列表:")
    for edge in graph_data.edges:
        print(f"  - {edge}")
    print()


if __name__ == "__main__":
    demo_simple_invoke()
    demo_multi_turn()
    demo_graph_structure()
