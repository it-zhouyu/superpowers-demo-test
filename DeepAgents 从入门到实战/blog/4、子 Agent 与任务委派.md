> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

单个 Agent 处理简单任务没问题。但当任务变复杂——比如"先调研一个技术方案，再根据调研结果写一份教程"——Agent 在执行过程中会产生大量中间输出：搜索结果、阅读笔记、草稿修改记录。这些中间内容全部堆在主 Agent 的上下文窗口（Context Window）里，很快就会把上下文撑满。

子 Agent 解决了这个问题。每个子 Agent 有独立的上下文窗口，在隔离环境中执行任务。主 Agent 只接收子 Agent 的最终结果（一条消息），不会被中间过程污染。

## 创建子 Agent

在 `create_deep_agent` 中通过 `subagents` 参数定义子 Agent。这是一个列表，列表中的每个元素是一个字典，描述一个子 Agent 的配置。

先准备两个自定义工具——一个模拟搜索，一个模拟写文档：

```python
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """模拟网络搜索，返回搜索结果。"""
    mock_results = {
        "Python 异步编程": (
            "Python 异步编程核心概念:\n"
            "1. async/await 语法（Python 3.5+ 引入）\n"
            "2. asyncio 事件循环（Event Loop）\n"
            "3. 协程（Coroutine）与任务（Task）\n"
            "4. aiohttp / httpx 等异步 HTTP 客户端\n"
            "5. 异步数据库驱动: asyncpg, aiomysql\n"
            "参考: https://docs.python.org/3/library/asyncio.html"
        ),
    }
    for key, value in mock_results.items():
        if key in query or any(word in query for word in key.split()):
            return value
    return f"搜索 '{query}' 的结果: 找到了 3 篇相关文章和 2 个示例项目。"

@tool
def write_document(title: str, content: str) -> str:
    """将内容写入文档（模拟）。"""
    return f"文档 '{title}' 已写入完成，共 {len(content)} 字。内容:\n{content}"
```

然后定义两个子 Agent——一个负责调研，一个负责写作：

```python
from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent

llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key="your-api-key",
    base_url="https://api.deepseek.com",
)

# 研究子 Agent —— 擅长搜索和整理信息
research_subagent = {
    "name": "research-agent",
    "description": "负责深入研究特定主题。使用 search_web 工具搜索相关信息并整理成结构化的研究结果。",
    "system_prompt": (
        "你是一个专业的研究员。你的任务是:\n"
        "1. 根据给定的研究主题，使用 search_web 工具搜索相关信息\n"
        "2. 整理搜索结果，提取关键知识点\n"
        "3. 返回简洁、结构化的研究摘要（不超过 300 字）\n"
        "请用中文回复。"
    ),
    "tools": [search_web],
}

# 写作子 Agent —— 擅长内容创作
writing_subagent = {
    "name": "writing-agent",
    "description": "负责根据研究结果撰写文档和教程大纲。擅长内容组织和结构化写作。",
    "system_prompt": (
        "你是一个技术写作专家。你的任务是:\n"
        "1. 根据提供的研究资料，撰写教程大纲或文档\n"
        "2. 大纲应该由浅入深，结构清晰\n"
        "3. 每个章节要有简短说明\n"
        "请用中文回复。"
    ),
    "tools": [write_document],
}
```

把子 Agent 传给主 Agent：

```python
agent = create_deep_agent(
    model=llm,
    system_prompt=(
        "你是一个项目协调者，负责管理研究任务。\n"
        "当用户给出复杂任务时，你应该:\n"
        "1. 分析任务，判断需要哪些子 Agent 协助\n"
        "2. 通过 task() 工具委派任务给合适的子 Agent\n"
        "3. 汇总子 Agent 的结果，给用户最终回复\n"
        "请用中文回复。"
    ),
    tools=[search_web, write_document],
    subagents=[research_subagent, writing_subagent],
)
```

主 Agent 创建完成后，自动获得一个内置的 `task()` 工具。主 Agent 通过这个工具把任务委派给子 Agent，`task()` 的参数是子 Agent 的 `name` 和任务描述。

**子 Agent 配置的字段说明**：

| 字段 | 是否必填 | 说明 |
|------|----------|------|
| name | 是 | 唯一标识符，主 Agent 通过 `task(name=...)` 调用时使用 |
| description | 是 | 能力描述，主 Agent 据此判断什么时候委派给这个子 Agent |
| system_prompt | 是 | 子 Agent 的系统提示词（不会继承主 Agent 的提示词） |
| tools | 否 | 子 Agent 的工具列表（不设置则继承主 Agent 的工具） |
| model | 否 | 覆盖主 Agent 的模型（可以让不同子 Agent 用不同模型） |
| skills | 否 | 子 Agent 专属的技能路径 |

