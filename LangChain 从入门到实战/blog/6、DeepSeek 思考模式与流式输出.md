> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前面我们学了 LangChain 的流式输出：`stream()`、`astream()`、`astream_events()` 都能让最终回答逐字显示。

但 DeepSeek 还有一个特殊能力：思考模式（Thinking Mode）。开启后，模型会先输出一段 `reasoning_content`，表示它的推理过程；然后再输出 `content`，也就是最终回答。

这篇就解决两个问题：

1. 在 LangChain 里怎么开启 DeepSeek 的思考模式
2. 怎么把思考过程和最终回答都流式输出出来

## 开启 DeepSeek 思考模式

DeepSeek V4 系列支持思考模式和非思考模式。本文使用当前官方推荐的模型名：

```python
model="deepseek-v4-pro"
```

如果你想用更便宜、更快的版本，也可以换成：

```python
model="deepseek-v4-flash"
```

在 OpenAI 兼容 API 格式下，开启思考模式要传两个关键参数：

```python
reasoning_effort="high"
extra_body={"thinking": {"type": "enabled"}}
```

放到 LangChain 里就是这样：

```python
from langchain_deepseek import ChatDeepSeek

llm = ChatDeepSeek(
    model="deepseek-v4-pro",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)
```

这里先解释一下这两个参数：

| 参数 | 作用 |
|------|------|
| `extra_body={"thinking": {"type": "enabled"}}` | 开启 DeepSeek 的思考模式 |
| `reasoning_effort="high"` | 控制思考强度，常用值是 `"high"` 或 `"max"` |

`extra_body` 是 LangChain 透传给底层 OpenAI 兼容 API 的额外请求参数。DeepSeek 的思考模式开关不属于标准的 OpenAI 顶层参数，所以需要放在 `extra_body` 里。

`reasoning_effort` 控制模型在思考阶段投入多少推理力度。一般任务用 `"high"` 就够了；更复杂的数学、代码分析、长上下文推理，可以用 `"max"`。

注意：DeepSeek 官方说明，思考模式下 `temperature`、`top_p`、`presence_penalty`、`frequency_penalty` 这些采样参数不会生效。为了避免误导，开启思考模式时不要再传这些参数。

## 非流式读取思考内容

先不用流式，直接看一次完整调用会返回什么。

```python
response = llm.invoke("9.11 和 9.8 哪个更大？请给出简短结论。")

reasoning = response.additional_kwargs.get("reasoning_content", "")
answer = response.content

print("思考过程:")
print(reasoning)

print("\n最终回答:")
print(answer)
```

输出结构大致是这样：

```text
思考过程:
需要比较 9.11 和 9.8。把 9.8 写成 9.80，9.80 大于 9.11...

最终回答:
9.8 更大。因为 9.8 等于 9.80，而 9.80 > 9.11。
```

这里有一个关键点：`response.content` 里只有最终回答，不包含思考过程。

思考过程在：

```python
response.additional_kwargs["reasoning_content"]
```

这是 `langchain-deepseek` 帮我们从 DeepSeek API 返回值里取出来的字段。

## 流式输出思考过程

前面我们已经用过：

```python
for chunk in llm.stream("用100字介绍Python"):
    print(chunk.content, end="", flush=True)
```

普通流式输出只打印 `chunk.content`。但开启 DeepSeek 思考模式后，每个 chunk 可能有两类内容：

| 字段 | 含义 |
|------|------|
| `chunk.additional_kwargs["reasoning_content"]` | 当前片段的思考过程 |
| `chunk.content` | 当前片段的最终回答 |

所以流式输出思考过程时，要同时检查这两个字段：

```python
reasoning_text = ""
answer_text = ""
is_answer_started = False

for chunk in llm.stream("9.11 和 9.8 哪个更大？请给出简短结论。"):
    reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
    answer_chunk = chunk.content

    if reasoning_chunk:
        reasoning_text += reasoning_chunk
        print(reasoning_chunk, end="", flush=True)

    if answer_chunk:
        if not is_answer_started:
            is_answer_started = True
            print("\n\n最终回答:\n", end="", flush=True)

        answer_text += answer_chunk
        print(answer_chunk, end="", flush=True)
```

