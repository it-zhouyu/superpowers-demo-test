> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 为什么需要 MCP

前面我们学过用 `@tool` 定义工具，前面又学了用 `create_agent` 把工具和模型组合成自动循环的 Agent。但你有没有想过一个问题：

你写的每个工具，都是"绑死"在当前项目里的 Python 函数。如果你想换个 Agent 框架（比如从 LangChain 换到 OpenAI Agents SDK），这些工具就得重写一遍。反过来，社区已经有很多现成的工具服务——文件系统、数据库查询、网页搜索——你想在 LangChain Agent 里用它们，也得针对 LangChain 的 `@tool` 接口重新包一层。

MCP（Model Context Protocol，模型上下文协议）就是来解决这个问题的。它是 Anthropic 在 2024 年底提出的开放协议，用于标准化 LLM 和外部工具/数据源之间的交互方式。任何实现了 MCP 的工具服务（MCP Server），都可以通过统一协议接入支持 MCP 的 Agent 框架。

## MCP 的架构

MCP 的核心是 Client-Server 架构：

- **MCP Server**（工具提供方）：一个独立进程或远程服务，通过 MCP 协议暴露工具（Tools）、数据资源（Resources）、提示模板（Prompts）
- **MCP Client**（工具使用方）：Agent 框架（如 LangChain）中的客户端组件，负责连接 MCP Server，获取工具列表，调用工具

两者通过**传输层（Transport）**通信。MCP 目前支持两种传输方式：

| 传输方式 | 通信机制 | 适用场景 |
|---------|---------|---------|
| stdio | 标准输入输出 | MCP Server 作为本地子进程运行，适合本地开发和小型工具 |
| HTTP（Streamable HTTP） | HTTP 请求 + SSE（Server-Sent Events） | MCP Server 部署在远程，适合生产环境和企业级服务 |

SSE（Server-Sent Events，服务器推送事件）是一种基于 HTTP 的单向推送机制，服务器可以持续向客户端发送消息流，适合长时间运行的工具调用场景。

不管用哪种传输方式，Client 和 Server 之间的通信内容都是统一的 JSON-RPC 消息。这意味着：

- 你可以用本地 stdio 方式开发和调试 MCP Server
- 上线时切换到 HTTP 部署，Agent 代码只需要改连接配置，不需要改任何业务逻辑

## MCP Server 提供了什么

一个 MCP Server 可以暴露三类能力：

| 能力 | 说明 | 举例 |
|------|------|------|
| Tools（工具） | 可调用的函数，LLM 决定什么时候调用 | 数据库查询、文件操作、网页搜索 |
| Resources（资源） | 可读取的数据，类似文件系统 | 配置文件、数据库记录、API 响应 |
| Prompts（提示模板） | 可复用的提示词模板 | 代码审查模板、总结模板 |

其中 Tools 是最核心的能力，也是我们最常用的。每个 Tool 的描述信息包括：工具名称、功能描述、参数的 JSON Schema。这些信息和 `@tool` 装饰器从 docstring 和类型注解中提取的信息是一样的——只是格式统一成了 MCP 协议标准。

## 用 FastMCP 写一个 MCP Server

Python 官方 MCP SDK 提供了 `FastMCP`，写一个 MCP Server 非常简单。

先安装依赖：

```bash
pip install mcp langchain-mcp-adapters
```

创建 `math_server.py`：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

这段代码做了什么：

1. `FastMCP("Math")` 创建了一个名为 "Math" 的 MCP Server
2. `@mcp.tool()` 把函数注册为 MCP 工具，用法和 LangChain 的 `@tool` 几乎一样——函数名就是工具名，docstring 就是工具描述，类型注解定义参数 Schema
3. `mcp.run(transport="stdio")` 以 stdio 模式启动 Server，等待 Client 连接

注意这里不需要任何 LangChain 的代码。MCP Server 是完全独立的，它只关心"我能做什么"（暴露哪些工具），不关心"谁在用我"（哪个 Agent 框架在调用）。

## 在 LangChain 中使用 MCP 工具

### 连接本地 MCP Server（stdio）

LangChain 通过 `langchain-mcp-adapters` 库来桥接 MCP 工具。核心类是 `MultiServerMCPClient`，它可以同时连接多个 MCP Server。

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

async def main():
    client = MultiServerMCPClient(
        {
            "math": {
                "transport": "stdio",
                "command": "python",
                "args": ["math_server.py"],
            }
        }
    )

    # 获取 MCP Server 暴露的所有工具
    tools = await client.get_tools()

    # 直接传给 create_agent，和 @tool 定义的工具用法完全一样
    agent = create_agent(
        "deepseek:deepseek-v4-flash",
        tools,
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "(3 + 5) x 12 等于多少？"}]}
    )
    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
```

这里的关键步骤：

1. `MultiServerMCPClient` 配置了名为 "math" 的 MCP Server，用 stdio 传输，启动命令是 `python math_server.py`
2. `client.get_tools()` 连接 MCP Server，获取它暴露的所有工具（`add` 和 `multiply`），自动转换成 LangChain 的 Tool 对象
3. 转换后的工具直接传给 `create_agent`，用法和 `@tool` 定义的工具完全一样——Agent 不知道也不关心这些工具来自 MCP 还是本地函数

### 连接远程 MCP Server（HTTP）

如果你的 MCP Server 部署在远程服务器上，用 HTTP 传输：

```python
client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://your-server:8000/mcp",
        }
    }
)

