"""
LangGraph 教程 - Step 6: Multi-Agent（多智能体）

演示 Supervisor 模式：
1. Supervisor 节点决定任务分配
2. Researcher 子图负责信息搜索
3. Writer 子图负责内容撰写
4. Supervisor 循环调度直到任务完成
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_deepseek import ChatDeepSeek
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 定义共享状态
# ============================================================

class AgentState(TypedDict):
    """多智能体共享状态"""
    messages: Annotated[list[BaseMessage], add_messages]  # 消息历史
    next_agent: str  # 下一个要调用的 agent: "researcher" / "writer" / "FINISH"


# ============================================================
# 创建 LLM 实例
# ============================================================

llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    api_base=DEEPSEEK_BASE_URL,
)


# ============================================================
# 定义工具
# ============================================================

@tool
def search_web(query: str) -> str:
    """搜索互联网获取信息（模拟）"""
    # 模拟搜索结果
    mock_results = {
        "Python GIL": (
            "Python GIL（Global Interpreter Lock，全局解释器锁）是 CPython 中的互斥锁，"
            "确保同一时刻只有一个线程执行 Python 字节码。\n"
            "关键要点:\n"
            "- GIL 使得 CPU 密集型任务无法真正并行\n"
            "- I/O 密集型任务不受 GIL 影响\n"
            "- Python 3.13 引入了实验性的 free-threaded 模式，可禁用 GIL\n"
            "- 多进程（multiprocessing）是绕过 GIL 的常用方案\n"
            "- C 扩展可以在执行计算时释放 GIL"
        ),
        "default": "搜索结果: 未找到相关信息，请尝试其他关键词。",
    }
    for key, value in mock_results.items():
        if key.lower() in query.lower():
            return value
    return mock_results["default"]


# ============================================================
# Researcher Agent（研究智能体）
# ============================================================

def researcher_node(state: AgentState) -> dict:
    """研究智能体：根据任务搜索信息"""
    messages = state["messages"]

    # 构造研究指令
    system_msg = SystemMessage(content=(
        "你是一个研究助手。根据用户的任务，使用 search_web 工具搜索相关信息，"
        "然后整理成结构化的研究结果返回。"
        "只返回研究结果，不要添加多余的解释。"
    ))

    # 调用带工具的 LLM
    researcher_llm = llm.bind_tools([search_web])
    response = researcher_llm.invoke([system_msg] + messages)

    # 手动执行工具调用（简化版，避免嵌套子图的复杂性）
    tool_calls = getattr(response, "tool_calls", None)
    research_results = []

    if tool_calls:
        for tc in tool_calls:
            if tc["name"] == "search_web":
                result = search_web.invoke(tc["args"])
                research_results.append(f"[搜索查询: {tc['args']['query']}]\n{result}")

    # 如果有工具调用结果，再让 LLM 总结
    if research_results:
        combined = "\n\n".join(research_results)
        summary_response = llm.invoke([
            SystemMessage(content="将以下搜索结果整理成简洁的研究报告。"),
            HumanMessage(content=combined),
        ])
        return {
            "messages": [HumanMessage(content=f"研究结果:\n{summary_response.content}", name="researcher")],
            "next_agent": "supervisor",
        }

    # 没有工具调用，直接返回 LLM 响应
    return {
        "messages": [HumanMessage(content=f"研究结果:\n{response.content}", name="researcher")],
        "next_agent": "supervisor",
    }


# ============================================================
# Writer Agent（写作智能体）
# ============================================================

def writer_node(state: AgentState) -> dict:
    """写作智能体：根据研究结果撰写内容"""
    messages = state["messages"]

    system_msg = SystemMessage(content=(
        "你是一个技术写作助手。根据提供的研究结果，撰写一篇结构清晰、内容准确的技术总结。"
        "要求:\n"
        "- 使用中文撰写\n"
        "- 包含标题和分段\n"
        "- 语言简洁专业\n"
        "- 只返回撰写的内容，不要添加多余说明"
    ))

    response = llm.invoke([system_msg] + messages)

    return {
        "messages": [HumanMessage(content=f"撰写内容:\n{response.content}", name="writer")],
        "next_agent": "supervisor",
    }


# ============================================================
# Supervisor Node（监督智能体）
# ============================================================

def supervisor_node(state: AgentState) -> dict:
    """监督智能体：决定下一步调用哪个 agent"""
    messages = state["messages"]

    system_msg = SystemMessage(content=(
        "你是一个任务调度器。根据对话历史，决定下一步应该调用哪个智能体。\n"
        "可选的智能体:\n"
        "- researcher: 需要搜索和收集信息时调用\n"
        "- writer: 已经有足够的研究结果，需要撰写内容时调用\n"
        "- FINISH: 任务已完成，不需要继续\n\n"
        "判断规则:\n"
        "1. 如果还没有搜索过信息，分配给 researcher\n"
        "2. 如果已有研究结果但还没有撰写内容，分配给 writer\n"
        "3. 如果已经有撰写好的内容，返回 FINISH\n\n"
        "只返回以下三个值之一: researcher, writer, FINISH\n"
        "不要返回任何其他内容。"
    ))

    response = llm.invoke([system_msg] + messages)
    decision = response.content.strip().upper()

    # 标准化输出
    if "RESEARCHER" in decision:
        next_agent = "researcher"
    elif "WRITER" in decision:
        next_agent = "writer"
    elif "FINISH" in decision:
        next_agent = "FINISH"
    else:
        # 默认兜底
        next_agent = "FINISH"

    print(f"  [Supervisor] 决策: next_agent = {next_agent}")

    return {"next_agent": next_agent}


# ============================================================
# 路由函数：根据 supervisor 决策选择下一个节点
# ============================================================

def route_agent(state: AgentState) -> str:
    """根据 next_agent 字段路由到对应节点"""
    next_agent = state.get("next_agent", "FINISH")
    if next_agent == "researcher":
        return "researcher"
    elif next_agent == "writer":
        return "writer"
    else:
        return END


# ============================================================
# 构建多智能体图
# ============================================================

def build_multi_agent_graph():
    """构建 Supervisor 模式的多智能体图"""
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)

    # 设置入口
    graph.add_edge(START, "supervisor")

    # supervisor 根据决策路由到不同 agent
    graph.add_conditional_edges("supervisor", route_agent)

    # agent 执行完毕后回到 supervisor 继续调度
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("writer", "supervisor")

    return graph.compile()


# ============================================================
# Demo: 多智能体协作
# ============================================================

def demo_multi_agent():
    """演示 Supervisor 模式的多智能体协作"""
    print("=" * 50)
    print("Demo: Multi-Agent Supervisor 模式")
    print("=" * 50)

    app = build_multi_agent_graph()

    # 打印图结构
    print("\n--- 图结构 ---")
    print("START -> supervisor -> (researcher | writer | END)")
    print("researcher -> supervisor (循环)")
    print("writer -> supervisor (循环)")

    # 执行任务
    task = "研究 Python GIL 机制，并写一篇技术总结"
    print(f"\n--- 用户任务: {task} ---")

    result = app.invoke({
        "messages": [HumanMessage(content=task)],
        "next_agent": "",
    })

    # 展示执行过程
    print(f"\n--- 执行结果（共 {len(result['messages'])} 条消息）---")
    for i, msg in enumerate(result["messages"]):
        name = getattr(msg, "name", "user") or "user"
        role = type(msg).__name__
        content = msg.content
        print(f"\n  [{i}] {role} (name={name}):")
        # 缩进输出
        for line in content.split("\n"):
            print(f"      {line}")

    print(f"\n--- 最终决策: {result.get('next_agent', 'unknown')} ---")


# ============================================================
# Demo 2: 简单任务直接完成
# ============================================================

def demo_simple_task():
    """演示简单任务：不需要多个 agent"""
    print("\n" + "=" * 50)
    print("Demo 2: 简单任务（supervisor 直接完成）")
    print("=" * 50)

    app = build_multi_agent_graph()

    # 一个已经包含足够信息的任务
    task = "请根据以下信息直接写总结: Python 的 GIL 是全局解释器锁，影响多线程并行。"
    print(f"\n--- 用户任务: {task} ---")

    result = app.invoke({
        "messages": [HumanMessage(content=task)],
        "next_agent": "",
    })

    print(f"\n--- 执行结果 ---")
    for i, msg in enumerate(result["messages"]):
        name = getattr(msg, "name", "user") or "user"
        role = type(msg).__name__
        content = msg.content[:200] if len(msg.content) > 200 else msg.content
        print(f"  [{i}] {role} (name={name}): {content}")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("LangGraph Step 6: Multi-Agent（多智能体）")
    print("Supervisor 模式演示\n")

    # Demo 1: 完整的研究 + 写作任务
    demo_multi_agent()

    # Demo 2: 简单任务
    demo_simple_task()

    print("\n" + "=" * 50)
    print("所有 Demo 执行完毕")
    print("=" * 50)