运行时的显示效果大致是：

```text
需要比较 9.11 和 9.8。先把 9.8 写成 9.80...

最终回答:
9.8 更大。因为 9.8 等于 9.80，而 9.80 > 9.11。
```

这段代码做了三件事：

1. 从 `additional_kwargs` 里取 `reasoning_content`，有内容就打印到"思考过程"区域
2. 从 `content` 里取最终回答，有内容就打印到"最终回答"区域
3. 用 `is_answer_started` 判断最终回答是不是第一次出现，第一次出现时插入分隔标题

为什么需要 `is_answer_started`？因为 DeepSeek 的流式输出通常先输出思考过程，再输出最终回答。我们不想在每个回答片段前都打印一次"最终回答"，只需要在第一个回答片段到达时打印一次。

## 封装成可复用函数

实际项目里，不建议每次都手写一遍循环。可以封装成一个函数：

```python
def stream_deepseek_thinking(llm, question: str) -> tuple[str, str]:
    """流式输出 DeepSeek 思考过程和最终回答"""
    reasoning_text = ""
    answer_text = ""
    is_answer_started = False

    print("思考过程:\n", end="", flush=True)

    for chunk in llm.stream(question):
        reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
        answer_chunk = chunk.content

        if reasoning_chunk:
            reasoning_text += reasoning_chunk
            print(reasoning_chunk, end="", flush=True)

        if answer_chunk:
            if not is_answer_started:
                is_answer_started = True
                print("\n\n最终回答:\n", end="", flush=True)

            answer_text += answer_chunk
            print(answer_chunk, end="", flush=True)

    print()
    return reasoning_text, answer_text
```

用的时候只需要传入模型和问题：

```python
reasoning, answer = stream_deepseek_thinking(
    llm,
    "请判断：9.11 和 9.8 哪个更大？",
)
```

这个函数返回两个字符串：

| 返回值 | 说明 |
|--------|------|
| `reasoning` | 完整思考过程 |
| `answer` | 完整最终回答 |

这样前端既可以实时显示思考过程，也可以在结束后把完整内容保存到日志或数据库。

## Chain 中流式输出思考过程

如果只调用 LLM，前面的代码已经够用了。但实际项目经常会用 LCEL 拼 Chain。

先看一个容易写错的版本：

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个严谨的数学老师，用中文回答。"),
    ("human", "{question}"),
])

chain = prompt | llm | StrOutputParser()
```

这个 Chain 能流式输出最终回答，但不适合展示思考过程。原因是 `StrOutputParser()` 会把 `AIMessageChunk` 解析成普通字符串，解析后只剩最终文本，`additional_kwargs["reasoning_content"]` 就拿不到了。

如果要展示思考过程，先不要接 `StrOutputParser()`：

```python
chain = prompt | llm
```

然后这样流式读取：

```python
for chunk in chain.stream({"question": "9.11 和 9.8 哪个更大？"}):
    reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
    answer_chunk = chunk.content

    if reasoning_chunk:
        print(reasoning_chunk, end="", flush=True)

    if answer_chunk:
        print(answer_chunk, end="", flush=True)
```

这里的 `chunk` 仍然是 `AIMessageChunk`，所以可以同时访问：

```python
chunk.additional_kwargs.get("reasoning_content")
chunk.content
```

如果你只关心最终回答，再接 `StrOutputParser()`；如果你要展示思考过程，就保留原始消息对象。

## 异步流式输出

Web 服务通常用异步方式，比如 FastAPI 里返回 SSE（Server-Sent Events，服务器推送事件）。这时用 `astream()`：

```python
async def astream_deepseek_thinking(llm, question: str):
    reasoning_text = ""
    answer_text = ""
    is_answer_started = False

    print("思考过程:\n", end="", flush=True)

    async for chunk in llm.astream(question):
        reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
        answer_chunk = chunk.content

        if reasoning_chunk:
            reasoning_text += reasoning_chunk
            print(reasoning_chunk, end="", flush=True)

        if answer_chunk:
            if not is_answer_started:
                is_answer_started = True
                print("\n\n最终回答:\n", end="", flush=True)

            answer_text += answer_chunk
            print(answer_chunk, end="", flush=True)

    print()
    return reasoning_text, answer_text
