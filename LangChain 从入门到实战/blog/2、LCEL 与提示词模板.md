> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前面我们搭出了第一条 LCEL 链：`prompt | llm | StrOutputParser()`。它能工作了，但提示词模板还比较基础——只用了 system 和 human 两个角色，没有对话历史，也没有对输出格式做任何约束。

这一篇解决这些问题：多角色模板、注入对话历史、结构化输出、在链中做自定义处理、并行执行多条链。

## ChatPromptTemplate 的多角色模板

前面讲到的模板用了一个 system 和一个 human：

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是{role}，请用专业但易懂的方式回答问题。"),
    ("human", "{input}"),
])
```

`from_messages` 其实支持更多角色。来看一个包含三种角色的例子：

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{style}风格的翻译官。"),
    ("human", "请把以下内容翻译成英文：{text}"),
])

formatted = prompt.invoke({
    "style": "幽默",
    "text": "今天天气真好",
})
```

注意 `prompt.invoke()` 这一步只做模板填充，不会调用模型。返回的是 `ChatPromptValue` 对象，可以用 `.to_messages()` 查看生成的消息列表：

```python
for msg in formatted.to_messages():
    print(f"{msg.type}: {msg.content}")
```

输出：

```
system: 你是一个幽默风格的翻译官。
human: 请把以下内容翻译成英文：今天天气真好
```

`from_messages` 支持的角色类型：

| 角色名 | 对应 OpenAI 的 role | 用途 |
|--------|---------------------|------|
| `system` | system | 设定模型的行为规则、角色设定 |
| `human` | user | 用户输入的消息 |
| `ai` | assistant | 模型之前的回复，用于构建多轮对话的上下文 |
| `placeholder` | — | 注入一组动态消息，比如对话历史 |

前三个都是单个消息，用 `("角色名", "内容")` 元组表示。第四个下面单独讲。

## MessagesPlaceholder：注入对话历史

角色模板能拼 system/human/ai，但多轮对话的历史消息数量是不固定的——可能两条，可能二十条。这时候需要一个"占位符"，在调用时动态塞入一整组消息。`MessagesPlaceholder` 就是干这个的。

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有帮助的AI助手。"),
    MessagesPlaceholder("history"),
    ("human", "{input}"),
])
```

注意这行 `MessagesPlaceholder("history")`——它声明了一个叫 `history` 的占位符，调用时会用一组消息来替换。

```python
history = [
    HumanMessage(content="LangChain 是什么？"),
    AIMessage(content="LangChain 是一个用于构建 LLM 应用的框架。"),
]

formatted = prompt.invoke({
    "history": history,
    "input": "它有哪些核心模块？",
})

for msg in formatted.to_messages():
    print(f"{msg.type}: {msg.content}")
```

输出：

```
system: 你是一个有帮助的AI助手。
human: LangChain 是什么？
ai: LangChain 是一个用于构建 LLM 应用的框架。
human: 它有哪些核心模块？
```

四条消息按顺序排列，模型能看到完整对话上下文。这就是实现多轮对话的基础——每次调用时把之前的对话记录塞进 `history`。

## 输出解析器：从自由文本到结构化数据

到目前为止，我们用的都是 `StrOutputParser`，它只做一件事：提取纯文本。但很多时候你需要模型返回结构化的数据，比如一个 JSON 对象。

LangChain 提供了 `JsonOutputParser`，配合 Pydantic 模型来约束输出格式：

**什么是 Pydantic？** 它是 Python 的数据验证库，核心做的事情就一件：用带类型注解的类来定义数据结构，自动校验输入数据是否符合类型要求。比如定义 `age: int`，传入字符串就会报错。在 LangChain 里用它，是为了告诉 LLM "你的输出必须长什么样"——Pydantic 自动生成 JSON Schema，LangChain 把它塞进提示词里让模型遵守，比手写"请输出 JSON 格式，字段有 xxx"靠谱得多。

```python
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser

class MovieReview(BaseModel):
    title: str = Field(description="电影名称")
    rating: float = Field(description="评分，1-10 分")
    summary: str = Field(description="一句话评价")

parser = JsonOutputParser(pydantic_object=MovieReview)
```

这里定义了一个 `MovieReview` 类，描述期望的输出结构。`Field(description=...)` 中的 description 不是给 Python 用的，是给模型看的——LangChain 会把它转化成提示词，告诉模型每个字段该填什么。

关键一步：把格式说明注入到提示词模板中。

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个电影评论家。{format_instructions}"),
    ("human", "请评价电影：{movie}"),
])

# partial() 把 format_instructions 提前注入模板
# 这样 invoke 时不需要每次都传这个参数
prompt = prompt.partial(format_instructions=parser.get_format_instructions())
```

