> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="100" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## LLM 生成文本的本质

LLM（Large Language Model，大语言模型）生成文本的方式，用一句话概括：**根据前面的文字，猜下一个最可能出现的词**。

你输入"今天天气真"，它算出下一个最可能的词是"好"，于是输出"好"。
然后把"今天天气真好"作为新的输入，继续猜下一个词。
一个字一个字地往外蹦，直到生成结束标记。

## Chat Completion API 的核心结构

前面我们用到的 `client.chat.completions.create()` 就是 Chat Completion API。它的核心参数有三个：

```python
response = client.chat.completions.create(
    model="deepseek-v4-flash",   # 用哪个模型
    messages=messages,      # 对话历史
    temperature=0.7         # 生成参数（可选）
)
```

其中 `messages` 是最重要的参数——它决定了 LLM 看到什么信息，也就决定了 LLM 会生成什么回应。

## 消息与角色

`messages` 是一个列表，每条消息有两个字段：`role`（角色）和 `content`（内容）。

四种角色：
- `system` — 系统指令，定义 AI 的行为规则
- `user` — 用户输入
- `assistant` — AI 的回复
- `tool` — 工具执行结果


一个完整的对话流程：

```python
messages = [
    # 系统指令：告诉 AI "你是谁、该怎么回答"
    {"role": "system", "content": "你是一个 Python 编程助手，回答要简洁，附带代码示例"},

    # 第一轮对话
    {"role": "user", "content": "怎么读取 JSON 文件？"},
    {"role": "assistant", "content": "用 json.load()：\n```python\nimport json\nwith open('data.json') as f:\n    data = json.load(f)\n```"},

    # 第二轮对话
    {"role": "user", "content": "如果文件不存在怎么办？"},
    {"role": "assistant", "content": "用 try-except 捕获 FileNotFoundError：\n```python\ntry:\n    with open('data.json') as f:\n        data = json.load(f)\nexcept FileNotFoundError:\n    data = {}\n```"},
]
```

**System Prompt 是 Agent 行为的控制器**，改一行 system prompt，AI 的回答风格就可能完全不同：

```python
# 改成旅游助手
{"role": "system", "content": "你是一个旅游规划助手，根据用户的需求推荐景点和行程"}

# 改成严格的数据分析师
{"role": "system", "content": "你是一个数据分析助手。回答必须基于数据，不知道就说不知道，不要编造"}
```

## Token 与上下文窗口

### 什么是 Token

Token 是 LLM 处理文本的最小单位。一个 Token 不等于一个字符，也不等于一个单词。大致规则：

- 常见英文单词 ≈ 1 个 Token（如 "hello" = 1 token）
- 常见中文词 ≈ 1-2 个 Token（如 "你好" ≈ 1 token）
- 生僻词、专业术语会被拆成多个 Token

可以用 OpenAI 的 `tiktoken` 库来近似计数（DeepSeek 等非 OpenAI 模型没有对应的 tiktoken 编码器，用 `cl100k_base` 做近似即可）：

```python
import tiktoken

# DeepSeek 等非 OpenAI 模型用 cl100k_base 近似
encoding = tiktoken.get_encoding("cl100k_base")

text = "你好，我是一个 AI 助手"
tokens = encoding.encode(text)
print(f"文本: {text}")
print(f"Token 数: {len(tokens)}")
print(f"Token 列表: {tokens}")
```

输出：

```
文本: 你好，我是一个 AI 助手
Token 数: 10
Token 列表: [57668, 53901, 3922, 37046, 21043, 48044, 15592, 55699, 102, 46034]
```

### 上下文窗口

每个模型有一个**上下文窗口**（Context Window），单次请求中所有 messages 的 Token 总数不能超过这个窗口大小。

常见模型的上下文窗口：

| 模型 | 上下文窗口 | 大约能装多少字 |
|------|-----------|---------------|
| GPT-5.5 | 1M | 约 75 万字中文 |
| Claude Opus 4.7 | 200K | 约 15 万字中文 |
| DeepSeek-V4 | 1M | 约 75 万字中文 |

随着对话轮次的增加，messages 列表会越来越长，后续就需要用到**上下文压缩**（后续会讲到），通过压缩对话内容，从而避免超出窗口限制。

### Token 费用

API 调用按 Token 计费，输入（messages）和输出（response）分别计价，所以对话内容越多，消耗的 Token 也越多，成本也就会更高。