其中 `description` 很关键——主 Agent 根据这个字段来决定"这个任务该交给谁"。如果 description 写得模糊，主 Agent 可能选错子 Agent，或者干脆不委派，自己直接干。

## 任务委派流程

定义好了子 Agent，来看一个完整的委派过程。任务："研究 Python 的异步编程模型，然后写一份教程大纲"。

这个任务明显分两步——先调研，再写作。主 Agent 应该先把调研任务交给 `research-agent`，拿到结果后再交给 `writing-agent` 写大纲。

为了让主 Agent 按正确的顺序委派，在 `system_prompt` 中明确告诉它执行步骤：

```python
agent = create_deep_agent(
    model=llm,
    system_prompt=(
        "你是一个技术团队的协调者。\n"
        "面对复杂任务时，按以下步骤执行:\n"
        "1. 先调用 research-agent 完成调研\n"
        "2. 再调用 writing-agent 基于调研结果撰写文档\n"
        "3. 汇总结果返回给用户\n"
        "请用中文回复。"
    ),
    tools=[search_web, write_document],
    subagents=[research_subagent, writing_subagent],
)

complex_task = "研究 Python 的异步编程模型，然后写一份教程大纲"
result = agent.invoke({"messages": complex_task})
```

我们来分析执行过程中的消息流，看主 Agent 是怎么委派的：

```python
for i, msg in enumerate(result["messages"]):
    msg_type = type(msg).__name__
    if msg_type == "HumanMessage":
        print(f"[{i}] 用户: {msg.content}")
    elif msg_type == "AIMessage":
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "task":
                    args = tc["args"]
                    subagent_name = args.get("name", "unknown")
                    subagent_task = args.get("description", "")
                    print(f"[{i}] 主 Agent 委派任务给: {subagent_name}")
                    print(f"     任务描述: {subagent_task[:100]}")
                else:
                    print(f"[{i}] Agent 调用工具: {tc['name']}")
        else:
            print(f"[{i}] Agent 回复: {msg.content[:300]}")
    elif msg_type == "ToolMessage":
        print(f"[{i}] 工具结果: {msg.content[:200]}")
```

输出大致如下：

```
[0] 用户: 研究 Python 的异步编程模型，然后写一份教程大纲
[1] 主 Agent 委派任务给: research-agent
     任务描述: 研究 Python 异步编程模型的核心概念、关键技术和学习路径
[2] 工具结果: research-agent 的研究结果（async/await 语法、事件循环、协程与任务等）
[3] 主 Agent 委派任务给: writing-agent
     任务描述: 根据以下研究结果撰写 Python 异步编程教程大纲
[4] 工具结果: writing-agent 的写作结果（教程大纲）
[5] Agent 回复: 研究 + 教程大纲已就绪。以下是摘要...
```

整个委派流程拆解如下：

1. 主 Agent 收到用户任务
2. 主 Agent 调用 `task(name="research-agent", description="研究 Python 异步编程模型")`
3. `research-agent` 在独立上下文中执行：调用 `search_web` 搜索信息，整理成结构化摘要，返回结果
4. 主 Agent 收到 research-agent 的结果（一条 ToolMessage）
5. 主 Agent 调用 `task(name="writing-agent", description="根据研究结果写教程大纲")`
6. `writing-agent` 在独立上下文中执行：基于研究结果写教程大纲，返回结果
7. 主 Agent 收到 writing-agent 的结果，汇总后回复用户

关键点在步骤 3 和 6：子 Agent 的搜索过程、思考过程、工具调用的中间结果——这些全部在子 Agent 的独立上下文中，不会出现在主 Agent 的上下文里。主 Agent 只看到步骤 4 和 6 返回的两条 ToolMessage，上下文非常干净。

## 核心概念

上面走完了一个完整的委派流程，这里总结几个关键概念。

**独立上下文窗口**

每个子 Agent 拥有独立的上下文窗口，与主 Agent 完全隔离。子 Agent 执行过程中产生的所有工具调用、中间结果，都不会占用主 Agent 的上下文空间。主 Agent 只接收子 Agent 的最终结果（一条 ToolMessage）。

这是子 Agent 最大的价值——不是"多个人干活"这么简单，而是**隔离中间过程，保护主 Agent 的上下文不被撑满**。

**主 Agent 是协调者**