`parser.get_format_instructions()` 会生成一段文本，大致是"请按以下 JSON 格式输出：{"title": string, "rating": number, ...}"。`prompt.partial()` 把这段文本提前注入到模板的 `{format_instructions}` 占位符中，之后每次 `invoke` 只需要传 `movie` 就行。

完整链路：

```python
chain = prompt | llm | parser

result = chain.invoke({"movie": "星际穿越"})
print(result)
```

输出是一个 Python 字典：

```python
{'title': '星际穿越', 'rating': 9.0, 'summary': '硬核科幻与人文情感完美融合的史诗级太空之旅'}
```

注意最后的 `parser` 不是 `StrOutputParser` 而是 `JsonOutputParser`——它接收模型输出，解析成字典。`parser` 和 `llm` 之间用 `|` 连接，数据自动流转。

常用的输出解析器：

| 解析器 | 输出类型 | 适用场景 |
|--------|----------|----------|
| `StrOutputParser` | str | 只需要纯文本回复 |
| `JsonOutputParser` | dict | 需要 JSON 格式的结构化数据 |
| `PydanticOutputParser` | Pydantic Model | 同上，但返回带类型验证的对象 |

`JsonOutputParser` 和 `PydanticOutputParser` 功能类似，区别是前者返回字典，后者返回 Pydantic 模型实例。大部分场景用 `JsonOutputParser` 就够了。

## RunnablePassthrough：在链中添加自定义处理

LCEL 链中有时需要对输入数据做一些预处理。比如用户只传了 `topic` 和 `question`，但提示词模板需要一个 `context` 字段来提供背景信息。`RunnablePassthrough.assign()` 可以在不改变原始输入的情况下，动态添加新字段：

```python
from langchain_core.runnables import RunnablePassthrough

enriched = RunnablePassthrough.assign(
    context=lambda x: f"用户正在问关于「{x['topic']}」的问题",
)
```

`assign` 接收一个字典，值是函数（或 Runnable）。函数的参数 `x` 是整个输入字典，返回值会成为新字段的值。原始输入的所有字段会被原样保留。

把它加到链中：

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "{context}。请简洁回答。"),
    ("human", "{question}"),
])

chain = enriched | prompt | llm | StrOutputParser()

result = chain.invoke({
    "topic": "Python",
    "question": "列表推导式和 map 函数哪个更好？",
})
```

数据流经 `enriched` 时，输入字典从 `{"topic": "Python", "question": "..."}` 变成了 `{"topic": "Python", "question": "...", "context": "用户正在问关于「Python」的问题"}`。后面的 `prompt` 就能使用 `context` 变量了。

## RunnableLambda：包装任意函数

`RunnablePassthrough.assign()` 适合给输入添加字段。如果你需要在链中做更通用的处理（比如打印日志、格式转换），用 `RunnableLambda` 把任意函数包装成 Runnable：

```python
from langchain_core.runnables import RunnableLambda

def print_and_pass(x):
    print(f"[调试] 当前数据: {x}")
    return x

debug = RunnableLambda(print_and_pass)
chain = debug | prompt | llm | StrOutputParser()
```

`RunnableLambda` 接收一个函数，把它变成 LCEL 链中的一个节点。函数接收上游输出，返回值传给下游。任何 `callable` 都可以。

## RunnableParallel：并行执行多条链

有时候你想让模型同时做几件事，比如用中文和英文分别回答同一个问题。用 `RunnableParallel` 可以让多条链并行运行，结果合并成一个字典：

```python
from langchain_core.runnables import RunnableParallel

prompt_cn = ChatPromptTemplate.from_messages([
    ("system", "用中文回答，不超过一句话。"),
    ("human", "{question}"),
])

prompt_en = ChatPromptTemplate.from_messages([
    ("system", "Answer in English, one sentence only."),
    ("human", "{question}"),
])

parallel_chain = RunnableParallel(
    chinese=prompt_cn | llm | StrOutputParser(),
    english=prompt_en | llm | StrOutputParser(),
)

