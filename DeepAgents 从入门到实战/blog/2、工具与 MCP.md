> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 为什么需要自定义工具

前面我们跑了第一个 Deep Agent，它默认自带文件操作、任务管理这些工具。但实际项目中，你需要的是业务相关的工具——搜索网页、查数据库、调用第三方 API。

DeepAgents 的自定义工具机制和 LangChain 一样，都是用 `@tool` 装饰器。自定义工具会被追加到内置工具列表中，不会替换任何内置工具。也就是说，添加自定义工具后，Agent 既有文件操作能力，又有你新加的业务能力。

## 用 @tool 定义自定义工具

先看一个完整的例子。我们定义三个工具：网页搜索、数学计算、股票查询。

```python
import json
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

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
    }

    for key, value in mock_results.items():
        if key in query or query in key:
            return value

    return json.dumps({"result": f"搜索 '{query}' 的结果: 找到 3 条相关信息（模拟数据）"}, ensure_ascii=False)

@tool
def calculate(expression: str) -> str:
    """计算数学表达式并返回结果。支持加减乘除、括号等基本运算。

    Args:
        expression: 数学表达式，如 "100 * 198.5"

    Returns:
        计算结果文本
    """
    allowed_chars = set("0123456789+-*/().% ")
    if not all(c in allowed_chars for c in expression):
        return f"错误: 表达式包含不允许的字符: {expression}"

    try:
        result = eval(expression)
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
```

每个工具的定义遵循相同的模式：

1. 用 `@tool` 装饰器标记函数
2. 写函数签名，参数加上类型注解（`query: str`、`symbol: str`）
3. 在 docstring 中描述工具功能和参数含义
4. 函数体实现具体逻辑，返回字符串

这里有两个关键点：

**docstring 决定了 LLM 能否正确使用工具。** LLM 看到的工具描述，就是从 docstring 里提取的。第一行是工具的简要说明，`Args` 部分是参数说明。如果 docstring 写得不清楚，LLM 就不知道什么时候该调这个工具、该怎么传参。

**类型注解决定了参数的 Schema。** `symbol: str` 告诉 LLM 这个参数是字符串类型。如果你写 `count: int`，LLM 就知道该传整数。LangChain 会自动把类型注解转换成 JSON Schema，作为工具定义的一部分发给 LLM。

定义好工具后，传给 `create_deep_agent`：

```python
llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

agent = create_deep_agent(
    model=llm,
    tools=[search_web, calculate, get_stock_price],
    system_prompt="你是一个财务分析助手，可以搜索信息、查询股价、进行计算。请用中文回复。",
)
```

`tools` 参数接受一个工具列表。注意：这些工具是**追加**到内置工具上的。传了 `tools=[search_web, calculate, get_stock_price]` 之后，Agent 同时拥有 `search_web`、`calculate`、`get_stock_price` 这三个自定义工具，以及 `write_todos`、`read_file` 等所有内置工具。

## 多工具协作

给 Agent 一个需要跨工具协作的任务：

```python
task = "查询苹果公司(AAPL)的股票价格，然后计算如果买入100股需要多少钱"

result = agent.invoke({"messages": task})
```

Agent 的执行过程：

```
执行流程分析:
  步骤 1: Agent 调用 get_stock_price({'symbol': 'AAPL'})
          -> 返回: {"name": "苹果公司", "price": 198.5, "change": "+1.2%"}

Agent 最终回复:
  ## 苹果公司 (AAPL) 股票信息
  - **当前股价**：**$198.50**
  - **今日变动**：+1.2%

  买入100股所需资金: 100 × $198.50/股 = $19,850
```

Agent 自动完成了"查价格 -> 提取数字 -> 计算总价"这个工具链。你不需要告诉它"先调 get_stock_price 再调 calculate"，LLM 根据工具描述和用户意图自动编排调用顺序。

这就是工具协作的核心价值：你只管定义工具，LLM 负责决定什么时候调哪个工具、传什么参数。

### 工具参数字段说明

当你用 `@tool` 定义一个工具后，LangChain 会自动提取以下信息：

| 字段 | 来源 | 说明 |
|------|------|------|
| name | 函数名 | 工具名称，直接用函数名（如 `search_web`） |
| description | docstring 第一段 | 工具描述，LLM 根据这段话判断什么时候用这个工具 |
| args_schema | 类型注解 + docstring Args | 参数的 JSON Schema，包含参数名、类型、描述 |

