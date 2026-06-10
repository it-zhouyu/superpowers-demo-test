> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

如果你之前用 OpenAI 的 Python SDK 调用过 LLM，代码大概长这样：

```python
from openai import OpenAI

client = OpenAI(api_key="sk-xxx")

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "你好"}],
)

print(response.choices[0].message.content)
```

能用，但每做一件事都得自己拼。想加系统提示词？自己拼 messages 数组。想解析 JSON 输出？自己写正则或 json.loads。想把多步操作串起来？自己写循环。项目小的时候没问题，一旦需求变复杂，重复代码到处都是。

LangChain 做的事情很简单：把这些重复模式封装成现成的组件，然后用一条统一的语法把它们串起来。同样的调用，LangChain 的写法是：

```python
from langchain_deepseek import ChatDeepSeek

llm = ChatDeepSeek(model="deepseek-v4-flash", api_key="sk-xxx")
ai_message = llm.invoke("你好")
print(ai_message.content)
```

看起来差不多？别急，这只是最基础的用法。当你需要加提示词模板、输出解析、工具调用的时候，差别就出来了。后面的文章会一步步展示。

本文先从零开始，搞定三件事：安装依赖、调用模型、理解 LangChain 的链式语法。

## 安装依赖

```bash
pip install langchain langchain-deepseek python-dotenv
```

三个包各管一件事：

| 包名 | 作用 |
|------|------|
| langchain | 核心框架，提供 Chain、Prompt Template、Output Parser 等基础组件 |
| langchain-deepseek | DeepSeek 模型的适配器，让 LangChain 能调用 DeepSeek API |
| python-dotenv | 从 .env 文件加载环境变量，避免把 API Key 写死在代码里 |

在项目根目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

其中 `deepseek-v4-flash` 是 DeepSeek V4 Flash 模型的 API 参数名，调用时直接用这个名字就行。

## 创建模型实例

```python
from langchain_deepseek import ChatDeepSeek

llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
    temperature=0,
)
```

逐行说明：

- `model`：模型名称，对应 DeepSeek API 的模型标识符
- `api_key`：你的 API Key，建议从环境变量读取，不要硬编码
- `base_url`：API 地址，DeepSeek 默认是 `https://api.deepseek.com`，如果你的 Key 走中转服务，改成对应的地址
- `temperature`：控制输出的随机性，0 表示每次调用尽量给出相同结果，适合教程演示和需要稳定输出的场景

如果用环境变量管理（推荐），可以借助 python-dotenv：

```python
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatDeepSeek(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    temperature=0,
)
```

## 第一次调用：观察 AIMessage

```python
ai_message = llm.invoke("你好")
```

一行代码就调完了。但 `invoke` 返回的不是纯字符串，而是一个 `AIMessage` 对象。看看它里面有什么：

```python
print(f"content: {ai_message.content}")
print(f"response_metadata: {ai_message.response_metadata}")
print(f"id: {ai_message.id}")
```

输出大致如下：

```
content: 你好！很高兴见到你！我是DeepSeek，一个AI助手，可以帮你解答问题、提供建议、进行创作、处理文档等等。无论你有什么需要，都可以随时告诉我！
response_metadata: {'token_usage': {'completion_tokens': 198, 'prompt_tokens': 5, 'total_tokens': 203, 'completion_tokens_details': {'reasoning_tokens': 143}, 'prompt_tokens_details': {'cached_tokens': 0}}, 'model_provider': 'deepseek', 'model_name': 'deepseek-v4-flash', 'finish_reason': 'stop'}
id: lc_run--019e952b-93ac-7ed1-b4ce-61f3f87b5cde-0
```

`AIMessage` 是 LangChain 对模型回复的封装，三个字段各管一件事：

| 字段 | 类型 | 说明 |
|------|------|------|
| `content` | str | 模型回复的文本内容，这是你最常用的字段 |
| `response_metadata` | dict | 模型返回的元信息，包括模型名称、Token 用量等 |
| `id` | str | 本次回复的唯一标识，用于日志追踪 |

大部分时候你只需要 `content`，但 `response_metadata` 里的 token 用量在监控成本时很有用。

## LCEL：LangChain 的组合语法

每次调用模型后手动取 `.content` 太麻烦了。LangChain 提供了一种更统一的组合方式：**LCEL**（LangChain Expression Language，LangChain 表达式语言）。