result = parallel_chain.invoke({"question": "什么是机器学习？"})
print(result["chinese"])
print(result["english"])
```

`RunnableParallel` 的参数是键值对，键是自定义的名字，值是 Runnable。所有 Runnable 同时执行（共享同一个输入），结果按键名汇总成字典：

```python
{
    "chinese": "机器学习是一种让计算机通过数据自动学习和改进算法，无需明确编程的技术。",
    "english": "Machine learning is a subset of artificial intelligence that enables systems to automatically learn and improve from experience without being explicitly programmed."
}
```

## RunnableBranch：条件分支

链中有时需要根据输入内容走不同的处理路径。比如用户问的是数学问题，就交给数学链；问的是翻译问题，就交给翻译链。`RunnableBranch` 根据条件自动选择执行哪条分支：

```python
from langchain_core.runnables import RunnableBranch

math_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个数学老师，只回答数学问题。"),
    ("human", "{question}"),
])

translate_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个翻译官，只做翻译。"),
    ("human", "{question}"),
])

general_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个通用助手。"),
    ("human", "{question}"),
])

def is_math(x):
    keywords = ["计算", "加", "减", "乘", "除", "数学", "等于"]
    return any(k in x["question"] for k in keywords)

def is_translate(x):
    keywords = ["翻译", "translate", "英文", "中文"]
    return any(k in x["question"] for k in keywords)

branch = RunnableBranch(
    (is_math, math_prompt | llm | StrOutputParser()),
    (is_translate, translate_prompt | llm | StrOutputParser()),
    general_prompt | llm | StrOutputParser(),  # 默认分支，前面都不匹配时执行
)

result = branch.invoke({"question": "计算 123 乘以 456"})
```

`RunnableBranch` 的参数是一系列 `(条件函数, Runnable)` 元组，最后一个参数不加条件，作为默认分支。执行时从上到下依次判断条件，第一个返回 `True` 的分支被执行。

## Runnable 类型一览

本文介绍了四种 Runnable 组件，加上之前的 `ChatPromptTemplate` 和输出解析器，你已经掌握了 LCEL 的核心构建块：

| Runnable | 作用 | 典型用法 |
|----------|------|----------|
| `RunnablePassthrough` | 原样传递输入，可用 `.assign()` 添加字段 | 在链中对输入做预处理 |
| `RunnableLambda` | 包装任意函数为 Runnable | 打印日志、格式转换、自定义逻辑 |
| `RunnableParallel` | 并行执行多个 Runnable，结果合并为字典 | 同时做多件事（翻译、摘要、分类） |
| `RunnableBranch` | 条件分支，根据输入选择不同的 Runnable | 根据问题类型走不同处理路径 |

这些组件都可以用 `|` 互相连接，组合出复杂的处理流程，同时保持代码的可读性。

## 综合示例：把所有组件串起来

把本文学到的组件组合成一个完整的链：

```python
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableBranch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field

# 1. 用 assign 给输入添加 context 字段
enriched = RunnablePassthrough.assign(
    context=lambda x: f"用户在问关于「{x['topic']}」的问题",
)

# 2. 定义主链
prompt = ChatPromptTemplate.from_messages([
    ("system", "{context}。用中文回答，不超过三句话。"),
    ("human", "{question}"),
])
main_chain = enriched | prompt | llm | StrOutputParser()

# 3. 并行执行：主链回答 + 翻译
full_chain = RunnableParallel(
    answer=main_chain,
    question_length=lambda x: len(x["question"]),
)

result = full_chain.invoke({
    "topic": "Python",
    "question": "列表推导式和 map 函数哪个更好？",
})

# 4. 条件分支：根据问题类型选择不同的处理链
def is_math(x):
    keywords = ["计算", "加", "减", "乘", "除", "数学", "等于"]
    return any(k in x["question"] for k in keywords)

def is_translate(x):
    keywords = ["翻译", "translate", "英文", "中文"]
    return any(k in x["question"] for k in keywords)

math_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个数学老师，只回答数学问题，给出计算过程。"),
    ("human", "{question}"),
])
translate_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个翻译官，只做翻译，直接给出翻译结果。"),
    ("human", "{question}"),
])
general_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个通用助手，简洁回答。"),
    ("human", "{question}"),
])

branch = RunnableBranch(
    (is_math, math_prompt | llm | StrOutputParser()),
    (is_translate, translate_prompt | llm | StrOutputParser()),
    general_prompt | llm | StrOutputParser(),  # 默认分支
)

