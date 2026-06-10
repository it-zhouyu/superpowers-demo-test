> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前面我们已经手写过工具调用循环：模型返回 `tool_calls`，Python 执行工具，再把 `ToolMessage` 喂回模型，直到模型给出最终回答。

手写循环适合理解底层原理，但每个项目都手写一遍会很麻烦。LangChain 提供了一个更高层的封装：`create_agent`。

它做的事情很直接：**把模型、工具、系统提示词组合成一个能自动循环调用工具的 Agent**。

## 为什么需要 create_agent

先回忆一下手写工具循环做了什么：

```python
messages = [HumanMessage(content="北京今天适合出门吗？")]

ai_message = llm_with_tools.invoke(messages)
messages.append(ai_message)

for tool_call in ai_message.tool_calls:
    tool_result = get_weather.invoke(tool_call["args"])
    messages.append(ToolMessage(
        content=tool_result,
        tool_call_id=tool_call["id"],
    ))

final_message = llm_with_tools.invoke(messages)
print(final_message.content)
```

这段代码有三个固定动作：

1. 调用模型，看它要不要调用工具
2. 如果有 `tool_calls`，执行对应工具
3. 把工具结果放回消息列表，再次调用模型

`create_agent` 就是把这个循环封装起来。你只需要告诉它：

| 你提供什么 | 作用 |
|------------|------|
| `model` | 用哪个模型思考和回答 |
| `tools` | 模型可以调用哪些工具 |
| `system_prompt` | Agent 的角色、规则、行为边界 |

剩下的"模型要不要调工具、调哪个工具、工具结果怎么喂回去、什么时候结束"，都由 Agent 运行时处理。

## 最小天气 Agent

我们还是用天气查询做例子。先定义工具：

```python
from langchain_core.tools import tool

@tool(description="查询指定城市的天气")
def get_weather(city: str) -> str:
    return f"{city}今天晴，气温 26 度。"
```

这个工具有一个参数 `city`，模型会根据用户问题自动生成参数。

然后创建模型：

```python
from langchain_deepseek import ChatDeepSeek

llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)
```

接下来创建 Agent：

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,
    tools=[get_weather],
    system_prompt="你是一个有帮助的助手。需要天气信息时必须调用工具。",
)
```

调用时传入 `messages`：

```python
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "北京今天适合出门吗？请先查天气再回答。"},
    ]
})
```

返回的 `result` 是一个字典，里面最重要的是 `messages`：

```python
for msg in result["messages"]:
    print(type(msg).__name__, msg.content)
```

输出大致是：

```text
HumanMessage 北京今天适合出门吗？请先查天气再回答。
AIMessage
ToolMessage 北京今天晴，气温 26 度。
AIMessage 北京今天天气晴朗，气温 26 度，非常适合出门。
```

这里你没有手写工具循环，但 Agent 已经自动完成了：

1. 模型决定调用 `get_weather`
2. Agent 执行 `get_weather({"city": "北京"})`
3. Agent 把工具结果包装成 `ToolMessage`
4. 模型读取工具结果，生成最终回答

## messages 里发生了什么

`create_agent` 的返回结果里包含完整消息历史。这个消息历史正好能看出 Agent 的执行过程。

我们把每条消息打印得详细一点：

```python
for msg in result["messages"]:
    print(f"\n[{type(msg).__name__}]")
    print(f"content: {msg.content}")

    if getattr(msg, "tool_calls", None):
        print(f"tool_calls: {msg.tool_calls}")

    if getattr(msg, "tool_call_id", None):
        print(f"tool_call_id: {msg.tool_call_id}")
```

你会看到类似这样的结构：

```text
[HumanMessage]
content: 北京今天适合出门吗？请先查天气再回答。

[AIMessage]
content:
tool_calls: [{"name": "get_weather", "args": {"city": "北京"}, "id": "..."}]

[ToolMessage]
content: 北京今天晴，气温 26 度。
tool_call_id: ...

