> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 从 LangGraph 到 DeepAgents

学完 LangGraph 之后，你可能会想：每次都要自己定义 State、自己连边、自己处理工具调用逻辑……写一个像样的 Agent 怎么这么麻烦？

这不是你的问题。LangGraph 的定位是"Agent 底层运行时"，它提供 State、Node、Edge、条件路由、检查点等基础能力，但不会默认替你配置规划、文件系统、子 Agent、技能系统这些上层能力。

DeepAgents 就是来补这一层的。它是 LangChain AI 团队推出的开箱即用 Agent 框架，底层用 LangGraph 实现，但把规划、文件管理、子 Agent、技能系统、上下文管理这些能力全部封装好了。它提供的是一个能直接运行的 Agent Harness（代理框架），而不是只提供底层编排 API。

本系列从这篇文章开始，带你从创建第一个 Deep Agent 到掌握生产部署的完整链路。

## 安装和第一个 Agent

### 准备环境

创建项目目录，安装依赖：

```bash
mkdir deepagents-demo && cd deepagents-demo
pip install deepagents langchain-deepseek python-dotenv
```

DeepAgents 版本要求 >= 0.6.4。本系列所有示例基于此版本。

然后创建 `.env` 文件，配置 API Key：

```
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

再创建 `config.py`，把配置集中管理，后面的所有示例都复用这个文件：

```python
import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
```

这里用 `deepseek-v4-flash` 作为默认模型，对应 DeepSeek V4 Flash。`base_url` 默认指向 DeepSeek 官方 API 地址。如果你用的是其他 OpenAI 兼容的服务（如 OpenRouter），改一下 `base_url` 就行。

### 最简单的 Agent

创建 `step1_create_agent.py`，写一个最简单的 Deep Agent：

```python
from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

agent = create_deep_agent(
    model=llm,
    system_prompt="你是一个友好的中文助手，请用简洁的中文回答问题。",
)

result = agent.invoke({"messages": "你好，请用一句话介绍一下你自己"})
print(result["messages"][-1].content)
```

运行它：

```bash
python step1_create_agent.py
```

输出类似：

```
Agent 类型: CompiledStateGraph
Agent 创建成功，默认自带以下工具:
  - write_todos: 任务清单管理
  - ls, read_file, write_file, edit_file, glob, grep: 文件操作
  - execute: 执行命令(需要沙箱后端)
  - task: 调用子 Agent

Agent 回复:
  你好！我是 Deep Agent，一个友好的中文 AI 助手，可以帮助你完成任务、解答问题、处理文件、搜索信息等等。
```

这段代码做了什么？

1. `ChatDeepSeek` 创建了一个 LLM 实例，封装了和 DeepSeek API 的通信
2. `create_deep_agent` 用这个 LLM 创建了一个 Deep Agent，返回的是 LangGraph 的 `CompiledStateGraph`
3. `agent.invoke({"messages": "..."})` 调用 Agent，输入格式和 LangGraph 完全一致
4. `result["messages"]` 包含完整对话历史，最后一条就是 Agent 的回复

注意 `invoke` 的参数格式：`{"messages": "字符串"}`。这是 LangGraph StateGraph 的标准输入格式，DeepAgents 原封不动地继承了。你也可以传一个消息列表 `{"messages": [HumanMessage("...")]}`，效果一样。

### create_deep_agent 参数说明

刚才的例子只用了 `model` 和 `system_prompt` 两个参数。`create_deep_agent` 其实还支持很多参数，我们逐个会在后面的文章中用到，这里先给一个全貌：

| 参数 | 类型 | 说明 |
|------|------|------|
| model | str 或 BaseChatModel | LLM 模型，支持 "provider:model" 字符串或 ChatModel 实例 |
| system_prompt | str | 系统提示词，定义 Agent 的角色和行为 |
| tools | list | 自定义工具列表，追加到内置工具上（不会替换内置工具） |
| backend | Backend | 文件系统后端，默认 StateBackend（内存） |
| subagents | list | 子 Agent 配置列表 |
| skills | list | 技能（Skill）配置列表 |
| checkpointer | Checkpointer | 对话持久化组件 |
| name | str | Agent 名称，用于子 Agent 调用时识别 |
| permissions | list | 文件系统权限控制 |

前两个参数就能跑起来，其他的按需添加。这种"最小可用、按需扩展"的设计是 DeepAgents 的核心思路。

## 内置能力一览

一个什么参数都不传的"裸"Agent，默认自带这些工具：

- **write_todos** — 任务清单管理。Agent 接到复杂任务时会自动规划步骤、创建待办列表
- **ls** — 列出目录内容
- **read_file** — 读取文件
- **write_file** — 写入文件
- **edit_file** — 编辑已有文件（支持搜索替换）
- **glob** — 按模式匹配文件路径
- **grep** — 按内容搜索文件
- **execute** — 执行命令（需要沙箱后端支持）
- **task** — 调用子 Agent 执行子任务

这些工具覆盖了"规划-读写-搜索-执行-委派"这一完整的 Agent 工作流。默认的文件操作使用 `StateBackend`，所有文件存储在 Agent 的内存状态中，不会写入真实磁盘。

下面看一个让 Agent 展示规划能力的例子：

```python
agent = create_deep_agent(
    model=llm,
    system_prompt="你是一个项目经理助手，擅长拆分任务和制定计划。请用中文回复。",
)

