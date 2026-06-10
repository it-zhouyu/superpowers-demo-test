"""
LangGraph 教程 - Step 2: 状态管理
=================================
演示如何在 StateGraph 中使用复杂状态：
- 多字段的 TypedDict 状态
- reducer 函数（add_messages、operator.add）
- 状态在节点之间的传递和累积
"""

import operator
from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage, AIMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 1. 定义复杂状态
# ============================================================
# State 可以包含多个字段，每个字段可以有不同的 reducer
# - messages: 使用 add_messages reducer，新消息追加到列表
# - context: 普通字段，新值覆盖旧值
# - step_count: 使用 operator.add reducer，新值与旧值相加（累加器）
class State(TypedDict):
    messages: Annotated[list, add_messages]
    context: str
    step_count: Annotated[int, operator.add]


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
def analyzer(state: State) -> dict:
    """分析节点：分析用户输入，提取上下文信息"""
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, "content") else str(last_message)

    # 使用 LLM 分析用户意图，生成上下文摘要
    analysis_prompt = f"请用一句话概括以下用户输入的主题：\n\n{user_input}"
    analysis = llm.invoke([HumanMessage(content=analysis_prompt)])

    # 返回需要更新的字段
    # context 是普通字段，新值覆盖旧值
    # step_count 使用 operator.add reducer，返回 1 表示累加 1
    return {
        "context": f"主题: {analysis.content}",
        "messages": [AIMessage(content=f"[分析结果] 用户在讨论: {analysis.content}")],
        "step_count": 1,
    }


def responder(state: State) -> dict:
    """回复节点：根据上下文和消息历史生成回复"""
    # 构造包含上下文的提示
    context_info = state.get("context", "无上下文")
    messages = state["messages"]

    # 把上下文信息注入到系统消息中
    system_msg = HumanMessage(
        content=f"当前对话上下文: {context_info}\n\n"
        f"请基于以上上下文，简短回复用户。"
    )

    # 使用最后一条用户消息作为主要输入
    user_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    last_user_msg = user_msgs[-1] if user_msgs else messages[0]

    response = llm.invoke([system_msg, last_user_msg])

    return {
        "messages": [response],
        "step_count": 1,
    }


def counter(state: State) -> dict:
    """计数节点：记录处理步骤"""
    current_count = state.get("step_count", 0)
    print(f"  [计数器] 当前已执行 {current_count} 个步骤")

    # 只累加 1，不需要返回其他字段
    return {"step_count": 1}


# ============================================================
# 4. 构建图
# ============================================================
# 线性流程: START -> analyzer -> responder -> counter -> END
graph = StateGraph(State)
graph.add_node("analyzer", analyzer)
graph.add_node("responder", responder)
graph.add_node("counter", counter)

graph.add_edge(START, "analyzer")
graph.add_edge("analyzer", "responder")
graph.add_edge("responder", "counter")
graph.add_edge("counter", END)

app = graph.compile()


# ============================================================
# 5. 演示
# ============================================================
def demo_single_invoke():
    """Demo 1: 单次调用，观察状态在各节点间的传递"""
    print("=" * 50)
    print("Demo 1: 单次调用 - 状态在节点间传递")
    print("=" * 50)

    initial_state = {
        "messages": [HumanMessage(content="Python 的列表推导式怎么用？")],
        "context": "",
        "step_count": 0,
    }

    result = app.invoke(initial_state)

    print(f"\n最终状态:")
    print(f"  step_count: {result['step_count']} (经过了 {result['step_count']} 个节点)")
    print(f"  context: {result['context']}")
    print(f"  消息数量: {len(result['messages'])}")

    print(f"\n消息列表:")
    for i, msg in enumerate(result["messages"]):
        role = type(msg).__name__
        content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        print(f"  [{i}] {role}: {content_preview}")
    print()


def demo_accumulated_state():
    """Demo 2: 连续调用，复用消息历史"""
    print("=" * 50)
    print("Demo 2: 连续调用 - 复用消息历史")
    print("=" * 50)

    # 第一次调用
    print("--- 第一次调用 ---")
    result1 = app.invoke({
        "messages": [HumanMessage(content="什么是递归？")],
        "context": "",
        "step_count": 0,
    })
    print(f"  消息数量: {len(result1['messages'])}")

    # 第二次调用，把第一次的对话历史带上，再追加新的用户消息
    print("\n--- 第二次调用（携带历史） ---")
    result2 = app.invoke({
        "messages": result1["messages"] + [HumanMessage(content="能举个例子吗？")],
        "context": "",
        "step_count": 0,
    })
    print(f"  消息数量: {len(result2['messages'])}")

    print(f"\n第二次调用的完整消息历史:")
    for i, msg in enumerate(result2["messages"]):
        role = type(msg).__name__
        content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        print(f"  [{i}] {role}: {content_preview}")
    print()


def demo_state_schema():
    """Demo 3: 查看状态的结构定义"""
    print("=" * 50)
    print("Demo 3: 状态结构（State Schema）")
    print("=" * 50)

    # 查看图的 channels（即状态的各个字段及其 reducer）
    print("状态字段:")
    print(f"  messages: list, reducer=add_messages (追加消息)")
    print(f"  context:  str, 无 reducer (直接覆盖)")
    print(f"  step_count: int, reducer=operator.add (累加)")

    # 也可以从编译后的图获取节点信息
    graph_data = app.get_graph()
    print(f"\n执行路径:")
    for edge in graph_data.edges:
        print(f"  {edge.source} -> {edge.target}")
    print()


if __name__ == "__main__":
    demo_single_invoke()
    demo_accumulated_state()
    demo_state_schema()