tools = await client.get_tools()
```

远程连接还支持传自定义 Header（比如认证 Token）：

```python
client = MultiServerMCPClient(
    {
        "weather": {
            "transport": "http",
            "url": "http://your-server:8000/mcp",
            "headers": {
                "Authorization": "Bearer your-token-here",
            },
        }
    }
)
```

### 同时连接多个 MCP Server

`MultiServerMCPClient` 的 "Multi" 就体现在这里——一个 Client 可以同时连接多个 MCP Server，每个 Server 可以用不同的传输方式：

```python
client = MultiServerMCPClient(
    {
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["math_server.py"],
        },
        "weather": {
            "transport": "http",
            "url": "http://your-server:8000/mcp",
        },
    }
)

tools = await client.get_tools()
```

`get_tools()` 会返回所有 Server 的工具合集。Agent 拿到的是一个统一的工具列表，不需要区分"这个工具来自哪个 Server"。

### MCP 工具和 @tool 工具混合使用

MCP 工具和 `@tool` 定义的自定义工具可以放在同一个列表里传给 Agent：

```python
from langchain_core.tools import tool

# 自定义工具：业务逻辑
@tool
def process_order(order_id: str) -> str:
    """处理订单"""
    return f"订单 {order_id} 处理完成"

# MCP 工具：通用能力
client = MultiServerMCPClient(
    {
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@anthropic/mcp-filesystem", "/tmp"],
        }
    }
)

mcp_tools = await client.get_tools()
business_tools = [process_order]

# 合并
agent = create_agent(
    "deepseek:deepseek-v4-flash",
    mcp_tools + business_tools,
)
```

Agent 不会区分工具来源。对 LLM 来说，所有工具都只是一个"名称 + 描述 + 参数 Schema"。

## @tool vs MCP：怎么选

| 维度 | `@tool` | MCP |
|------|---------|-----|
| 工具定义方式 | Python 函数 + 装饰器 | 独立的 MCP Server 进程 |
| 适用场景 | 项目特定的业务逻辑 | 通用能力（文件系统、数据库、搜索） |
| 框架绑定 | 绑定 LangChain | 框架无关，任何支持 MCP 的 Agent 都能用 |
| 生态 | 需要自己写 | 社区有大量现成的 MCP Server（文件系统、GitHub、数据库等） |
| 切换成本 | 换框架就重写 | 换框架只改连接代码，工具不用动 |

实际项目中的推荐做法：**两者配合使用。** MCP 负责通用能力，`@tool` 负责业务特定逻辑。

## 有状态会话

默认情况下，`MultiServerMCPClient` 是无状态的：每次工具调用都创建一个新的 MCP 会话，执行完就清理。如果你的 MCP Server 需要在多次工具调用之间保持状态（比如维护一个上下文），可以显式创建有状态会话：

```python
async with client.session("math") as session:
    tools = await load_mcp_tools(session)
    agent = create_agent("deepseek:deepseek-v4-flash", tools)
    result = await agent.ainvoke({"messages": "算个复杂题目"})
```

`client.session("server_name")` 会创建一个持久的 ClientSession，在整个 `async with` 块内，所有工具调用共享同一个会话。

## 工具拦截器

MCP Server 作为独立进程运行，它无法访问 LangChain Agent 的内部状态（比如用户信息、会话上下文）。**拦截器（Interceptor）**就是用来弥补这个缺口的——它可以在 MCP 工具调用的前后插入自定义逻辑，比如注入用户信息、记录日志、实现重试等。

拦截器是一个异步函数，接收请求和处理器，遵循"洋葱模型"——第一个拦截器是最外层，最后调用工具，再从内到外返回结果：

```python
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

async def logging_interceptor(request: MCPToolCallRequest, handler):
    """在工具调用前后打印日志"""
    print(f"调用工具: {request.name}, 参数: {request.args}")
    result = await handler(request)
    print(f"工具 {request.name} 返回: {result}")
    return result

client = MultiServerMCPClient(
    {"math": {"transport": "stdio", "command": "python", "args": ["math_server.py"]}},
    tool_interceptors=[logging_interceptor],
)
```

拦截器还可以做到更多：修改请求参数、注入认证 Header、根据 Agent 状态过滤工具、实现失败重试等。这里不展开，知道有这个机制就行，需要时查阅 LangChain 文档。

## 小结

- MCP 是 Anthropic 提出的开放协议，标准化了 LLM 和工具之间的交互方式
- MCP 采用 Client-Server 架构，通过 stdio 或 HTTP 传输，通信内容是统一的 JSON-RPC
- MCP Server 可以暴露 Tools（工具）、Resources（资源）、Prompts（提示模板）三类能力
- `langchain-mcp-adapters` 的 `MultiServerMCPClient` 负责连接 MCP Server，获取工具列表
- MCP 工具和 `@tool` 自定义工具可以混合使用，推荐 MCP 负责通用能力，`@tool` 负责业务逻辑
- 拦截器可以在 MCP 工具调用前后插入自定义逻辑（日志、认证、重试等）