task = (
    "我需要准备一个技术分享的演讲，主题是'Deep Agent 入门'。"
    "请帮我规划一下准备工作的步骤，包括: 调研主题、编写大纲、准备代码示例、制作 PPT。"
)

result = agent.invoke({"messages": task})
```

Agent 的执行过程大致如下：

```
[0] 用户: 我需要准备一个技术分享的演讲...
[1] Agent 调用工具: write_todos
     参数: {'todos': [{'content': "调研主题 'Deep Agent 入门'", 'status': 'in_progress'}, ...]}
[2] 工具结果: Updated todo list to [...]
[3] Agent 调用工具: task
     参数: {'description': '调研 "Deep Agent" 主题，为我准备一份技术分享的调研报告...'}
[4] 工具结果: 调研报告已完成并保存到 /Deep_Agent_技术调研报告.md
[5] Agent 调用工具: write_todos
     参数: {'todos': [{'content': "调研主题...", 'status': 'completed'}, ...]}
[6] 工具结果: Updated todo list to [...]
...
[29] Agent 回复: 全部准备工作已完成！以下是交付成果清单...
```

Agent 自动调用了 `write_todos` 来创建任务清单，然后根据清单逐项给出建议。这个过程不需要你在 `system_prompt` 里明确要求，Agent 内置的 `TodoListMiddleware` 会在识别到复杂任务时自动触发规划行为。

再看一个涉及文件操作的例子：

```python
agent = create_deep_agent(
    model=llm,
    system_prompt="你是一个开发助手。请用中文回复。",
)

task = (
    "请帮我完成以下工作:\n"
    "1. 创建一个名为 notes.txt 的文件，写入三行笔记\n"
    "2. 然后读取这个文件，确认内容正确\n"
    "3. 最后总结一下你刚才做了什么"
)

result = agent.invoke({"messages": task})
```

执行后，Agent 会依次调用 `write_file`、`read_file`，然后在内存中管理文件内容。最终 `result` 中除了 `messages` 之外，还可能包含 `files` 字段，里面保存了 Agent 创建的所有文件。

```
工具调用统计:
  - write_file: 调用了 1 次
  - read_file: 调用了 1 次

Agent 最终回复:
  内容确认无误。以下是完成工作的总结：
  1. 创建文件 — 在根目录下创建了 notes.txt，写入了三行关于 Deep Agent 核心特性的笔记
  2. 读取确认 — 读取了 notes.txt 文件，验证了写入的内容准确无误
  3. 总结汇报 — 向用户汇报已完成的工作

Agent 创建的文件:
  /notes.txt:
    Deep Agent 核心特性：\n1. 使用工具完成任务\n2. 自动管理复杂任务\n3. 简洁直接的回答风格
```

StateBackend 的文件存在 Agent 的状态中（内存），不会写入真实磁盘。如果需要真实的文件操作，可以用 `FilesystemBackend`，这个在后面的文章中会讲。

## 模型配置的两种方式

在 `create_deep_agent` 的 `model` 参数中，有两种传值方式。

**方式一：字符串格式**

```python
agent = create_deep_agent(
    model="deepseek:deepseek-v4-flash",
    system_prompt="...",
)
```

格式是 `"provider:model_name"`。DeepAgents 内部会自动创建对应的 ChatModel 实例。这种方式最简洁，但缺点是无法自定义 `base_url` 等参数。

**方式二：ChatModel 实例**

```python
from langchain_deepseek import ChatDeepSeek

llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key="sk-xxx",
    base_url="https://api.deepseek.com",
)

agent = create_deep_agent(
    model=llm,
    system_prompt="...",
)
```

这种方式需要多写几行代码，但可以完全控制模型参数。本系列所有示例都使用这种方式，因为 `langchain-deepseek` 需要单独配置 `base_url`。

实际项目中推荐把模型配置抽到 `config.py`，统一管理：

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
```

然后每个示例文件统一从这里导入：

```python
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL
```

这样换模型或换 API 地址时只改 `.env` 就行，不用动代码。

## DeepAgents 和 LangChain + LangGraph 的关系

看到这里你可能会有疑问：DeepAgents 和 LangChain、LangGraph 到底是什么关系？是替代还是补充？

三个东西的定位：

- **LangGraph** — Agent 运行时。提供状态图（`StateGraph`）、节点、边、条件路由等机制，用于编排 Agent 的执行流程。它是独立库，可以不依赖 LangChain 单独使用
- **LangChain** — LLM 应用开发框架。提供模型调用抽象（`ChatDeepSeek`）、工具定义（`@tool`）、消息类型（`HumanMessage`、`AIMessage`）、600+ 模型集成等基础组件。从 1.0 版本起，LangChain 的 `create_agent` 底层调用 LangGraph 的执行引擎来跑 Agent 循环
- **DeepAgents** — 开箱即用的 Agent 框架。在 LangGraph 之上封装了规划、文件管理、子 Agent、技能系统、上下文管理等高级能力

它们的依赖关系：**LangChain 的 `create_agent` 底层依赖 LangGraph**（安装 LangChain 时 `langgraph` 会作为依赖被自动安装）。反过来不成立——LangGraph 可以独立使用，不依赖 LangChain。你可以只装 `langgraph`，直接用 `StateGraph` 构建 Agent，自己对接模型 SDK（比如直接用 `openai` 库而不是 `langchain-openai`）。DeepAgents 同时依赖 LangGraph（运行时）和 LangChain（模型集成）。

简单说：如果你只用 LangGraph 写 Agent，可以完全不碰 LangChain。但如果用 LangChain 的 `create_agent` 或 DeepAgents 的 `create_deep_agent`，LangGraph 就已经在底层跑着了。

### create_agent vs create_deep_agent

既然 LangChain 的 `create_agent` 和 DeepAgents 的 `create_deep_agent` 底层都是 LangGraph，那它们有什么区别？

| 维度 | `create_agent`（LangChain） | `create_deep_agent`（DeepAgents） |
|------|------|------|
| 定位 | 轻量级 Agent 工厂，你自己提供工具，它负责跑循环 | 开箱即用的 Agent 框架，自带规划、文件管理、子 Agent 等全套能力 |
| 内置工具 | 无。你传什么工具它就用什么，不传就只会聊天 | 9 个内置工具（write_todos、read_file、write_file 等），还支持追加自定义工具 |
| 规划能力 | 无。不会自动拆分任务 | 内置 TodoListMiddleware，识别到复杂任务时自动规划 |
| 文件操作 | 无。需要你自己定义文件相关工具 | 内置 StateBackend（内存文件系统）和 FilesystemBackend（真实磁盘） |
| 子 Agent | 无。单 Agent | 内置 `task` 工具，支持创建子 Agent 委派子任务 |
| 技能系统 | 无 | 支持 Skill 配置，类似 Claude Code 的技能机制 |
| 适用场景 | 你知道自己要什么工具，只需要一个跑工具循环的 Agent | 你要一个能自主规划、读写文件、委派任务的完整 Agent |

简单说：`create_agent` 是"你给我工具，我帮你跑"；`create_deep_agent` 是"工具我自带，你告诉我目标就行"。

当你调用 `create_deep_agent(model=llm, system_prompt="...")` 时，背后发生的事情：

1. DeepAgents 创建一个 LangGraph 的 `StateGraph`
2. 往图里添加 LLM 节点、工具执行节点
3. 注册所有内置工具
4. 设置条件路由（LLM 说要调工具就走工具节点，否则直接返回结果）
5. 编译成 `CompiledStateGraph` 返回给你

