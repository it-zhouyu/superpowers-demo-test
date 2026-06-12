> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 什么是 AI Agent

当你用 ChatGPT 或 DeepSeek 聊天时，模型只能基于训练数据回答问题。你问"北京今天天气怎么样"，它的回答要么是编的，要么直接说"我无法获取实时数据"。这是大语言模型（LLM，Large Language Model）的根本局限——它是一个文本生成模型，没有能力与外部世界交互。

AI Agent（人工智能代理）就是来解决这个问题的。Agent 这个词来自拉丁语"agens"，意思是"正在行动的人或事物"。在 AI 领域，Agent 指的是一种能够**自主感知环境、做出决策、执行动作**的系统。它不再只是"说话"，而是能"做事"。

一个 LLM 和一个 Agent 的核心区别：

- **LLM**：接收文本输入，返回文本输出，无法执行任何实际操作
- **Agent**：在 LLM 的基础上增加了工具调用能力，能自主决定是否需要调用外部工具、调用哪个工具、传什么参数，并根据工具返回的结果继续推理或生成最终回答

也就是说，Agent = LLM + 工具 + 自主决策循环

## Agent 的核心架构

一个完整的 Agent 系统通常包含四个核心模块：

### 感知（Perception）

感知是 Agent 获取信息的方式。最基础的感知是接收用户的文本输入。更复杂的 Agent 还能感知对话历史、文件内容、数据库状态、API 返回结果等。感知模块决定了 Agent 能"看到"什么信息，这些信息是后续决策的基础。

### 规划（Planning）

规划是 Agent 的"大脑"，由 LLM 承担。它负责分析感知到的信息，决定下一步做什么。规划可能是简单的一次性判断（比如"需要查天气"），也可能是复杂的多步推理（比如"先查天气，再根据天气推荐穿搭，最后查找附近的服装店"）。规划的质量直接取决于底层 LLM 的推理能力。

### 行动（Action）

行动是 Agent 对外部世界产生实际影响的方式。Agent 通过调用工具（Tool）来执行行动。工具可以是任意可编程的功能：调用天气 API、读写文件、发送邮件、执行数据库查询、运行代码等。每个工具都有明确的名字、参数定义和功能描述，LLM 根据这些描述来决定调用哪个工具。

### 记忆（Memory）

记忆是 Agent 保存和检索历史信息的能力。记忆分为两种：

- **短期记忆**：当前对话的上下文，即对话历史。LLM 在每次调用时都会收到之前的对话记录，这是最基础的记忆形式
- **长期记忆**：跨对话持久化存储的信息，比如用户的偏好、之前任务的结果等。长期记忆通常需要借助外部存储（如向量数据库、文件系统）来实现

## 工具调用：Agent 如何与外部世界交互

工具调用（Tool Calling）是 Agent 区别于普通 LLM 的关键能力。理解工具调用，就理解了 Agent 的核心工作原理。

### 什么是工具

工具就是一个普通的函数，它有明确的功能、输入参数和输出结果。比如一个查询天气的工具，接收城市名作为参数，返回该城市的天气信息。关键是，这个函数不需要 LLM 自己实现，它由开发者预先定义好，LLM 只负责决定何时调用、传什么参数。

### 工具调用的执行流程

工具调用的完整流程分四步：

1. **用户提问**：用户发送一个需要外部数据或操作才能回答的问题
2. **LLM 决策**：LLM 分析问题，判断是否需要调用工具。如果需要，生成一个工具调用请求，包含工具名称和参数
3. **执行工具**：开发者（或框架）根据 LLM 的请求调用对应的函数，获取结果
4. **LLM 生成回答**：把工具执行结果返回给 LLM，LLM 基于这些结果生成最终回复

这个过程用代码表示就是：

