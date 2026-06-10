> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前面几篇讲了工具、文件系统、子 Agent——这些都是 Agent "能做什么"的能力。但还有一个问题没解决：Agent 怎么"记住"事情？比如项目约定、用户偏好、累积的经验。system_prompt 是静态字符串，写死在代码里；tools 是无状态的，调用完就结束了。Memory 填补了这个空白。

## AGENTS.md：让 Agent 记住项目约定

先看一个具体的问题。你让 Agent 帮你写代码，但每次都要重复告诉它："项目用 Python，测试框架是 pytest，代码风格用 Ruff"。这些信息每次对话都要说一遍，很繁琐。

Memory 就是解决这个问题的。把项目约定写进 AGENTS.md 文件，Agent 每次启动都会自动读取：

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

backend = FilesystemBackend(root_dir=work_dir)

agent = create_deep_agent(
    model=llm,
    memory=["/AGENTS.md"],
    backend=backend,
    system_prompt="你是一个编程助手。",
)
```

`memory` 参数接受一个文件路径列表，路径相对于 backend 的 `root_dir`。`["/AGENTS.md"]` 表示从 `root_dir/AGENTS.md` 读取记忆内容。Agent 启动时，会读取这些文件的内容，注入到系统提示词中。

AGENTS.md 的内容由你自己定义，比如：

```markdown
# 项目约定

## 技术栈
- 语言：Python 3.11+
- Web 框架：FastAPI
- 测试框架：pytest
- 代码风格：Ruff

## 命名规范
- 函数名：snake_case
- 类名：PascalCase
- 常量：UPPER_SNAKE_CASE

## 回复风格
- 用中文回复
- 代码示例优先
- 解释简洁直接
```

测试一下：

```python
# 不需要每次都说"用 Python"——AGENTS.md 里已经有了
task = "帮我写一个分页查询的用户列表 API"
result = agent.invoke({"messages": task})

print(result["messages"][-1].content)
```

Agent 会按照 AGENTS.md 中的约定——用 FastAPI、snake_case 命名、中文回复——来生成代码。你不需要在每次对话中重复这些要求。

**AGENTS.md 写什么？**

| 内容类型 | 示例 |
|---------|------|
| 技术选型 | 语言、框架、库的版本 |
| 命名规范 | 函数名、类名、文件名的命名风格 |
| 代码风格 | 缩进、引号、import 顺序 |
| 回复偏好 | 语言、详细程度、是否要代码示例 |
| 项目结构 | 目录约定、文件组织方式 |

一个原则：**Memory 放始终需要的信息，Skill 放按需加载的流程**。如果一个信息 Agent 每次对话都需要知道（比如"项目用 Python"），放 Memory。如果只有特定任务才需要（比如"怎么做代码审查"），放 Skill。

`memory` 也可以传入多个文件，把不同类型的信息分开管理：

```python
agent = create_deep_agent(
    model=llm,
    memory=["/AGENTS.md", "/preferences.md"],
    backend=backend,
)
```

## Memory、System Prompt、Skills 的关系

到目前为止，我们接触了三种给 Agent 传递信息的方式。它们的核心区别在于**加载时机**：

- **System Prompt**：你手动编写的静态字符串，定义 Agent 的角色和行为。每次调用都是固定的内容，Agent 不能修改它
- **Memory（AGENTS.md）**：存储在文件中的上下文信息，Agent 启动时自动加载。和 system_prompt 的区别是，Memory 可以被 Agent 自己更新（后面会讲到）
- **Skills（SKILL.md）**：按需加载的专业能力。Agent 启动时只看摘要（name 和 description），匹配到具体任务时才加载完整内容

三者组合在一起，构成了 Agent 启动时看到的完整系统提示词：

1. 你写的 `system_prompt`（定义角色）
2. 内置的 base prompt（规划、文件系统、子 Agent 等工具说明）
3. Memory 文件内容（始终加载）
4. Skills 摘要列表（只加载 name 和 description）
5. 内置工具的使用说明

什么时候用哪个？

- 定义 Agent 的身份和行为 -> System Prompt（"你是编程助手"、"用中文回复"）
- 项目约定、始终需要的背景信息 -> Memory（"项目用 Python"、"测试框架是 pytest"）
- 分步骤的专业工作流程 -> Skill（"怎么做代码审查"、"怎么写 Git Commit Message"）
- 单个原子操作 -> Tool（搜索、计算、读写文件）

## Agent 自主更新记忆

Memory 不仅仅是"你写什么 Agent 就看什么"。Agent 可以主动更新记忆文件——通过内置的 `edit_file` 工具。

先创建一个带有用户偏好区的 AGENTS.md：

```python
agents_md = """\
# 项目约定
- 用中文回复
- 代码风格遵循 PEP 8

# 用户偏好
（待补充）
"""
```

让 Agent 在对话中学习并记住用户偏好：

```python
agent = create_deep_agent(
    model=llm,
    memory=["/AGENTS.md"],
    backend=backend,
    system_prompt=(
        "你是一个编程助手。当用户告诉你他的偏好时，"
        "用 edit_file 工具把偏好更新到 AGENTS.md 的'用户偏好'部分。"
    ),
)