```

调用方式：

```python
import asyncio

asyncio.run(astream_deepseek_thinking(
    llm,
    "请用三步推理解释：为什么 9.8 大于 9.11？",
))
```

如果要发给前端，可以把思考片段和回答片段分成两种事件：

```python
async for chunk in llm.astream(question):
    reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
    answer_chunk = chunk.content

    if reasoning_chunk:
        yield {"type": "reasoning", "content": reasoning_chunk}

    if answer_chunk:
        yield {"type": "answer", "content": answer_chunk}
```

前端拿到 `type="reasoning"` 就显示在"思考过程"区域，拿到 `type="answer"` 就显示在"最终回答"区域。

## 思考模式下调用工具

思考模式也可以和工具调用一起用。比如定义一个天气工具：

```python
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。"""
    return f"{city}今天晴，气温 26 度。"
```

然后把工具绑定到开启思考模式的模型上：

```python
llm_with_tools = llm.bind_tools([get_weather])
```

第一轮调用时，模型会先思考，然后生成工具调用：

```python
messages = [
    HumanMessage(content="北京今天适合出门吗？请先查询天气工具再回答。")
]

ai_message = llm_with_tools.invoke(messages)

print(ai_message.content)
print(ai_message.additional_kwargs.get("reasoning_content"))
print(ai_message.tool_calls)
```

返回结构大致是这样：

```python
ai_message.content
# "好的，我先查询一下北京的天气情况。"

ai_message.additional_kwargs["reasoning_content"]
# "需要查询北京天气，然后根据天气判断是否适合出门..."

ai_message.tool_calls
# [{"name": "get_weather", "args": {"city": "北京"}, "id": "..."}]
```

接下来执行工具，并把工具结果包装成 `ToolMessage`：

```python
messages.append(ai_message)

for tool_call in ai_message.tool_calls:
    tool_result = get_weather.invoke(tool_call["args"])
    messages.append(
        ToolMessage(
            content=tool_result,
            tool_call_id=tool_call["id"],
        )
    )

final_message = llm_with_tools.invoke(messages)
print(final_message.content)
```

这里最关键的一点是：**把 LangChain 返回的 `ai_message` 原样 append 回 `messages`**。

不要自己手写一个新的 AI 消息，只保留 `content` 和 `tool_calls`。因为在 DeepSeek 思考模式下，`reasoning_content` 也属于这轮 assistant 消息的一部分。

另外，如果你要在思考模式下使用工具调用，建议把 `langchain-deepseek` 升到 1.1.0 以上：

```text
langchain-deepseek>=1.1.0
```

因为旧版本在 `create_agent` 这类 Agent 内部多轮调用时，曾经出现过 `reasoning_content` 没有被正确带回下一轮请求的问题。这个 bug 我们放到后面会单独讲。

## 流式输出工具调用

如果第一轮也要流式输出，工具调用本身会通过 `tool_call_chunks` 分片返回。做法和前面讲到的流式工具调用类似：把每个 chunk 累积起来，最后得到完整的工具调用。

```python
full_chunk = None
reasoning_text = ""
answer_text = ""

for chunk in llm_with_tools.stream(messages):
    full_chunk = chunk if full_chunk is None else full_chunk + chunk

    reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
    answer_chunk = chunk.content

    if reasoning_chunk:
        reasoning_text += reasoning_chunk
        print(reasoning_chunk, end="", flush=True)

    if answer_chunk:
        answer_text += answer_chunk
```

循环结束后，`full_chunk.tool_calls` 就是完整工具调用：

```python
print(full_chunk.tool_calls)
```

然后把 `full_chunk` 原样放回消息列表，再追加工具结果：

```python
messages.append(full_chunk)

for tool_call in full_chunk.tool_calls:
    tool_result = get_weather.invoke(tool_call["args"])
    messages.append(
        ToolMessage(
            content=tool_result,
            tool_call_id=tool_call["id"],
        )
    )
```

第二轮再调用模型，让它基于工具结果生成最终回答：

```python
for chunk in llm_with_tools.stream(messages):
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

这个流程里有两个要点：

1. `chunk.additional_kwargs["reasoning_content"]` 是思考过程片段
2. `chunk.tool_call_chunks` 是工具调用片段，需要靠 `full_chunk = full_chunk + chunk` 累积成完整工具调用

思考模式下的工具调用流程可以理解成：

```text
用户问题
-> 模型思考 reasoning_content
-> 模型生成 tool_calls
-> Python 执行工具
-> ToolMessage 写回消息列表
-> 模型继续思考
-> 模型生成最终回答 content
```

## 多轮对话要注意什么

DeepSeek 的思考模式有一个容易踩坑的点：`reasoning_content` 和普通 `content` 不是同一个字段。

如果只是普通多轮对话，没有工具调用，DeepSeek 官方说明：上一轮的 `reasoning_content` 不需要参与下一轮上下文拼接。也就是说，下一轮通常只需要保留最终回答：

```python
messages = [
    ("human", "9.11 和 9.8 哪个更大？"),
    ("ai", "9.8 更大。因为 9.8 等于 9.80，而 9.80 > 9.11。"),
    ("human", "那 9.11 和 9.09 呢？"),
]
```

如果中间涉及工具调用，建议不要主动丢掉 `reasoning_content`。工程上最稳的做法是：**不要手动重建 assistant 消息，直接保留 LangChain 返回的原始消息对象**。这样可以保留 `tool_calls`、`reasoning_content`、响应元数据等字段。

简单记：

| 场景 | 建议 |
|------|------|
| 普通多轮对话，没有工具调用 | 通常只保留最终回答即可 |
| 思考模式 + 手写工具循环 | 原样保留 LangChain 返回的 `AIMessage` / `AIMessageChunk` |
| 思考模式 + `create_agent` | 使用 `langchain-deepseek>=1.1.0`，后面会单独讲 |

实际做 Agent 时，如果你要同时开启 DeepSeek 思考模式和工具调用，最好写一个最小测试：让模型调用一次工具，再把工具结果喂回去，看第二轮是否能正常生成最终回答。

## 什么时候开启思考模式

思考模式不是所有任务都要开。

适合开启的场景：

| 场景 | 原因 |
|------|------|
| 数学推理 | 需要多步比较、计算、验证 |
| 代码分析 | 需要先定位问题，再给修改建议 |
| 复杂规划 | 需要拆步骤、权衡方案 |
| 长上下文总结 | 需要先梳理材料，再组织答案 |

不太适合开启的场景：

| 场景 | 原因 |
|------|------|
| 简单问答 | 思考过程会增加等待时间和 token 消耗 |
| 固定格式抽取 | 直接结构化输出更合适 |
| 高频客服回复 | 更看重速度和成本 |
| 不希望暴露推理过程的产品界面 | 可以只展示最终回答 |

实用建议：默认用非思考模式；遇到复杂推理、代码分析、长文档理解时，再开启思考模式。

## 小结

这篇学了 DeepSeek 思考模式在 LangChain 里的用法：

- 用 `extra_body={"thinking": {"type": "enabled"}}` 开启思考模式
- 用 `reasoning_effort="high"` 或 `"max"` 控制思考强度
- 非流式调用时，从 `response.additional_kwargs["reasoning_content"]` 读取思考过程
- 流式调用时，从 `chunk.additional_kwargs["reasoning_content"]` 读取思考片段，从 `chunk.content` 读取最终回答片段
- 如果要展示思考过程，Chain 末尾不要接 `StrOutputParser()`，否则会丢失 `additional_kwargs`
- 思考模式下也能调用工具；流式工具调用需要累积 `tool_call_chunks`，并把累积后的消息原样放回 `messages`
- 普通多轮对话通常不需要回传上一轮 `reasoning_content`，但思考模式下的手写工具循环建议保留 LangChain 返回的原始消息对象