```python
# 第1步：用户提问
user_message = "北京今天天气怎么样"

# 第2步：LLM 判断需要调用工具，生成工具调用请求
# LLM 返回的不是文本回答，而是类似这样的结构：
tool_call = {
    "name": "get_weather",
    "arguments": {"city": "北京"}
}

# 第3步：执行工具函数
weather_result = get_weather("北京")
# 返回：{"city": "北京", "weather": "晴天，18°C"}

# 第4步：把结果喂回 LLM，生成最终回答
# LLM 收到工具结果后回答："北京今天天气晴朗，气温18度，适合户外活动"
```

注意第2步，LLM 并不直接执行函数，它只是输出了一个"我想调用这个函数"的请求。实际执行函数的是你的代码。这个设计很重要——LLM 是决策者，不是执行者。

### 一个关键细节

LLM 怎么知道有哪些工具可用？答案是开发者在调用 LLM 时，会把所有可用工具的描述信息一起传过去。每个工具的描述包含三部分：

- **工具名称**：函数名，比如 `get_weather`
- **参数定义**：每个参数的名称、类型和描述，比如 `city: str - 要查询天气的城市名称`
- **功能描述**：一段简短的文字说明这个工具做什么，比如 `查询指定城市的天气信息`

LLM 根据这些描述信息来判断：用户的问题是否需要调用工具？调用哪个工具？传什么参数？

## Agent 的运行循环

理解了工具调用，再来看 Agent 的运行循环就清楚了。Agent 不是调用一次 LLM 就结束，而是一个**循环往复**的过程。最常见的循环模式是 ReAct（Reasoning + Acting）。

### ReAct 模式

ReAct 模式把 Agent 的每一步分为两种类型：

- **Reasoning（推理）**：LLM 分析当前情况，思考下一步该做什么
- **Acting（行动）**：根据推理结果调用工具，获取新信息

一个典型的 ReAct 执行过程：

```
用户：帮我查一下北京天气，如果下雨就推荐室内活动，否则推荐户外活动

第1轮 - Reasoning：用户想知道北京天气，我需要先调用天气工具
第1轮 - Acting：调用 get_weather("北京") → "晴天，18°C"

第2轮 - Reasoning：北京天气是晴天，应该推荐户外活动
第2轮 - Acting：直接生成回答（不需要再调用工具）

最终回答：北京今天天气晴朗，气温18度，推荐去公园散步、骑行或爬山等户外活动
```

这个循环会一直执行，直到 LLM 认为已经收集到足够的信息，可以生成最终回答为止。这就是为什么 Agent 能处理复杂的多步骤任务——它在循环中逐步收集信息、逐步推理，直到得出结论。

### 循环什么时候停止

Agent 的循环不是无限运行的，它有明确的终止条件：

- LLM 不再请求调用工具，直接生成文本回答——这说明它认为信息已经足够
- 达到预设的最大循环次数——防止 LLM 陷入死循环
- 遇到错误且无法恢复——比如工具调用失败且没有备选方案

## 完整代码示例

下面用 Python 和 OpenAI SDK 实现一个最小但完整的 Agent。这个 Agent 拥有两个工具：查询天气和查询时间。它能根据用户的问题自主决定调用哪个工具，并在一个循环中完成多步推理。

先安装依赖：

```bash
pip install openai
```

完整代码：