[AIMessage]
content: 北京今天天气晴朗，气温 26 度，非常适合出门。
```

这里有三个关键点：

| 消息 | 说明 |
|------|------|
| 第一条 `AIMessage` | 模型没有直接回答，而是生成了工具调用 |
| `ToolMessage` | Agent 执行工具后，把结果写回消息列表 |
| 第二条 `AIMessage` | 模型看到工具结果后，生成最终回答 |

所以 `create_agent` 不是一种全新的机制，它只是把我们前面手写过的工具调用循环封装成标准流程。

## create_agent 和手写循环的映射

把两种写法对照起来看，会更清楚。

| 手写工具循环 | create_agent |
|--------------|--------------|
| `llm.bind_tools([tool])` | `create_agent(model=llm, tools=[tool])` |
| 自己维护 `messages` | Agent 自动维护执行过程中的消息 |
| 自己解析 `ai_message.tool_calls` | Agent 自动识别工具调用 |
| 自己执行工具函数 | Agent 自动执行工具 |
| 自己创建 `ToolMessage` | Agent 自动创建 `ToolMessage` |
| 自己决定是否继续循环 | Agent 自动循环直到最终回答 |

这也是学习顺序为什么要先手写循环，再学 `create_agent`：

1. 先手写，理解工具调用到底是什么
2. 再用 `create_agent`，知道它帮你省掉了哪几步

如果一上来就用 `create_agent`，代码看起来很短，但出了问题会不知道中间发生了什么。

## 多工具场景

`create_agent` 可以同时绑定多个工具。比如我们再加一个时间工具：

```python
@tool(description="查询指定城市当前时间")
def get_time(city: str) -> str:
    return f"{city}当前时间是 14:30。"
```

创建 Agent 时把两个工具都传进去：

```python
agent = create_agent(
    model=llm,
    tools=[get_weather, get_time],
    system_prompt="你是一个生活助手，需要实时信息时必须调用工具。",
)
```

用户可以一次问两个问题：

```python
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "北京现在几点？天气适合出门吗？"},
    ]
})
```

模型会根据问题决定调用哪些工具。可能先调用 `get_time`，再调用 `get_weather`，最后综合两个结果回答。

这就是 Agent 和普通 Chain 的区别：普通 Chain 是你提前写好固定步骤；Agent 是模型根据当前问题决定下一步要不要调用工具、调用哪个工具。

## 什么时候用 create_agent

`create_agent` 适合这类场景：

| 场景 | 为什么适合 |
|------|------------|
| 工具数量较多 | 模型可以根据问题选择工具 |
| 是否调用工具不固定 | 有些问题能直接回答，有些问题需要工具 |
| 可能连续调用多个工具 | Agent 会自动循环 |
| 想快速搭一个可用 Agent | 少写工具循环代码 |

不适合这类场景：

| 场景 | 更适合的方式 |
|------|--------------|
| 固定步骤流程 | LCEL Chain |
| 只调用一个确定工具 | 手写调用或简单 Chain |
| 强业务规则很多 | 手写流程或 LangGraph |
| 需要精确控制每个节点 | LangGraph |

简单建议：学习和原型阶段用 `create_agent` 很方便；生产环境如果流程复杂、状态多、分支多，就要考虑 LangGraph。

## 加上 DeepSeek 思考模式

前面讲过 DeepSeek 思考模式。`create_agent` 也可以使用开启思考模式的模型：

```python
llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)
```

然后照常创建 Agent：

```python
agent = create_agent(
    model=llm,
    tools=[get_weather],
    system_prompt="你是一个有帮助的助手。需要天气信息时必须调用工具。",
)
```

调用后，`AIMessage` 里除了 `content` 和 `tool_calls`，还会有 `reasoning_content`：

```python
for msg in result["messages"]:
    reasoning = msg.additional_kwargs.get("reasoning_content", "")
    if reasoning:
        print("思考内容长度:", len(reasoning))