核心写法就一个符号：组合符 `|`。

把多个组件用 `|` 连起来，数据从左到右依次传给每个组件，上一个组件的输出自动变成下一个组件的输入。

来看第一个 LCEL 链：

```python
from langchain_core.output_parsers import StrOutputParser

chain = llm | StrOutputParser()
result = chain.invoke("用一句话介绍 LangChain")
print(result)
```

`StrOutputParser` 做的事情很简单：接收 `AIMessage`，返回它的 `.content`。也就是说，它帮你把 `ai_message.content` 这一步自动化了。

对比一下没有 LCEL 的写法：

```python
# 没有 LCEL：手动处理每一步
ai_message = llm.invoke("用一句话介绍 LangChain")
result = ai_message.content

# 有 LCEL：组件自动传递
result = (llm | StrOutputParser()).invoke("用一句话介绍 LangChain")
```

现在只有两步，差别不大。但后面加上提示词模板、输出解析器、工具调用，每多一步手动传递就多一份重复代码。LCEL 的优势在组件越多时越明显。

## 带提示词模板的完整链

上面的链直接把用户输入传给模型，没有系统提示词。实际项目中你通常会告诉模型"你扮演什么角色"。LangChain 用 `ChatPromptTemplate` 来管理提示词：

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 定义提示词模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是{role}，请用专业但易懂的方式回答问题。"),
    ("human", "{input}"),
])

# 用组合符串成完整链路
chain = prompt | llm | StrOutputParser()

# 调用
result = chain.invoke({
    "role": "一位资深 Python 开发工程师",
    "input": "Python 的 GIL 是什么？",
})
print(result)
```

这条链的执行过程：

1. `prompt` 接收字典 `{"role": "...", "input": "..."}`，把占位变量替换成实际值，生成消息列表
2. 消息列表自动传给 `llm`，模型生成回复
3. `AIMessage` 自动传给 `StrOutputParser()`，提取出纯文本

三步之间不需要任何手动传递，`|` 会按从左到右的顺序把组件连接起来。

`ChatPromptTemplate.from_messages()` 接收一个元组列表，每个元组的第一个元素是角色名，第二个是模板字符串。模板中的 `{role}` 和 `{input}` 是占位变量，`invoke` 时传入对应值的字典即可。

## 小结

回顾一下本文涉及的核心概念：

- **ChatDeepSeek**：LangChain 封装的 DeepSeek 模型客户端，`invoke()` 方法发送消息并返回 `AIMessage`
- **AIMessage**：模型回复的封装对象，包含 `content`（文本）、`response_metadata`（元信息）、`id`（标识）
- **LCEL**：LangChain 的组合语法，用 `|` 把组件串成处理链，数据自动流转
- **StrOutputParser**：最简单的输出解析器，从 `AIMessage` 中提取纯文本
- **ChatPromptTemplate**：提示词模板，支持角色区分和变量占位

## 完整代码

把下面代码保存为 `step1_first_chain.py`，并和前面的 `config.py` 放在同一个目录下运行：

```python
from langchain_deepseek import ChatDeepSeek
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

def main():
    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0,
    )

    print("=" * 50)
    print("Demo 1: 直接调用 llm.invoke()")
    print("=" * 50)

    ai_message = llm.invoke("你好")
    print(f"\n[content] 模型回复的文本内容：\n{ai_message.content}")
    print(f"\n[response_metadata] 模型返回的元信息：\n{ai_message.response_metadata}")
    print(f"\n[id] 本次回复的唯一标识：\n{ai_message.id}")

    print("\n" + "=" * 50)
    print("Demo 2: LCEL Chain = llm | StrOutputParser")
    print("=" * 50)

    chain = llm | StrOutputParser()
    result = chain.invoke("用一句话介绍 LangChain")
    print(f"\n{result}")

    print("\n" + "=" * 50)
    print("Demo 3: prompt | llm | StrOutputParser")
    print("=" * 50)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是{role}，请用专业但易懂的方式回答问题。"),
        ("human", "{input}"),
    ])

    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({
        "role": "一位资深 Python 开发工程师",
        "input": "Python 的 GIL 是什么？为什么它在多线程场景下很重要？",
    })
    print(f"\n{result}")

if __name__ == "__main__":
    main()
```