task = "我喜欢详细的代码注释，函数都要有 docstring。请记住这个偏好。"
result = agent.invoke({"messages": task})
```

Agent 会调用 `edit_file` 把偏好写入 AGENTS.md。下一次对话（同一个线程中），Agent 读到的 AGENTS.md 已经包含了这个偏好。

这就是 Memory 和 system_prompt 的关键区别：**system_prompt 是静态的，你写什么就是什么；Memory 是动态的，Agent 可以根据经验自主更新。**

### 可写 vs 只读

默认情况下，Agent 对 Memory 文件有读写权限。但在某些场景下你需要限制为只读——比如组织级的合规策略，不应该被 Agent 修改。可以通过 `permissions` 参数来控制：

```python
from deepagents import FilesystemPermission

permissions = [
    FilesystemPermission(
        operations=["write"],
        paths=["/AGENTS.md"],
        mode="deny",
    ),
]

agent = create_deep_agent(
    model=llm,
    memory=["/AGENTS.md"],
    backend=backend,
    permissions=permissions,
)
```

这样 Agent 可以读取 AGENTS.md 中的内容，但不能修改它。适用于多人共享的 Agent 场景——防止一个用户通过对话注入的指令修改共享记忆。

## 跨会话记忆：长期记忆

前面讲的 Memory 有一个限制：文件存在 backend 的存储中，默认的 StateBackend 只在单个对话线程内持久。开一个新线程，之前存的偏好就没了。

如果需要 Agent 在不同对话、不同线程之间记住信息，需要用**长期记忆**。实现方式是 `CompositeBackend` + `StoreBackend`——把 `/memories/` 路径下的文件路由到 LangGraph Store，其他文件仍然走默认 backend。

先看一个最基本的跨线程记忆例子：

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

# 创建 Store（生产环境用 LangGraph Platform 的持久化 Store）
store = InMemoryStore()

agent = create_deep_agent(
    model=llm,
    memory=["/memories/AGENTS.md"],
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/memories/": StoreBackend(rt),
        },
    ),
    store=store,
    system_prompt=(
        "你是一个助手。当用户告诉你偏好时，"
        "保存到 /memories/AGENTS.md。请用中文回复。"
    ),
)
```

这里有几个关键点：

- `CompositeBackend` 是一个混合后端，不同路径可以走不同的存储。它像路由器一样，根据文件路径决定用哪个底层 backend
- `routes={"/memories/": StoreBackend(rt)}` 表示 `/memories/` 下的文件存在 Store 中
- `default=StateBackend(rt)` 表示其他文件仍然存在内存中
- `store=store` 传入 Store 实例，提供跨线程的持久化能力
- `backend` 传的是函数（`lambda rt: ...`），因为每次调用需要用当前的 runtime 来创建 backend