result = branch.invoke({"question": "计算 123 乘以 456"})
```

这条链做了四件事：
- 用 `assign` 自动生成上下文信息
- 用提示词模板生成结构化的 prompt
- 用 `RunnableParallel` 同时产出回答和问题长度统计
- 用 `RunnableBranch` 根据问题类型（数学/翻译/通用）自动选择处理链

## 小结

- **ChatPromptTemplate.from_messages** 支持多种角色（system/human/ai），模板中用 `{变量名}` 做占位
- **MessagesPlaceholder** 在模板中预留一个位置，调用时动态注入一组消息，是实现多轮对话的关键
- **JsonOutputParser + Pydantic** 让模型输出结构化 JSON，`get_format_instructions()` 生成格式说明文本，用 `.partial()` 注入模板
- **RunnablePassthrough.assign()** 给输入字典添加新字段，不改变原始数据
- **RunnableLambda** 把任意函数包装成链中的节点
- **RunnableParallel** 并行执行多条链，结果汇总成字典
- **RunnableBranch** 条件分支，根据输入自动选择不同的处理链

## 完整代码

把下面代码保存为 `step2_lcel_prompts.py`，并和前面的 `config.py` 放在同一个目录下运行：

```python
"""
Step 2: LCEL 与 Prompt Template 深入

本文件演示：
- ChatPromptTemplate 的多种用法（system/human/ai 角色）
- MessagesPlaceholder 注入对话历史
- JsonOutputParser 配合 Pydantic 模型输出结构化数据
- RunnablePassthrough.assign() 给输入添加字段
- RunnableParallel 并行执行多条链
- RunnableBranch 条件分支
"""

from pydantic import BaseModel, Field
from langchain_deepseek import ChatDeepSeek
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel, RunnableBranch
from langchain_core.messages import HumanMessage, AIMessage

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