所以 `agent.invoke()` 的行为和你在 LangGraph 里手写的 ReAct Agent 完全一致——因为底层就是同一个东西。DeepAgents 只是帮你省去了"定义状态、添加节点、连边、编译"这些重复劳动。

这也意味着：如果你有特殊需求（比如自定义状态字段、自定义路由逻辑），你完全可以不用 DeepAgents，直接用 LangGraph 写。DeepAgents 解决的是 80% 的通用场景。

## 小结

- DeepAgents 是 LangChain AI 团队的开箱即用 Agent 框架，底层用 LangGraph 实现
- `create_deep_agent` 只需要 `model` 和 `system_prompt` 就能创建一个可用的 Agent
- 默认自带 9 个内置工具，覆盖规划、文件操作、命令执行、子 Agent 调用
- 默认使用 StateBackend，文件存储在内存中
- 模型配置支持字符串格式和 ChatModel 实例两种方式

## 完整代码

把下面代码保存为 `step1_create_agent.py`，并和前面的 `config.py` 放在同一个目录下运行：

```python
from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

def create_llm():
    return ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

def demo1_minimal_agent():
    print("=" * 50)
    print("Demo 1: 最简 Deep Agent")
    print("=" * 50)

    agent = create_deep_agent(
        model=create_llm(),
        system_prompt="你是一个友好的中文助手，请用简洁的中文回答问题。",
    )

    print(f"Agent 类型: {type(agent).__name__}")
    print("Agent 创建成功，默认自带以下工具:")
    print("  - write_todos: 任务清单管理")
    print("  - ls, read_file, write_file, edit_file, glob, grep: 文件操作")
    print("  - execute: 执行命令，需要沙箱后端")
    print("  - task: 调用子 Agent")

    result = agent.invoke({"messages": "你好，请用一句话介绍一下你自己"})
    print("\nAgent 回复:")
    print(result["messages"][-1].content)
    print()

def demo2_planning_agent():
    print("=" * 50)
    print("Demo 2: Agent 的规划能力")
    print("=" * 50)

    agent = create_deep_agent(
        model=create_llm(),
        system_prompt="你是一个项目经理助手，擅长拆分任务和制定计划。请用中文回复。",
    )

    task = (
        "我需要准备一个技术分享的演讲，主题是'Deep Agent 入门'。"
        "请帮我规划一下准备工作的步骤，包括: 调研主题、编写大纲、准备代码示例、制作 PPT。"
    )

    result = agent.invoke({"messages": task})

    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__
        if msg_type == "HumanMessage":
            print(f"[{i}] 用户: {msg.content}")
        elif msg_type == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    print(f"[{i}] Agent 调用工具: {tool_call['name']}")
                    print(f"    参数: {str(tool_call['args'])[:120]}")
            else:
                print(f"[{i}] Agent 回复: {msg.content[:200]}")
        elif msg_type == "ToolMessage":
            print(f"[{i}] 工具结果: {msg.content[:150]}")
    print()

def demo3_builtin_capabilities():
    print("=" * 50)
    print("Demo 3: Agent 内置能力展示")
    print("=" * 50)

    agent = create_deep_agent(
        model=create_llm(),
        system_prompt="你是一个开发助手。请用中文回复。当需要管理任务时，使用 write_todos 工具。",
    )

    task = (
        "请帮我完成以下工作:\n"
        "1. 创建一个名为 notes.txt 的文件，写入三行笔记，内容是关于 Deep Agent 的核心特性\n"
        "2. 然后读取这个文件，确认内容正确\n"
        "3. 最后总结一下你刚才做了什么"
    )

    result = agent.invoke({"messages": task})

    tool_calls = {}
    for msg in result["messages"]:
        if type(msg).__name__ == "AIMessage" and hasattr(msg, "tool_calls"):
            for tool_call in msg.tool_calls:
                name = tool_call["name"]
                tool_calls[name] = tool_calls.get(name, 0) + 1

    print("工具调用统计:")
    for name, count in tool_calls.items():
        print(f"  - {name}: 调用了 {count} 次")

    print("\nAgent 最终回复:")
    print(result["messages"][-1].content)

    if "files" in result:
        print("\nAgent 创建的文件:")
        for path, content in result["files"].items():
            print(f"  {path}:")
            print(f"    {str(content)[:200]}")

if __name__ == "__main__":
    demo1_minimal_agent()
    demo2_planning_agent()
    demo3_builtin_capabilities()
```