```

典型消息结构会变成：

```text
HumanMessage
AIMessage      # reasoning_content + tool_calls
ToolMessage
AIMessage      # reasoning_content + 最终回答
```

也就是说，Agent 仍然是同一个 Agent，只是模型在每轮调用时多返回了思考内容。

## 版本注意：reasoning_content 回传 bug

这里顺便提一个真实 bug。

`create_agent` 和 DeepSeek 思考模式一起使用工具时，旧版 `langchain-deepseek` 曾经会报错。这个问题记录在 [GitHub issue #37178](https://github.com/langchain-ai/langchain/issues/37178) 中。

报错内容是：

```text
Error code: 400
The `reasoning_content` in the thinking mode must be passed back to the API.
```

这个错误是什么意思？

当 DeepSeek 思考模式返回一条 assistant 消息时，这条消息可能同时包含：

| 字段 | 说明 |
|------|------|
| `reasoning_content` | 模型思考过程 |
| `content` | 模型对用户说的话 |
| `tool_calls` | 模型要调用的工具 |

如果下一轮请求要把这条 assistant 消息传回 DeepSeek API，就需要把相关字段保留下来。旧版 `langchain-deepseek` 的问题是：第一轮接收时拿到了 `reasoning_content`，但第二轮发送时没有把它放回 API 请求里，于是 DeepSeek 拒绝请求。

问题流程可以这样理解：

```text
模型第一轮返回 reasoning_content + tool_calls
-> create_agent 执行工具
-> create_agent 准备第二轮模型调用
-> 旧版 langchain-deepseek 丢掉 reasoning_content
-> DeepSeek API 返回 400
```

这个问题在 `langchain-deepseek 1.1.0` 修复。项目里建议直接写：

```text
langchain-deepseek>=1.1.0
```

验证当前版本：

```python
import importlib.metadata

print(importlib.metadata.version("langchain-deepseek"))
```

如果你使用的是 `create_agent + DeepSeek 思考模式 + 工具调用`，这是必须检查的版本项。

## 最小验证代码

配套 demo 里提供了完整验证代码：`langchain-demo/step8_create_agent.py`。

核心逻辑是：

```python
agent = create_agent(
    model=llm,
    tools=[get_weather],
    system_prompt="你是一个有帮助的助手。需要天气信息时必须调用工具。",
)

result = agent.invoke({
    "messages": [
        {"role": "user", "content": "北京今天适合出门吗？请先查天气再回答。"},
    ]
})

for msg in result["messages"]:
    reasoning = msg.additional_kwargs.get("reasoning_content", "")
    print(type(msg).__name__)
    print("content:", msg.content)
    print("reasoning_content 长度:", len(reasoning))
    if getattr(msg, "tool_calls", None):
        print("tool_calls:", msg.tool_calls)
```

正常输出里应该能看到：

```text
HumanMessage
AIMessage      # 有 tool_calls，也有 reasoning_content
ToolMessage
AIMessage      # 有最终回答，也有 reasoning_content
```

关键不是思考内容具体写了什么，而是 Agent 能完整跑完工具调用和第二轮回答。

## 小结

这篇重点讲了 `create_agent`：

- `create_agent` 把模型、工具、系统提示词组合成自动工具调用 Agent
- 它内部封装了"模型生成工具调用 -> 执行工具 -> 写回 ToolMessage -> 再次调用模型"这套循环
- 返回结果里的 `messages` 能看到完整执行过程
- 多工具场景下，模型可以自己决定调用哪个工具
- 简单 Agent 可以直接用 `create_agent`，复杂流程建议进入 LangGraph
- 如果使用 DeepSeek 思考模式和工具调用，确保 `langchain-deepseek>=1.1.0`

到这里，LangChain 入门教程从模型调用、Chain、工具、记忆、流式、思考模式、RAG，一直讲到了 Agent 封装。下一步如果要继续深入，就该进入 LangGraph：用状态图把 Agent 的循环、分支、工具调用、人机交互都显式建模出来。
