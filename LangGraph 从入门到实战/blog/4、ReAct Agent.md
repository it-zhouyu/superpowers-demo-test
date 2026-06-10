> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前面手动搭了一个 ReAct（Reasoning + Acting，推理与行动）循环：定义 agent 节点、写 should_continue 路由函数、连接 ToolNode。能用，但需要手动处理的细节不少——绑定工具、检查 tool_calls、构建条件边。

LangGraph 提供了 `create_react_agent`，把这些重复步骤封装成一行代码。本文先用它快速搭一个 Agent，再拆开看它内部做了什么，最后对比两种方式的适用场景。

## 用 @tool 定义工具

定义工具的方式和前面一样，用 `@tool` 装饰器把普通 Python 函数变成 LangChain 工具：

```python
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气信息"""
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
    """计算数学表达式。输入必须是合法的 Python 数学表达式"""
    try:
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "错误: 表达式包含不允许的字符"
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"

tools = [get_weather, get_time, calculate]
```

三个工具各管一件事。`@tool` 装饰器提取函数名、参数签名、docstring，自动生成工具描述。LLM 根据这些描述决定什么时候调用哪个工具。比如用户问"北京天气"，模型会匹配到 `get_weather`，因为它的 docstring 里有"天气"。

## create_react_agent：一行创建 Agent

前面手动构建 Agent 循环需要 20 多行代码。`create_react_agent` 压缩成一行：

```python
from langchain_deepseek import ChatDeepSeek
from langgraph.prebuilt import create_react_agent
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatDeepSeek(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

agent = create_react_agent(llm, tools)
```

就这样。`create_react_agent` 返回的是一个已经编译好的图，可以直接 `invoke`：

```python
from langchain_core.messages import HumanMessage

result = agent.invoke({
    "messages": [HumanMessage(content="北京今天天气怎么样？顺便帮我算一下 (15 + 27) * 3")]
})

for msg in result["messages"]:
    msg_type = type(msg).__name__
    if msg_type == "HumanMessage":
        print(f"用户: {msg.content}")
    elif msg_type == "AIMessage":
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            print(f"AI 调用工具: {[tc['name'] for tc in msg.tool_calls]}")
        else:
            print(f"AI 回复: {msg.content}")
    elif msg_type == "ToolMessage":
        print(f"工具结果: {msg.content}")
```

输出：

```
用户: 北京今天天气怎么样？顺便帮我算一下 (15 + 27) * 3
AI 调用工具: ['get_weather', 'calculate']
工具结果: 晴天，气温 28 度，空气质量良好
工具结果: (15 + 27) * 3 = 126
AI 回复: 北京今天是晴天，气温28度，空气质量良好。另外，(15 + 27) × 3 = 126。
```

一个用户问题触发了两个工具调用（模型判断需要同时查天气和做计算），工具结果返回后模型综合两个结果生成了最终回复。整个 ReAct 循环——思考、调用工具、观察结果、再思考——全自动完成。

## create_react_agent 的参数

`create_react_agent` 最重要的参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `model` | LLM 实例 | 绑定了工具的模型，用于 agent 节点 |
| `tools` | 工具列表 | Agent 可调用的工具函数 |
| `prompt` | str 或 SystemMessage | 系统提示词，设定 Agent 的行为 |
| `state_schema` | TypedDict | 自定义 State 的结构，默认只有 messages |

`prompt` 参数可以给 Agent 设定角色：

```python
agent = create_react_agent(
    llm,
    tools,
    prompt="你是一个实用的生活助手。回答要简洁，每次不超过两句话。",
)
```

`state_schema` 用来自定义 State 结构。默认 State 只有 `messages` 字段。如果需要额外的字段（比如计数器、上下文），可以传入自定义的 TypedDict。但大部分场景默认的就够用。

## 拆开看：手动构建同样的 Agent

`create_react_agent` 内部做了什么？用手动构建来还原。理解了底层，出了问题才知道怎么调试。

手动构建需要四个部分：State、agent 节点、ToolNode、should_continue 路由函数。

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# State：只需要 messages
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# 绑定工具到 LLM
llm_with_tools = llm.bind_tools(tools)

# agent 节点：调用绑定了工具的 LLM
def agent_node(state: AgentState) -> dict:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# should_continue：判断是否需要调用工具
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# ToolNode：自动执行 tool_calls
tool_node = ToolNode(tools)

# 构建图
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")  # 工具执行完回到 agent

app = graph.compile()
```

这就是 `create_react_agent` 内部做的事情，步骤对应关系：

| create_react_agent 内部 | 对应的手动代码 |
|-------------------------|--------------|
| 自动调用 `bind_tools` | `llm_with_tools = llm.bind_tools(tools)` |
| 自动创建 agent 节点 | `def agent_node(state)` |
| 自动创建 should_continue | `def should_continue(state)` |
| 自动创建 ToolNode | `tool_node = ToolNode(tools)` |
| 自动连接边和条件边 | `add_edge` + `add_conditional_edges` |
| 自动 compile | `app = graph.compile()` |

手动构建的执行效果和 `create_react_agent` 完全一样：

```python
result = app.invoke({
    "messages": [HumanMessage(content="深圳天气如何？现在几点了？")]
})
```

输出：

```
AI 调用工具: ['get_weather', 'get_time']
工具结果: 雷阵雨，气温 32 度，湿度较高
工具结果: 当前时间: 2026-06-04 14:30:00 (时区: Asia/Shanghai)
AI 回复: 深圳现在雷阵雨，气温32度，湿度较高。当前时间是下午2点30分。
```

## 流式输出：逐步观察 Agent 的执行

`invoke` 会等所有节点执行完才返回。如果你想实时看到 Agent 在做什么——先思考了什么、调用了哪个工具、工具返回了什么——用 `stream()`：

```python
question = "帮我算一下 1024 * 768"
print(f"用户: {question}\n")