def main():
    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0,
    )

    # ============================================================
    # Demo 1: ChatPromptTemplate.from_messages — 多角色消息模板
    # ============================================================
    print("=" * 50)
    print("Demo 1: ChatPromptTemplate 多角色模板")
    print("=" * 50)

    # from_messages 支持三种角色：system、human、ai
    # 可以在模板中混合多种角色，构建多轮对话的 prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个{style}风格的翻译官。"),
        ("human", "请把以下内容翻译成英文：{text}"),
    ])

    # .invoke() 只做模板填充，不调用模型
    # 返回的是 ChatPromptValue，可以 .to_messages() 查看生成的消息列表
    formatted = prompt.invoke({
        "style": "幽默",
        "text": "今天天气真好",
    })
    print(f"\n[模板填充结果] 类型: {type(formatted).__name__}")
    for msg in formatted.to_messages():
        print(f"  {msg.type}: {msg.content}")

    # ============================================================
    # Demo 2: MessagesPlaceholder — 注入对话历史
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 2: MessagesPlaceholder 注入对话历史")
    print("=" * 50)

    # MessagesPlaceholder("history") 会在 invoke 时被一组消息替换
    # 这在实现多轮对话时非常有用
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个有帮助的AI助手。"),
        MessagesPlaceholder("history"),
        ("human", "{input}"),
    ])

    # 模拟之前的对话历史
    history = [
        HumanMessage(content="LangChain 是什么？"),
        AIMessage(content="LangChain 是一个用于构建 LLM 应用的框架。"),
    ]

    formatted = prompt.invoke({
        "history": history,
        "input": "它有哪些核心模块？",
    })
    print(f"\n[带历史的消息列表]")
    for msg in formatted.to_messages():
        print(f"  {msg.type}: {msg.content}")

    # ============================================================
    # Demo 3: 完整 LCEL 链 — prompt | llm | parser
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 3: 完整 LCEL 链 prompt | llm | StrOutputParser")
    print("=" * 50)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是 Python 专家，回答要简洁，不超过 3 句话。"),
        ("human", "{question}"),
    ])
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({"question": "Python 的装饰器是什么？"})
    print(f"\n{result}")

    # ============================================================
    # Demo 4: JsonOutputParser + Pydantic — 结构化输出
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 4: JsonOutputParser + Pydantic 结构化输出")
    print("=" * 50)

    # 定义一个 Pydantic 模型来描述期望的输出结构
    class MovieReview(BaseModel):
        title: str = Field(description="电影名称")
        rating: float = Field(description="评分，1-10 分")
        summary: str = Field(description="一句话评价")

    # JsonOutputParser 会把 LLM 的输出解析成字典
    # get_format_instructions() 返回一段提示词，告诉模型按什么格式输出
    parser = JsonOutputParser(pydantic_object=MovieReview)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个电影评论家。{format_instructions}"),
        ("human", "请评价电影：{movie}"),
    ])

    # 用 partial 把 format_instructions 提前注入模板
    # 这样 invoke 时不需要每次都传 format_instructions
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    result = chain.invoke({"movie": "星际穿越"})
    print(f"\n[解析结果] 类型: {type(result).__name__}")
    print(f"  电影: {result['title']}")
    print(f"  评分: {result['rating']}")
    print(f"  评价: {result['summary']}")

    # ============================================================
    # Demo 5: RunnablePassthrough.assign() — 给输入添加字段
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 5: RunnablePassthrough.assign() 添加字段")
    print("=" * 50)

    # RunnablePassthrough.assign() 接收一个字典，
    # 字典的值可以是函数或 Runnable，用来计算新字段的值
    # 原始输入会原样保留，新字段追加进去
    enriched = RunnablePassthrough.assign(
        context=lambda x: f"用户正在问关于「{x['topic']}」的问题",
    )

    # 把 enrich 和链串起来
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{context}。请简洁回答。"),
        ("human", "{question}"),
    ])
    chain = enriched | prompt | llm | StrOutputParser()

    result = chain.invoke({
        "topic": "Python",
        "question": "列表推导式和 map 函数哪个更好？",
    })
    print(f"\n{result}")

    # ============================================================
    # Demo 6: RunnableParallel — 并行执行多条链
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 6: RunnableParallel 并行执行")
    print("=" * 50)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个有帮助的助手，用一句话回答。"),
        ("human", "{question}"),
    ])
    chain = prompt | llm | StrOutputParser()

    # RunnableParallel 同时运行多个 Runnable，各自独立，结果合并成一个字典
    # 这里的两条链共享同一个 llm，但 prompt 不同
    prompt_cn = ChatPromptTemplate.from_messages([
        ("system", "用中文回答，不超过一句话。"),
        ("human", "{question}"),
    ])
    prompt_en = ChatPromptTemplate.from_messages([
        ("system", "Answer in English, one sentence only."),
        ("human", "{question}"),
    ])

    parallel_chain = RunnableParallel(
        chinese=prompt_cn | llm | StrOutputParser(),
        english=prompt_en | llm | StrOutputParser(),
    )

    result = parallel_chain.invoke({"question": "什么是机器学习？"})
    print(f"\n[中文回答] {result['chinese']}")
    print(f"[英文回答] {result['english']}")

    # ============================================================
    # Demo 7: RunnableBranch — 条件分支
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 7: RunnableBranch 条件分支")
    print("=" * 50)

    # RunnableBranch 根据输入内容自动选择不同的处理链
    # 参数是一系列 (条件函数, Runnable) 元组，最后一个不加条件作为默认分支
    math_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个数学老师，只回答数学问题，给出计算过程。"),
        ("human", "{question}"),
    ])

    translate_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个翻译官，只做翻译，直接给出翻译结果。"),
        ("human", "{question}"),
    ])

    general_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个通用助手，简洁回答。"),
        ("human", "{question}"),
    ])

    def is_math(x):
        keywords = ["计算", "加", "减", "乘", "除", "数学", "等于"]
        return any(k in x["question"] for k in keywords)

    def is_translate(x):
        keywords = ["翻译", "translate", "英文", "中文"]
        return any(k in x["question"] for k in keywords)

    branch = RunnableBranch(
        (is_math, math_prompt | llm | StrOutputParser()),
        (is_translate, translate_prompt | llm | StrOutputParser()),
        general_prompt | llm | StrOutputParser(),  # 默认分支
    )

    # 测试数学问题
    result1 = branch.invoke({"question": "计算 123 乘以 456"})
    print(f"\n[数学问题] 计算 123 乘以 456")
    print(f"  回答: {result1}")

    # 测试翻译问题
    result2 = branch.invoke({"question": "把「今天天气真好」翻译成英文"})
    print(f"\n[翻译问题] 把「今天天气真好」翻译成英文")
    print(f"  回答: {result2}")

    # 测试通用问题
    result3 = branch.invoke({"question": "什么是 Python 的列表推导式？"})
    print(f"\n[通用问题] 什么是 Python 的列表推导式？")
    print(f"  回答: {result3}")

if __name__ == "__main__":
    main()
```
