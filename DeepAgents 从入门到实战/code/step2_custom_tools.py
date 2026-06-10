"""
DeepAgents 教程 - Step 2: 自定义工具与 MCP

本示例演示如何为 Deep Agent 添加自定义工具，
包括使用 @tool 装饰器定义工具、多工具协作、错误处理，
以及 MCP（Model Context Protocol）集成概念。

依赖: deepagents>=0.6.4, langchain-deepseek, langgraph>=1.2.2
"""

import json
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 定义自定义工具
# ============================================================

@tool
def search_web(query: str) -> str:
    """搜索网页，返回搜索结果摘要。

    Args:
        query: 搜索关键词

    Returns:
        搜索结果文本
    """
    # 模拟搜索结果（实际项目中可以调用真实的搜索 API）
    mock_results = {
        "苹果": json.dumps({
            "company": "Apple Inc.",
            "stock_price": 198.50,
            "market_cap": "3.1万亿",
            "currency": "USD",
        }, ensure_ascii=False),
        "特斯拉": json.dumps({
            "company": "Tesla Inc.",
            "stock_price": 245.30,
            "market_cap": "7800亿",
            "currency": "USD",
        }, ensure_ascii=False),
        "Deep Agent": json.dumps({
            "description": "LangChain 的 Deep Agents 是一个开箱即用的 Agent 框架",
            "features": ["子 Agent", "文件系统", "上下文管理", "技能系统"],
        }, ensure_ascii=False),
    }

    # 模糊匹配
    for key, value in mock_results.items():
        if key in query or query in key:
            return value

    return json.dumps({"result": f"搜索 '{query}' 的结果: 找到 3 条相关信息（模拟数据）"}, ensure_ascii=False)


@tool
def calculate(expression: str) -> str:
    """计算数学表达式并返回结果。

    支持加减乘除、括号等基本运算。

    Args:
        expression: 数学表达式，如 "100 * 198.5"

    Returns:
        计算结果文本
    """
    # 安全评估：只允许数字和基本运算符
    allowed_chars = set("0123456789+-*/().% ")
    if not all(c in allowed_chars for c in expression):
        return f"错误: 表达式包含不允许的字符: {expression}"

    try:
        result = eval(expression)  # noqa: S307 上面已经做了字符白名单校验
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


@tool
def get_stock_price(symbol: str) -> str:
    """获取指定股票的实时价格。

    Args:
        symbol: 股票代码，如 AAPL（苹果）、TSLA（特斯拉）

    Returns:
        股票价格信息 JSON 字符串
    """
    # 模拟股票数据
    stock_data = {
        "AAPL": {"name": "苹果公司", "price": 198.50, "change": "+1.2%"},
        "TSLA": {"name": "特斯拉", "price": 245.30, "change": "-0.8%"},
        "GOOGL": {"name": "谷歌", "price": 178.20, "change": "+0.5%"},
        "MSFT": {"name": "微软", "price": 425.60, "change": "+1.5%"},
    }

    symbol = symbol.upper()
    if symbol in stock_data:
        return json.dumps(stock_data[symbol], ensure_ascii=False)
    return json.dumps({"error": f"未找到股票代码: {symbol}，支持的代码: {list(stock_data.keys())}"}, ensure_ascii=False)


def demo1_custom_tools():
    """
    Demo 1: 添加自定义工具
    展示如何将自定义工具传给 create_deep_agent，以及 Agent 如何选择和调用工具
    """
    print("=" * 50)
    print("Demo 1: Agent + 自定义工具")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 创建带有自定义工具的 Agent
    # tools 参数是"追加"模式：自定义工具会和内置工具（文件操作等）合并
    # 不会移除任何内置工具
    agent = create_deep_agent(
        model=llm,
        tools=[search_web, calculate, get_stock_price],
        system_prompt="你是一个财务分析助手，可以搜索信息、查询股价、进行计算。请用中文回复。",
    )

    print("已注册的自定义工具:")
    print("  - search_web: 模拟网页搜索")
    print("  - calculate: 数学表达式计算")
    print("  - get_stock_price: 查询股票价格")
    print()

    # 给一个需要多工具协作的任务
    task = "查询苹果公司(AAPL)的股票价格，然后计算如果买入100股需要多少钱"
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})

    # 分析工具调用链
    print("执行流程分析:")
    step = 0
    for msg in result["messages"]:
        msg_type = type(msg).__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                step += 1
                print(f"  步骤 {step}: Agent 调用 {tc['name']}({tc['args']})")
        elif msg_type == "ToolMessage":
            content = msg.content[:120] if len(msg.content) > 120 else msg.content
            print(f"          -> 返回: {content}")
    print()

    # 最终回复
    last_msg = result["messages"][-1]
    print("Agent 最终回复:")
    print(f"  {last_msg.content}")
    print()