for event in app.stream({"messages": [HumanMessage(content=question)]}):
    for node_name, node_output in event.items():
        if "messages" in node_output:
            last_msg = node_output["messages"][-1]
            msg_type = type(last_msg).__name__
            if msg_type == "AIMessage":
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    print(f"  [{node_name}] 调用工具: {last_msg.tool_calls[0]['name']}")
                else:
                    print(f"  [{node_name}] 回复: {last_msg.content}")
            elif msg_type == "ToolMessage":
                print(f"  [{node_name}] 工具返回: {last_msg.content}")
```

`stream()` 每个节点执行完就返回一次。输出是实时的，不需要等整个图跑完：

```
用户: 帮我算一下 1024 * 768

  [agent] 调用工具: calculate
  [tools] 工具返回: 1024 * 768 = 786432
  [agent] 回复: 1024 × 768 = 786,432
```

可以看到完整的执行过程：agent 节点决定调用 calculate → ToolNode 执行计算 → agent 节点拿到结果生成最终回复。

stream 还有第二种调用方式——按事件类型过滤：

```python
for event in app.stream(
    {"messages": [HumanMessage(content="北京天气？")]},
    stream_mode="updates",
):
    print(event)
```

`stream_mode` 参数控制输出格式：

| stream_mode | 输出内容 | 适用场景 |
|-------------|---------|---------|
| `"values"` | 每步执行后的完整 State 快照 | 需要看 State 的完整变化 |
| `"updates"` | 每步的增量更新（只包含该节点返回的字段） | 需要看每个节点做了什么 |
| `"messages"` | 逐条输出 LLM 的 token | 需要实时展示模型的生成过程 |

默认是 `"values"`。`"updates"` 更轻量，只包含增量数据。`"messages"` 适合在前端做打字机效果。

## 快捷方式 vs 手动构建：何时用哪个

两种方式生成功能完全相同的 Agent，选择取决于你的需求：

| 维度 | create_react_agent | 手动构建 |
|------|-------------------|---------|
| 代码量 | 1 行 | 约 25 行 |
| 自定义程度 | 只能设 prompt 和 state_schema | 完全控制每个节点和边 |
| 调试难度 | 不方便观察中间步骤，只能看输入输出 | 可以在每个节点加日志 |
| 扩展性 | 加新功能需要换手动构建 | 随时加节点、改路由逻辑 |
| 适用场景 | 快速原型、标准 ReAct | 需要定制流程、多工具协调、复杂控制 |

实际项目中的常见路径：先用 `create_react_agent` 验证想法，跑通基本流程后，如果需要定制（比如在 agent 和 tools 之间加一个审核节点，或者限制单次对话的工具调用次数），就切换到手动构建。

`create_react_agent` 生成的图结构可以通过 `get_graph()` 查看：

```python
print(agent.get_graph().draw_mermaid())
```

输出和手动构建的图结构是一样的：agent 节点 + tools 节点 + 条件边循环。

## 工具调用的完整生命周期

通过一个完整的执行过程理解 ReAct 循环中消息的流转。用户问"北京天气怎么样"，State 中 messages 的变化过程：

**第 1 步：初始输入**

```python
[HumanMessage(content="北京天气怎么样？")]
```

**第 2 步：agent 节点（第 1 次执行）**

LLM 判断需要调用 get_weather 工具，返回带 tool_calls 的 AIMessage：

```python
[
    HumanMessage(content="北京天气怎么样？"),
    AIMessage(content="", tool_calls=[{"name": "get_weather", "args": {"city": "北京"}}]),
]
```

`should_continue` 检测到 tool_calls，路由到 tools 节点。

**第 3 步：tools 节点执行**

ToolNode 执行 get_weather("北京")，返回 ToolMessage：

```python
[
    ...,
    ToolMessage(content="晴天，气温 28 度，空气质量良好", name="get_weather"),
]
```

**第 4 步：agent 节点（第 2 次执行）**

LLM 拿到工具结果，生成最终回复。这次 AIMessage 没有 tool_calls：

```python
[
    ...,
    AIMessage(content="北京今天是晴天，气温28度，空气质量良好。"),
]
```

`should_continue` 检测不到 tool_calls，返回 END。图执行结束。

整个过程中 agent 节点执行了两次，第一次负责决策（调用工具），第二次负责总结（生成回复）。如果问题更复杂，可能需要更多轮循环——模型可能先查天气，再根据天气结果调用推荐工具，每一步都是一个 agent → tools → agent 的循环。

## 小结

- **create_react_agent** 一行代码创建 ReAct Agent，适合快速验证
- **@tool 装饰器** 定义工具函数，函数名和 docstring 是模型选择工具的依据
- **手动构建** 拆开看就是 StateGraph + agent_node + ToolNode + should_continue
- **stream()** 逐步返回每个节点的输出，比 invoke 更适合观察 Agent 的思考过程
- **stream_mode** 控制流式输出的格式：values（完整快照）、updates（增量）、messages（逐 token）
- **选择建议**：先用 create_react_agent 跑通，需要定制时切换手动构建

## 完整代码

把下面代码保存为 `step4_react_agent.py`，并和前面的 `config.py` 放在同一个目录下运行：

```python
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
```