测试跨线程记忆：

```python
from langchain_core.utils.uuid import uuid7

# 线程 1：告诉 Agent 你的偏好
config1 = {"configurable": {"thread_id": str(uuid7())}}
agent.invoke(
    {"messages": [{"role": "user", "content": "我喜欢简洁的回复，不要废话"}]},
    config=config1,
)

# 线程 2：新对话，Agent 记得你的偏好
config2 = {"configurable": {"thread_id": str(uuid7())}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "解释什么是 REST API"}]},
    config=config2,
)
print(result["messages"][-1].content)
```

线程 2 是一个全新的对话，但 Agent 在线程 1 中保存的偏好仍然有效——因为 `/memories/AGENTS.md` 存在 Store 中，不属于任何单个线程。

### Agent 级别 vs 用户级别记忆

上面的例子中，所有用户共享同一个 Store 命名空间，这意味着用户 A 的偏好也会影响用户 B 的对话。大多数场景下你不希望这样。

通过 StoreBackend 的 `namespace` 参数，可以控制记忆的作用域：

**用户级别记忆**——每个用户有独立的记忆空间，互不干扰：

```python
agent = create_deep_agent(
    model=llm,
    memory=["/memories/preferences.md"],
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/memories/": StoreBackend(
                rt,
                namespace=lambda rt: (rt.server_info.user.identity,),
            ),
        },
    ),
    store=store,
)
```

`namespace=lambda rt: (rt.server_info.user.identity,)` 表示每个用户有独立的命名空间。用户 A 的 `/memories/preferences.md` 和用户 B 的是完全隔离的两个文件。

**Agent 级别记忆**——所有用户共享同一个 Agent 的记忆：

```python
namespace=lambda rt: (rt.server_info.assistant_id,)
```

用 `assistant_id` 作为命名空间，同一个 Agent 的所有用户共享记忆。Agent 在和不同用户的对话中积累的经验，都会更新到同一个记忆文件中。适合 Agent 自身的知识积累——比如一个代码助手学会了某个框架的最佳实践，所有用户都能受益。

两种模式可以组合——用户偏好用用户级别，Agent 通用知识用 Agent 级别：

```python
backend=lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={
        "/user-memories/": StoreBackend(
            rt,
            namespace=lambda rt: (rt.server_info.user.identity,),
        ),
        "/agent-memories/": StoreBackend(
            rt,
            namespace=lambda rt: (rt.server_info.assistant_id,),
        ),
    },
),
```

三种作用域的对比：

| 作用域 | 命名空间 | 适用场景 |
|--------|---------|---------|
| 用户级别 | `(user_id,)` | 用户偏好、个人上下文 |
| Agent 级别 | `(assistant_id,)` | Agent 自身知识、通用经验 |
| 组织级别 | `(org_id,)` | 合规策略、组织约定（通常设为只读） |

### 预置记忆内容

Agent 启动时如果记忆路径下没有文件，记忆是空的。你可以在创建 Agent 之前，通过 Store API 预置初始内容：

```python
from deepagents.backends.utils import create_file_data

store.put(
    ("my-agent",),
    "/memories/AGENTS.md",
    create_file_data("""\
## 回复风格
- 用中文回复
- 代码示例优先

## 项目信息
- 框架：FastAPI
- 数据库：PostgreSQL
"""),
)
```

`create_file_data` 把字符串包装成 Store 能接受的文件格式。预置之后，Agent 第一次对话就能读到这些内容。

## 小结

- Memory 用 AGENTS.md 文件存储始终需要的上下文，Agent 启动时自动加载
- Memory、System Prompt、Skills 三者加载时机不同：Memory 始终加载，Skills 按需加载，System Prompt 静态定义
- Agent 可以通过 `edit_file` 自主更新记忆，也可以通过 `permissions` 限制为只读
- 跨会话记忆用 `CompositeBackend` + `StoreBackend`，把指定路径路由到持久化存储
- 通过 `namespace` 区分作用域：用户级别、Agent 级别、组织级别
