"""
LangGraph 教程 - Step 3: 条件路由
=================================
演示如何使用 add_conditional_edges 实现条件分支和循环：
- 根据状态动态选择下一个节点
- 路由函数的写法
- 用条件边实现循环
"""

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 1. 定义状态
# ============================================================
# 新增 classification 字段，用于路由决策
class State(TypedDict):
    messages: Annotated[list, add_messages]
    classification: str


# ============================================================
# 2. 初始化 LLM
# ============================================================
llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)


# ============================================================
# 3. 定义路由节点
# ============================================================
def router(state: State) -> dict:
    """路由节点：分析用户输入，判断应该交给哪个专家处理"""
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, "content") else str(last_message)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "你是一个分类器。根据用户的输入，判断它属于哪个类别。\n"
         "只能回复以下三个词之一：\n"
         "- math（数学相关：计算、公式、数学概念）\n"
         "- code（编程相关：代码、技术实现、调试）\n"
         "- chat（日常聊天：其他所有话题）\n"
         "只回复一个词，不要有其他内容。"),
        ("human", "{input}"),
    ])

    chain = prompt | llm
    result = chain.invoke({"input": user_input})
    classification = result.content.strip().lower()

    # 标准化分类结果
    if "math" in classification:
        classification = "math"
    elif "code" in classification:
        classification = "code"
    else:
        classification = "chat"

    return {
        "classification": classification,
        "messages": [AIMessage(content=f"[路由] 分类结果: {classification}")],
    }


# ============================================================
# 4. 定义专家节点
# ============================================================
def math_expert(state: State) -> dict:
    """数学专家节点"""
    user_msgs = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    question = user_msgs[-1].content if user_msgs else "无问题"

    response = llm.invoke([
        SystemMessage(content="你是一位数学专家。请简洁地回答数学问题，可以给出公式和简要推导。"),
        HumanMessage(content=question),
    ])
    return {"messages": [response]}


def code_expert(state: State) -> dict:
    """编程专家节点"""
    user_msgs = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    question = user_msgs[-1].content if user_msgs else "无问题"

    response = llm.invoke([
        SystemMessage(content="你是一位编程专家。请简洁地回答编程问题，必要时给出代码示例。"),
        HumanMessage(content=question),
    ])
    return {"messages": [response]}


def chat_expert(state: State) -> dict:
    """聊天专家节点"""
    user_msgs = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    question = user_msgs[-1].content if user_msgs else "无问题"

    response = llm.invoke([
        SystemMessage(content="你是一位友好的聊天助手。请简洁自然地回复。"),
        HumanMessage(content=question),
    ])
    return {"messages": [response]}


# ============================================================
# 5. 路由函数
# ============================================================
# add_conditional_edges 会调用这个函数，根据返回值决定下一个节点
# 返回值必须是图中已注册的节点名称
def route_by_classification(state: State) -> str:
    """根据分类结果路由到对应的专家节点"""
    classification = state.get("classification", "chat")
    return f"{classification}_expert"


# ============================================================
# 6. 构建条件路由图
# ============================================================
graph = StateGraph(State)

# 添加节点
graph.add_node("router", router)
graph.add_node("math_expert", math_expert)
graph.add_node("code_expert", code_expert)
graph.add_node("chat_expert", chat_expert)

# 添加边
graph.add_edge(START, "router")

# 条件边：根据路由函数的返回值，决定 router 之后走哪个节点
# route_by_classification 返回 "math_expert"/"code_expert"/"chat_expert"
graph.add_conditional_edges("router", route_by_classification)

# 每个专家节点执行完后都到 END
graph.add_edge("math_expert", END)
graph.add_edge("code_expert", END)
graph.add_edge("chat_expert", END)

app = graph.compile()


# ============================================================
# 7. 循环图示例（计数器循环）
# ============================================================
class LoopState(TypedDict):
    count: int
    messages: Annotated[list, add_messages]


def increment(state: LoopState) -> dict:
    """每次执行 count 加 1"""
    count = state["count"] + 1
    return {
        "count": count,
        "messages": [AIMessage(content=f"当前 count = {count}")],
    }


def should_continue(state: LoopState) -> str:
    """循环条件：count < 3 则继续循环，否则结束"""
    if state["count"] < 3:
        return "increment"
    return END


# 构建循环图
loop_graph = StateGraph(LoopState)
loop_graph.add_node("increment", increment)
loop_graph.add_edge(START, "increment")
loop_graph.add_conditional_edges("increment", should_continue, {"increment": "increment", END: END})
loop_app = loop_graph.compile()


# ============================================================
# 8. 演示
# ============================================================
def demo_conditional_routing():
    """Demo 1: 条件路由 - 自动分类并路由"""
    print("=" * 50)
    print("Demo 1: 条件路由")
    print("=" * 50)

    questions = [
        ("数学问题", "请解释一下斐波那契数列的通项公式"),
        ("编程问题", "Python 中如何实现一个简单的 HTTP 服务器"),
        ("日常聊天", "今天天气怎么样"),
    ]

    for label, question in questions:
        print(f"\n--- {label}: {question} ---")
        result = app.invoke({
            "messages": [HumanMessage(content=question)],
            "classification": "",
        })
        classification = result["classification"]
        ai_reply = [m for m in result["messages"] if isinstance(m, AIMessage)][-1]
        content_preview = ai_reply.content[:100] + "..." if len(ai_reply.content) > 100 else ai_reply.content
        print(f"  分类: {classification}")
        print(f"  回复: {content_preview}")
    print()


def demo_loop():
    """Demo 2: 简单循环 - 计数器递增到 3"""
    print("=" * 50)
    print("Demo 2: 条件循环（计数器）")
    print("=" * 50)

    result = loop_app.invoke({"count": 0, "messages": []})

    print(f"最终 count: {result['count']}")
    print(f"执行过程:")
    for msg in result["messages"]:
        print(f"  {msg.content}")
    print()


def demo_graph_structure():
    """Demo 3: 查看条件路由图结构"""
    print("=" * 50)
    print("Demo 3: 图结构")
    print("=" * 50)

    print("条件路由图 - Mermaid:")
    print(app.get_graph().draw_mermaid())

    print("\n循环图 - Mermaid:")
    print(loop_app.get_graph().draw_mermaid())
    print()


if __name__ == "__main__":
    demo_conditional_routing()
    demo_loop()
    demo_graph_structure()
