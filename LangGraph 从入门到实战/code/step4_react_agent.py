"""
LangGraph 教程 - Step 4: ReAct Agent
=====================================
演示两种构建 ReAct Agent 的方式：
1. 快捷方式：create_react_agent（适合简单场景）
2. 手动构建：用 StateGraph + ToolNode + 条件边（适合需要定制）
"""

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, create_react_agent

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 1. 定义工具
# ============================================================
# 使用 @tool 装饰器将普通函数转换为 LangChain 工具
# LLM 会根据函数名和 docstring 来决定何时调用哪个工具

@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气信息"""
    # 模拟天气数据（实际项目中会调用真实 API）
    weather_data = {
        "北京": "晴天，气温 28 度，空气质量良好",
        "上海": "多云，气温 26 度，有轻微雾霾",
        "深圳": "雷阵雨，气温 32 度，湿度较高",
    }
    return weather_data.get(city, f"{city}的天气数据暂不可用")


@tool
def get_time(timezone: str = "Asia/Shanghai") -> str:
    """查询当前时间"""
    from datetime import datetime
    now = datetime.now()
    return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (时区: {timezone})"


@tool
def calculate(expression: str) -> str:
    """计算数学表达式的结果。输入必须是一个合法的 Python 数学表达式，例如 '2 + 3 * 4'"""
    try:
        # 只允许数学运算，禁止执行任意代码
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "错误: 表达式包含不允许的字符"
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


# 工具列表
tools = [get_weather, get_time, calculate]


# ============================================================
# 2. 初始化 LLM
# ============================================================
llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)


# ============================================================
# 3. 快捷方式：create_react_agent
# ============================================================
# create_react_agent 是 LangGraph 提供的预构建 Agent
# 传入 model 和 tools 即可，内部自动处理 ReAct 循环
quick_agent = create_react_agent(llm, tools)


# ============================================================
# 4. 手动构建 ReAct 图
# ============================================================
# 手动构建能更精细地控制 Agent 的行为
# 核心模式: agent -> (判断是否需要调用工具) -> tools -> agent（循环）
#                                                       -> END（结束）

# 定义状态
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# 将 LLM 绑定工具
llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState) -> dict:
    """Agent 节点：调用绑定了工具的 LLM"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """判断是否需要继续调用工具"""
    last_message = state["messages"][-1]
    # 如果 LLM 的回复中包含 tool_calls，说明需要调用工具
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# 构建手动 ReAct 图
manual_graph = StateGraph(AgentState)
manual_graph.add_node("agent", agent_node)

# ToolNode 是预构建的工具执行节点，自动根据 tool_calls 调用对应工具
tool_node = ToolNode(tools)
manual_graph.add_node("tools", tool_node)

# 边的连接
manual_graph.add_edge(START, "agent")
manual_graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
manual_graph.add_edge("tools", "agent")  # 工具执行完回到 agent 继续推理

manual_app = manual_graph.compile()


# ============================================================
# 5. 演示
# ============================================================
def demo_quick_agent():
    """Demo 1: 快捷方式 - create_react_agent"""
    print("=" * 50)
    print("Demo 1: create_react_agent（快捷方式）")
    print("=" * 50)

    question = "北京今天天气怎么样？顺便帮我算一下 (15 + 27) * 3 等于多少"
    print(f"用户: {question}\n")

    result = quick_agent.invoke({"messages": [HumanMessage(content=question)]})

    print("执行过程:")
    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__
        if msg_type == "HumanMessage":
            print(f"  [{i}] 用户: {msg.content}")
        elif msg_type == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_names = [tc["name"] for tc in msg.tool_calls]
                print(f"  [{i}] AI 调用工具: {tool_names}")
            else:
                content_preview = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                print(f"  [{i}] AI 回复: {content_preview}")
        elif msg_type == "ToolMessage":
            content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
            print(f"  [{i}] 工具结果: {content_preview}")
    print()


def demo_manual_agent():
    """Demo 2: 手动构建 ReAct 图"""
    print("=" * 50)
    print("Demo 2: 手动构建 ReAct 图")
    print("=" * 50)

    question = "深圳的天气如何？现在几点了？"
    print(f"用户: {question}\n")

    result = manual_app.invoke({"messages": [HumanMessage(content=question)]})

    print("执行过程:")
    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__
        if msg_type == "HumanMessage":
            print(f"  [{i}] 用户: {msg.content}")
        elif msg_type == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_names = [tc["name"] for tc in msg.tool_calls]
                print(f"  [{i}] AI 调用工具: {tool_names}")
            else:
                content_preview = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                print(f"  [{i}] AI 回复: {content_preview}")
        elif msg_type == "ToolMessage":
            content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
            print(f"  [{i}] 工具结果: {content_preview}")
    print()


def demo_stream():
    """Demo 3: 流式输出 Agent 的执行过程"""
    print("=" * 50)
    print("Demo 3: 流式输出")
    print("=" * 50)

    question = "帮我算一下 1024 * 768"
    print(f"用户: {question}\n")

    # 使用 stream 逐步输出
    print("逐步执行:")
    for event in manual_app.stream({"messages": [HumanMessage(content=question)]}):
        # event 是一个字典，key 是节点名，value 是该节点的输出
        for node_name, node_output in event.items():
            if "messages" in node_output:
                last_msg = node_output["messages"][-1]
                msg_type = type(last_msg).__name__
                if msg_type == "AIMessage":
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        print(f"  [{node_name}] AI 决定调用工具: {last_msg.tool_calls[0]['name']}")
                    else:
                        print(f"  [{node_name}] AI: {last_msg.content}")
                elif msg_type == "ToolMessage":
                    print(f"  [{node_name}] 工具返回: {last_msg.content}")
    print()


def demo_comparison():
    """Demo 4: 两种方式的对比"""
    print("=" * 50)
    print("Demo 4: 快捷方式 vs 手动构建")
    print("=" * 50)

    print("快捷方式 (create_react_agent):")
    print("  - 优点: 一行代码创建 Agent，开箱即用")
    print("  - 缺点: 自定义能力有限")
    print("  - 适用: 快速原型、标准 ReAct 场景")
    print()
    print("手动构建 (StateGraph + ToolNode):")
    print("  - 优点: 完全控制图的拓扑、节点逻辑、条件分支")
    print("  - 缺点: 需要手写更多代码")
    print("  - 适用: 需要自定义工具调用逻辑、多 Agent 协作、复杂控制流")
    print()

    # 查看两种图的结构
    print("快捷方式图结构:")
    print(quick_agent.get_graph().draw_mermaid())

    print("\n手动构建图结构:")
    print(manual_app.get_graph().draw_mermaid())
    print()


if __name__ == "__main__":
    demo_quick_agent()
    demo_manual_agent()
    demo_stream()
    demo_comparison()