```python
import json
from datetime import datetime, timezone, timedelta
from openai import OpenAI

# ==================== 工具定义 ====================

def get_weather(city: str) -> str:
    """查询指定城市的天气信息"""
    mock_data = {
        "北京": "晴天，气温 18°C，空气质量良好",
        "上海": "多云，气温 22°C，有轻微雾霾",
        "深圳": "阴天，气温 26°C，可能有小雨",
    }
    weather = mock_data.get(city, f"暂无{city}的天气数据")
    return json.dumps({"city": city, "weather": weather}, ensure_ascii=False)


def get_time(city: str, timezone_str: str = "Asia/Shanghai") -> str:
    """查询指定城市的当前时间"""
    tz_map = {
        "Asia/Shanghai": timedelta(hours=8),
        "America/New_York": timedelta(hours=-4),
    }
    offset = tz_map.get(timezone_str, timedelta(hours=8))
    tz = timezone(offset)
    now = datetime.now(tz)
    return json.dumps({
        "city": city,
        "timezone": timezone_str,
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


# ==================== 工具描述 ====================

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "要查询天气的城市名称，例如：北京、上海",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "查询指定城市的当前时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "要查询时间的城市名称",
                    },
                    "timezone_str": {
                        "type": "string",
                        "description": "时区标识符，例如 Asia/Shanghai",
                    },
                },
                "required": ["city"],
            },
        },
    },
]

# 工具名称到函数的映射
tool_map = {
    "get_weather": get_weather,
    "get_time": get_time,
}

# ==================== Agent 核心 ====================

client = OpenAI(
    api_key="sk-xxx",          # 替换为你的 API Key
    base_url="https://api.deepseek.com",  # 替换为你的 API 地址
)


def run_agent(user_input: str, max_steps: int = 5) -> str:
    """
    运行 Agent 循环，直到获得最终回答或达到最大步数

    Args:
        user_input: 用户的输入文本
        max_steps: 最大循环次数，防止无限循环

    Returns:
        Agent 的最终回答文本
    """
    messages = [
        {"role": "system", "content": "你是一个有用的助手，能够查询天气和时间信息。请用中文回答。"},
        {"role": "user", "content": user_input},
    ]

    for step in range(max_steps):
        print(f"--- 第 {step + 1} 轮 ---")

        # 调用 LLM，传入对话历史和工具描述
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=tools,
        )

        message = response.choices[0].message

        # 检查 LLM 是否请求调用工具
        if message.tool_calls:
            # 把 LLM 的回复（包含工具调用请求）加入对话历史
            messages.append(message)

            # 逐个执行 LLM 请求的工具
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"  调用工具: {function_name}({function_args})")

                # 执行工具函数
                function_result = tool_map[function_name](**function_args)

                print(f"  工具返回: {function_result}")

                # 把工具执行结果加入对话历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_result,
                })
        else:
            # LLM 没有请求调用工具，说明它已经有了最终回答
            print("--- Agent 完成 ---")
            return message.content

    return "达到最大循环次数，Agent 未能完成任务"


# ==================== 运行示例 ====================

if __name__ == "__main__":
    # 测试1：单工具调用
    result = run_agent("北京今天天气怎么样？")
    print(f"\n回答：{result}\n")

    # 测试2：多步推理
    result = run_agent("帮我查一下北京和上海现在的天气和时间")
    print(f"\n回答：{result}\n")
```

运行结果（示例）：

```
--- 第 1 轮 ---
  调用工具: get_weather({'city': '北京'})
  工具返回: {"city": "北京", "weather": "晴天，气温 18°C，空气质量良好"}
--- 第 2 轮 ---
--- Agent 完成 ---

回答：北京今天天气晴朗，气温18°C，空气质量良好，非常适合户外活动。
```

代码逐段说明：

- **工具定义**（`get_weather`、`get_time`）：两个普通的 Python 函数，每个函数有清晰的类型注解和 docstring。本例用 mock 数据模拟，实际项目中替换为真实的 API 调用
- **工具描述**（`tools` 列表）：用 JSON Schema 格式描述每个工具的名称、功能和参数。LLM 根据这份描述来判断何时调用哪个工具
- **`run_agent` 函数**：Agent 的核心循环。每次循环调用 LLM，如果 LLM 返回了工具调用请求就执行工具并把结果喂回去，如果 LLM 直接返回了文本回答就结束循环
- **`messages` 列表**：对话历史的载体。每一步的操作（用户提问、LLM 的工具调用请求、工具返回结果）都追加到这个列表中，LLM 在下一轮调用时能看到完整的上下文

这段代码虽然简单，但它包含了 Agent 的全部核心要素：LLM 推理、工具调用、循环执行、对话历史管理。所有的 Agent 框架（LangChain、DeepAgents、CrewAI 等）都是在这个基础模式上做封装和扩展