[model.dev](https://models.dev/)这个完整可以看到很多模型相关的信息。

## 生成参数

`temperature` 是最常用的生成参数，控制 LLM 输出的随机性：

```python
# temperature = 0：每次都选最可能的词，输出稳定、确定
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    temperature=0    # 适合：代码生成、数据提取、分类
)

# temperature = 0.7：有一定随机性，输出自然、多样（默认值）
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    temperature=0.7  # 适合：对话、写作、翻译
)

# temperature = 1.5：高度随机，输出发散、创意强
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    temperature=1.5  # 适合：头脑风暴、创意写作
)
```

从底层原理看，temperature 改变的是"选下一个词"时的概率分布，简单理解就是：temperature=0 时总是选概率最高的词，temperature 越高，低概率的词被选中的机会越大。

另一个参数 `max_tokens` 控制生成的最大长度：

```python
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    max_tokens=100  # 最多生成 100 个 Token
)
```

注意：`max_tokens` 限制的是**输出**的 Token 数，不影响输入。如果设得太小，LLM 的回答会被截断。

## 完善 Agent 的对话循环

把前面学的知识用上，改进上一篇的对话程序：

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="your-api-key"
)

SYSTEM_PROMPT = """你是一个智能助手。回答要简洁直接。
如果用户的问题你不确定，就说"我不确定"，不要编造答案。"""

messages = [{"role": "system", "content": SYSTEM_PROMPT}]

print("Agent 已启动，输入消息开始对话，输入 exit 退出\n")

while True:
    user_input = input("你: ").strip()
    if not user_input or user_input.lower() in ("exit", "quit"):
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        temperature=0.7
    )

    assistant_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_message})

    print(f"AI: {assistant_message}\n")

    # 显示本次消耗的 Token 数
    usage = response.usage
    print(f"[本次消耗: 输入 {usage.prompt_tokens} + 输出 {usage.completion_tokens} = {usage.total_tokens} tokens]")
    print(f"[对话历史: {len(messages)} 条消息]\n")
```

运行：

```
Agent 已启动，输入消息开始对话，输入 exit 退出

你: Python 怎么反转字符串
AI: 使用切片：`s[::-1]`
[本次消耗: 输入 35 + 输出 49 = 84 tokens]
[对话历史: 3 条消息]

你: 列表也能这样反转吗
AI: 是的。`my_list[::-1]` 会返回反转后的新列表。但注意：字符串不可变，而列表可原地反转：`my_list.reverse()`。
[本次消耗: 输入 53 + 输出 170 = 223 tokens]
[对话历史: 5 条消息]
```

注意第二次请求消耗的输入 Token 比第一次多——因为 `messages` 列表变长了，包含了之前的对话历史，对话越多，每次请求的输入 Token 越多，这就是上下文窗口压力的来源。

## 完整代码

下面是整合了本文核心知识点的完整对话程序：

```python
# 运行方式：pip install openai
# 将 your-api-key 替换为你的 DeepSeek API Key，保存为 chat_agent.py 后运行：python chat_agent.py

from openai import OpenAI

# 初始化客户端，连接 DeepSeek API
client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="your-api-key"
)

# System Prompt — 定义 AI 的角色和行为规则
SYSTEM_PROMPT = """你是一个智能助手。回答要简洁直接。
如果用户的问题你不确定，就说"我不确定"，不要编造答案。"""

# 初始化 messages 列表，第一条是 system 消息
messages = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

print("=== AI Agent 对话程序 ===")
print("输入消息开始对话，输入 exit 或 quit 退出")
print("-" * 40)
print()

# 对话主循环
while True:
    user_input = input("你: ").strip()

    # 输入为空或输入 exit/quit 则退出循环
    if not user_input or user_input.lower() in ("exit", "quit"):
        print("再见！")
        break

    # 将用户消息添加到对话历史
    messages.append({"role": "user", "content": user_input})

    # 调用 Chat Completion API，传入完整对话历史
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        temperature=0.7
    )

    # 提取 AI 回复并添加到对话历史
    assistant_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_message})

    print(f"AI: {assistant_message}\n")

    # 显示本次请求的 Token 消耗
    usage = response.usage
    print(f"[本次消耗: 输入 {usage.prompt_tokens} + 输出 {usage.completion_tokens} = {usage.total_tokens} tokens]")
    print(f"[对话历史: {len(messages)} 条消息]\n")
```