主 Agent 不直接执行具体任务，而是分析用户需求、选择合适的子 Agent、传递任务描述、收集结果。如果某个子 Agent 的结果不满意，主 Agent 可以重新委派。

**内置的通用子 Agent**

每个 Deep Agent 自动拥有一个名为 `general-purpose` 的子 Agent。它自动继承主 Agent 的工具和技能，不需要专门配置。当你只想隔离上下文、不需要专门的指令时，可以直接委派给它。

**CompiledSubAgent（高级用法）**

除了字典定义的子 Agent，Deep Agent 还支持 `CompiledSubAgent`——直接使用 LangGraph 的 `CompiledStateGraph` 来定义子 Agent。这适合需要自定义工作流图的复杂场景，比如子 Agent 内部有条件分支、循环等逻辑。日常使用中字典定义已经足够。

## 什么时候用子 Agent（什么时候不用）

子 Agent 有明显的收益，但也有开销（额外的上下文创建和 LLM 调用）。不是所有任务都需要子 Agent。

**适合使用的场景**：

- **多步骤任务，会产生大量中间结果**。比如"调研一个技术方案"——搜索、阅读多篇文档、做笔记，这些中间过程如果全在主 Agent 上下文中，很容易撑满。交给子 Agent，主 Agent 只拿到一份摘要。
- **需要专门的指令或工具集**。比如研究子 Agent 只需要搜索工具，写作子 Agent 只需要文档工具。不同的子 Agent 配不同的工具，比把所有工具都给一个 Agent 更精确。
- **不同子任务需要不同的模型**。比如推理类子任务用强模型，写作类子任务用快模型。通过 `model` 字段可以给不同子 Agent 指定不同模型。

**不适合使用的场景**：

- **简单的单步任务**。比如"把这段代码翻译成 Python"，一个 Agent 直接就能做，委派给子 Agent 反而多了一层开销。
- **需要保留中间上下文**。如果主 Agent 需要看到子 Agent 执行过程中的每一步细节（而不仅仅是最终结果），子 Agent 的隔离特性反而是障碍。
- **委派开销大于收益**。简单的两轮对话任务，委派带来的上下文节省不明显，但增加了延迟和 token 消耗。

## 最佳实践

根据实际使用经验，这几个做法能显著提升子 Agent 的效果：

**description 要具体**

主 Agent 根据 description 判断"这个任务该交给谁"。写得模糊会导致主 Agent 选错子 Agent 或者不委派。

```python
# 太模糊
"description": "负责研究"

# 具体清晰
"description": "深入调研特定技术主题。使用 search_web 搜索相关信息，整理成结构化的研究摘要。当需要了解某个技术领域、收集资料时使用。"
```

**system_prompt 要包含输出格式要求**

子 Agent 返回什么格式、多长、包含哪些部分——这些都要在 system_prompt 中说清楚。否则子 Agent 可能返回一大段原始数据，主 Agent 还要花额外的上下文去理解。

```python
"system_prompt": (
    "你是一个专业的研究员。\n"
    "输出格式:\n"
    "  - 核心概念（3-5 条）\n"
    "  - 关键技术点（3-5 条）\n"
    "  - 推荐学习路径\n"
    "保持简洁，不超过 400 字。用中文回复。"
)
```

**tools 尽量精简**

只给子 Agent 必要的工具。子 Agent 工具越多，越容易"分心"——本该搜索的时候去写文件，本该写作的时候去搜索。工具少，行为更可预测。

**要求子 Agent 返回简洁摘要**

子 Agent 的返回结果会进入主 Agent 的上下文，所以要求子 Agent 返回 300-500 字的结构化摘要，而不是把搜索到的原始数据全部返回。

**不同子 Agent 可以用不同模型**

这是子 Agent 的一个隐藏优势。推理密集的子任务（比如代码分析、逻辑推导）用强模型，生成密集的子任务（比如写大纲、翻译）用快模型，在效果和成本之间取得平衡。

## 小结

这里讲了 Deep Agent 子 Agent 机制的核心内容：

- 子 Agent 通过 `subagents` 参数定义，每个子 Agent 需要 `name`、`description`、`system_prompt` 三个必填字段
- 主 Agent 通过内置的 `task()` 工具委派任务，子 Agent 在独立上下文中执行，只返回最终结果
- 子 Agent 的核心价值是隔离中间过程，保护主 Agent 的上下文不被撑满
- 适合多步骤、大量中间输出的复杂任务；简单任务不需要委派
- description 要具体、system_prompt 要包含输出格式、tools 要精简