你不需要手动定义这些字段，`@tool` 装饰器会自动处理。但你需要确保 docstring 写得清晰，因为 description 是 LLM 唯一能看到的工具说明。

## 工具错误处理

工具不会总是返回成功结果。当用户传入无效参数、API 调用失败、或者网络超时时，工具需要返回错误信息，让 LLM 自己决定怎么处理。

来看一个实际的例子。用户查询一个不存在的股票代码：

```python
agent = create_deep_agent(
    model=llm,
    tools=[search_web, calculate, get_stock_price],
    system_prompt="你是一个助手，请用中文回复。遇到错误时，向用户解释问题并建议替代方案。",
)

task = "帮我查一下股票代码 UNKNOWN 的价格，然后买入 200 股"
result = agent.invoke({"messages": task})
```

执行过程：

```
错误处理过程:
  工具返回: {"error": "未找到股票代码: UNKNOWN，支持的代码: ['AAPL', 'TSLA', 'GOOGL', 'MSFT']"}

Agent 最终回复:
  **问题 1：股票代码 `UNKNOWN` 无效**
  当前系统只支持以下股票代码：
  - `AAPL`（苹果）
  - `TSLA`（特斯拉）
  - `GOOGL`（谷歌）
  - `MSFT`（微软）

  **问题 2：买入 200 股**
  我没有执行交易操作（买入/卖出股票）的能力。只能提供股价查询服务。
```

注意这里发生了什么：

1. 工具返回了一个包含 `error` 字段的 JSON 字符串
2. LLM 拿到这个错误信息后，没有直接把它抛给用户
3. LLM 根据错误信息中"支持的代码"列表，主动给用户提供了可选项

这就是 Agent 比普通 API 调用强大的地方——工具只负责返回结果（包括错误），LLM 负责理解和处理。你不需要在工具里写"如果出错怎么办"的分支逻辑，LLM 会根据上下文自己判断。

在实际项目中，工具的错误处理遵循一个简单原则：**工具返回错误信息字符串，不做错误恢复。让 LLM 来决定怎么向用户解释、是否重试、或者提供替代方案。**

## MCP 集成

前面的自定义工具都是 Python 函数，绑在当前项目里。如果你想在 Agent 里使用社区已有的工具服务（文件系统、数据库、搜索等），或者让同一套工具服务对接不同的 Agent 框架，就需要 MCP（Model Context Protocol，模型上下文协议）。

前面讲过 MCP 的基本概念，这里直接看在 DeepAgents 中怎么用。

安装依赖：

```bash
pip install langchain-mcp-adapters
```

连接 MCP Server 并获取工具：

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    client = MultiServerMCPClient(
        {
            "filesystem": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "@anthropic/mcp-filesystem", "/tmp"],
            }
        }
    )

    # 获取 MCP Server 暴露的所有工具，自动转换成 LangChain Tool
    mcp_tools = await client.get_tools()

    # 和 @tool 定义的工具一样，直接传给 create_deep_agent
    agent = create_deep_agent(
        model=llm,
        tools=mcp_tools,
        system_prompt="你是一个文件管理助手",
    )

    result = await agent.ainvoke({"messages": "列出 /tmp 目录下的文件"})

if __name__ == "__main__":
    asyncio.run(main())
```

MCP 工具和 `@tool` 自定义工具可以混合使用——MCP 负责通用能力（文件系统、数据库、搜索），`@tool` 负责业务特定逻辑：

```python
mcp_tools = await client.get_tools()
business_tools = [process_order, query_user]

agent = create_deep_agent(
    model=llm,
    tools=mcp_tools + business_tools,
    system_prompt="你是一个客服助手",
)
```

Agent 不会区分工具来源。对 LLM 来说，所有工具都只是一个"名称 + 描述 + 参数 Schema"。

## 小结

- 用 `@tool` 装饰器定义自定义工具，docstring 和类型注解是 LLM 理解工具的关键
- 自定义工具追加到内置工具上，不会替换内置工具
- Agent 自动编排多工具调用链，你不需要手动指定调用顺序
- 工具返回错误字符串，LLM 负责理解错误并决定如何处理
- 通过 `langchain-mcp-adapters` 可以接入任何 MCP Server 的工具，和自定义工具混合使用

## 完整代码

把下面代码保存为 `step2_custom_tools.py`，并和前面的 `config.py` 放在同一个目录下运行：

```python
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
数据源的交互方式。它的作用是让工具服务通过统一协议接入 Agent：

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
```