def demo2_error_handling():
    """
    Demo 2: 工具错误处理
    展示当工具返回错误信息时，Agent 如何应对
    """
    print("=" * 50)
    print("Demo 2: 工具错误处理")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    agent = create_deep_agent(
        model=llm,
        tools=[search_web, calculate, get_stock_price],
        system_prompt="你是一个助手，请用中文回复。遇到错误时，向用户解释问题并建议替代方案。",
    )

    # 给一个会触发错误的任务: 查询不存在的股票
    task = "帮我查一下股票代码 UNKNOWN 的价格，然后买入 200 股"
    print(f"用户任务: {task}")
    print("(注意: UNKNOWN 是一个不存在的股票代码)")
    print()

    result = agent.invoke({"messages": task})

    # 展示错误处理过程
    print("错误处理过程:")
    for msg in result["messages"]:
        msg_type = type(msg).__name__
        if msg_type == "ToolMessage":
            content = msg.content[:150] if len(msg.content) > 150 else msg.content
            print(f"  工具返回: {content}")
    print()

    last_msg = result["messages"][-1]
    print("Agent 最终回复:")
    print(f"  {last_msg.content}")
    print()


def demo3_mcp_concept():
    """
    Demo 3: MCP 集成概念
    MCP (Model Context Protocol) 是一种标准化的工具集成协议，
    可以让 Agent 通过统一的接口连接外部工具和数据源。
    """
    print("=" * 50)
    print("Demo 3: MCP（Model Context Protocol）集成概念")
    print("=" * 50)

    print("""
什么是 MCP?

MCP 是 Anthropic 提出的一种开放协议，用于标准化 LLM 与外部工具/
数据源的交互方式。可以把它理解为"AI 工具的 USB 接口"：

- 任何实现了 MCP 协议的服务器，都可以直接接入支持 MCP 的 Agent
- 不需要为每个工具写适配代码，统一用 MCP 协议通信
- 一个 MCP 服务器可以暴露多个工具（如文件系统、数据库、API 等）

在 DeepAgents 中集成 MCP 服务器的方式:
""")

    print("-" * 40)
    print("方式 1: 通过 langchain-mcp-adapter 将 MCP 工具转为 LangChain 工具")
    print("-" * 40)
    print("""
    # 安装 MCP 适配器
    # pip install langchain-mcp-adapter

    from langchain_mcp import MCPToolkit

    # 连接到 MCP 服务器（以文件系统 MCP 为例）
    async with MCPToolkit.from_server(
        command="npx",
        args=["-y", "@anthropic/mcp-filesystem", "/tmp"],
    ) as toolkit:
        # 获取 MCP 服务器提供的所有工具
        mcp_tools = toolkit.get_tools()

        # 直接传给 create_deep_agent
        agent = create_deep_agent(
            model="deepseek:deepseek-chat",
            tools=mcp_tools,  # MCP 工具和自定义工具一样使用
            system_prompt="你是一个助手",
        )

        result = agent.invoke({"messages": "列出 /tmp 目录下的文件"})
""")

    print("-" * 40)
    print("方式 2: 通过 MCP SSE 连接远程 MCP 服务器")
    print("-" * 40)
    print("""
    from langchain_mcp import MCPToolkit

    # 连接到远程 MCP 服务器（SSE 方式）
    async with MCPToolkit.from_url("http://localhost:3000/sse") as toolkit:
        mcp_tools = toolkit.get_tools()

        agent = create_deep_agent(
            model="deepseek:deepseek-chat",
            tools=mcp_tools,
        )
        # 和本地 MCP 工具完全一样的使用方式
""")

    print("-" * 40)
    print("MCP vs 自定义工具对比:")
    print("-" * 40)
    print("""
    自定义工具 (@tool):
      - 适合项目特定的业务逻辑
      - 代码在本地运行，完全可控
      - 需要自己编写和维护

    MCP 工具:
      - 适合通用能力的接入（文件系统、数据库、搜索等）
      - 社区有大量现成的 MCP 服务器可以直接用
      - 标准化协议，切换和组合方便
      - 可以连接远程服务，无需本地部署

    实际项目中，两者通常配合使用:
      MCP 工具 -> 通用能力（文件、数据库、搜索）
      自定义工具 -> 业务特定逻辑（订单处理、用户管理等）
""")


if __name__ == "__main__":
    print("DeepAgents 教程 - Step 2: 自定义工具与 MCP")
    print()

    demo1_custom_tools()
    demo2_error_handling()
    demo3_mcp_concept()

    print("=" * 50)
    print("Step 2 完成!")
    print("=" * 50)
