> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前面我们用子 Agent 解决了"任务太重，一个 Agent 干不过来"的问题。但还有一种情况没覆盖：Agent 需要**专业知识**——不是"做什么"（Tool 能解决），而是"怎么做"（步骤、规范、判断标准）。

比如代码审查。Tool 能帮你读文件、搜索代码，但"怎么审查"——先检查什么、后检查什么、按什么标准判断好坏、结果怎么组织——这些是**工作流程**，不是单个函数调用能表达的。

Skill（技能）就是来解决这个问题的。一个 Skill 是一个可复用的行为模块，用 SKILL.md 文件定义，包含完整的步骤化指令。Agent 在需要时才加载它，按照里面的步骤执行。

## Skill 是什么

先通过一个对比来理解 Skill 的定位：

- **Tool（工具）**：单个原子操作。读文件、搜索、计算——一次调用，一个结果。Tool 回答"Agent 能做什么"
- **Skill（技能）**：多步骤工作流程。代码审查、文档生成、Git 提交——一系列有序步骤，包含领域知识和判断标准。Skill 回答"Agent 怎么做"
- **Memory（记忆，AGENTS.md）**：始终加载的项目上下文。项目约定、命名规范、技术选型。Memory 回答"Agent 要记住什么"

三者最关键的区别是**加载时机**：

- Memory（AGENTS.md）：Agent 启动时就加载，始终在上下文中
- Tool：Agent 在需要时调用，每次调用返回一个结果
- Skill：Agent 启动时只看摘要，匹配到相关任务时才加载完整内容

Skill 的这个"按需加载"机制叫**渐进式披露（Progressive Disclosure）**——先告诉 Agent"我有这个能力"，等真正需要时才展开全部指令。好处是节省上下文空间：Agent 不用把所有技能的完整指令都塞进上下文，只在匹配到具体任务时才加载。

## SKILL.md 格式

每个 Skill 是一个目录，核心文件是 SKILL.md。目录结构如下：

```
skills/
  code-reviewer/
    SKILL.md
  python-style-guide/
    SKILL.md
```

SKILL.md 由两部分组成：**Frontmatter**（YAML 格式的元数据）和**正文**（Markdown 格式的指令）。

先看一个完整的 code-reviewer（代码审查）技能：

```markdown
name: code-reviewer
description: 审查代码中的 bug 和最佳实践问题。当用户提交代码需要审查、或需要代码质量评估时使用此技能。
# Code Reviewer Skill

## 概述
这个技能用于审查 Python 代码，检查常见的 bug 模式和最佳实践。

## 指令

### 1. 阅读代码
仔细阅读用户提供的代码，理解其功能和意图。

### 2. 检查常见 Bug
逐项检查以下常见问题:
- 未处理的异常
- 资源泄漏（未关闭的文件、数据库连接等）
- 变量作用域问题
- 类型混淆
- 空值/None 处理

### 3. 检查最佳实践
- 函数命名是否清晰
- 是否有重复代码可以提取
- 是否符合 PEP 8 风格
- 错误处理是否充分

### 4. 输出格式
按以下格式输出审查结果:
```
## 代码审查报告

### 严重问题 (Critical)
- [列出严重的 bug]

### 建议改进 (Suggestions)
- [列出改进建议]

### 代码质量评分
- 整体评分: X/10
- 可读性: X/10
- 健壮性: X/10
```
```

上面用 `---` 包裹的部分是 Frontmatter，下面是正文。Frontmatter 中最关键的两个字段：

- `name`：技能的唯一标识符，Agent 内部用它来引用技能
- `description`：技能的描述，Agent 根据这个描述判断"当前任务是否需要这个技能"

正文通常包含三个部分：概述（这个技能做什么）、指令（分步骤描述执行流程）、输出格式（Agent 应该按什么格式返回结果）。

Frontmatter 还有一些可选字段，用在更高级的场景中：

| 字段 | 是否必需 | 说明 |
|------|----------|------|
| name | 是 | 技能的唯一标识符 |
| description | 是 | Agent 用来匹配任务的描述文本 |
| license | 否 | 许可证信息 |
| metadata | 否 | 额外元数据，如 author、version |
| allowed-tools | 否 | 限制该技能可以使用的工具范围 |
| module | 否 | 可导入的代码模块文件名（用于 Interpreter Skills） |

大多数情况下，只需要 `name` 和 `description` 就够了。

再看一个包含可选字段的示例——api-doc-writer（API 文档生成器）：

```markdown
name: api-doc-writer
description: 根据 API 接口定义自动生成 API 文档。当需要编写或更新 REST API 文档时使用。
license: MIT
metadata:
  author: demo-team
  version: "1.0"
# API Doc Writer

## 概述
根据 REST API 接口定义，生成标准化的 API 文档。

## 指令

### 1. 分析接口
读取用户提供的接口定义，识别:
- HTTP 方法和路径
- 请求参数（Query、Body、Path）
- 响应格式和状态码
- 认证要求

### 2. 生成文档
按以下模板生成每个接口的文档:
- 接口名称和描述
- 请求方法和 URL
- 请求参数表格（参数名、类型、必填、说明）
- 响应示例（JSON）
- 错误码说明

### 3. 输出
生成完整的 Markdown 格式 API 文档。
```

`license` 和 `metadata` 不会影响 Agent 的行为，主要用于技能的发布和版本管理。`allowed-tools` 可以限制技能执行时只使用指定的工具，防止技能越权。

## Agent 加载和使用 Skill

了解了 SKILL.md 的格式，接下来看 Agent 怎么发现和使用技能。

### 配置 Agent 使用技能

让 Agent 使用技能只需要在创建时指定 `skills` 参数：

```python
from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

# 使用 FilesystemBackend，技能从磁盘加载
backend = FilesystemBackend(root_dir=work_dir)

agent = create_deep_agent(
    model=llm,
    system_prompt=(
        "你是一个代码审查助手。当收到代码需要审查时，使用你的 code-reviewer 技能。\n"
        "按照技能中的指令逐步执行审查。\n"
        "请用中文回复。"
    ),
    backend=backend,
    skills=["/skills/"],  # 技能目录，相对于 backend 的 root_dir
)
```

`skills` 参数接受一个路径列表，路径相对于 `FilesystemBackend` 的 `root_dir`。`["/skills/"]` 表示从 `root_dir/skills/` 目录下加载所有技能。

### 渐进式披露的执行过程

Agent 使用技能的过程分四步：

**第 1 步：启动时读取摘要**

Agent 启动时，遍历 `skills/` 目录下所有子目录，读取每个 SKILL.md 的 Frontmatter（只读 `name` 和 `description`），不读正文。这一步很快，因为只需要解析几行 YAML。

**第 2 步：收到任务时匹配技能**

用户发来一个代码审查任务。Agent 看到任务描述中有"审查代码"等关键词，和 `code-reviewer` 技能的 `description` 匹配，决定激活这个技能。

**第 3 步：加载完整 SKILL.md**

匹配成功后，Agent 读取 `skills/code-reviewer/SKILL.md` 的完整内容，包括所有指令步骤。

**第 4 步：按步骤执行**

Agent 按照 SKILL.md 中的指令，逐步执行：先阅读代码，然后检查常见 Bug，再检查最佳实践，最后按指定格式输出审查报告。

### 用一个例子走完整个过程

给 Agent 一段有问题的代码，让它审查：

```python
code_to_review = """\
def get_user_data(user_id):
    conn = db.connect()
    result = conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
    data = result.fetchone()
    return data
"""

task_text = f"请审查以下代码并给出建议:\n```\n{code_to_review}\n```"
result = agent.invoke({"messages": task_text})
```

这段代码有三个明显问题：SQL 注入风险、数据库连接未关闭、没有异常处理。Agent 收到任务后，匹配到 `code-reviewer` 技能，加载完整指令，然后按步骤审查。

查看执行过程中的工具调用：

```python
tool_calls = {}
for msg in result["messages"]:
    if type(msg).__name__ == "AIMessage" and hasattr(msg, "tool_calls"):
        for tc in msg.tool_calls:
            name = tc["name"]
            tool_calls[name] = tool_calls.get(name, 0) + 1

for name, count in tool_calls.items():
    print(f"  - {name}: {count} 次")
```

Agent 最终会输出一份结构化的审查报告，指出 SQL 注入、资源泄漏、异常处理等问题，并给出评分和改进建议。

注意，整个过程不需要你在代码中手动加载 SKILL.md 或解析指令——Agent 自动完成了"匹配 -> 加载 -> 执行"的完整链路。你只需要把 SKILL.md 放到正确的目录，Agent 就能发现并使用它。

## 创建自定义 Skill

前面用的是预置的 code-reviewer 技能。实际项目中，你需要根据业务需求创建自己的技能。完整流程是：创建 SKILL.md -> 放到 skills 目录 -> 配置 Agent 的 skills 参数 -> 发任务触发。

### 创建一个 git-commit-helper 技能

假设你想让 Agent 帮你写规范的 Git Commit Message。先创建技能目录和文件：

```python
import os

skills_dir = os.path.join(work_dir, "skills", "git-commit-helper")
os.makedirs(skills_dir, exist_ok=True)
```

然后写入 SKILL.md：

```markdown
name: git-commit-helper
description: 帮助编写规范的 Git Commit Message。当用户需要提交代码、编写 commit message 时使用。
# Git Commit Helper Skill

## 概述
根据代码变更内容，生成符合 Conventional Commits 规范的提交信息。

## 指令

### 1. 分析变更
检查代码变更内容，识别:
- 变更类型（新增功能 / 修复 Bug / 重构 / 文档 / 测试）
- 影响范围（哪些模块/文件）
- 是否包含破坏性变更

### 2. 生成 Commit Message
按照 Conventional Commits 规范:
- 格式: type(scope): description
- type: feat / fix / refactor / docs / test / chore
- scope: 可选，表示影响范围
- description: 简短描述（不超过 50 字符）
- 正文: 详细说明（可选）

### 3. 示例输出
feat(auth): 添加 JWT token 刷新机制

实现了 access token 过期后自动使用 refresh token
获取新 token 的逻辑，包含错误处理和重试机制。
```

### 配置并测试

创建 Agent 并测试这个技能：

```python
llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

backend = FilesystemBackend(root_dir=work_dir)

agent = create_deep_agent(
    model=llm,
    system_prompt=(
        "你是一个 Git 助手。当用户需要帮助编写 commit message 时，"
        "使用 git-commit-helper 技能中的规范。\n"
        "请用中文回复。"
    ),
    backend=backend,
    skills=["/skills/"],
)

# 测试
task_text = (
    "我修改了用户登录模块，添加了 OAuth2 第三方登录支持，"
    "同时修复了密码校验的一个空指针异常。"
    "帮我写一个 commit message。"
)
result = agent.invoke({"messages": task_text})
```

Agent 会根据 `git-commit-helper` 技能中的指令，分析变更类型（新功能 + Bug 修复），按照 Conventional Commits 规范生成类似这样的提交信息：

```
feat(auth): 添加 OAuth2 第三方登录支持并修复密码校验空指针异常

- 新增 OAuth2 第三方登录功能，支持主流第三方平台认证
- 修复密码校验逻辑中的空指针异常，增加空值安全判断
```

### 技能的生命周期

从创建到执行，一个技能经历六个阶段：

1. **创建**：编写 SKILL.md 文件，定义 name、description 和步骤化指令
2. **部署**：放到 skills/ 目录下，目录名就是技能的标识
3. **发现**：Agent 启动时遍历 skills 目录，读取每个 SKILL.md 的 Frontmatter，注册到技能列表
4. **匹配**：收到任务时，Agent 根据 description 判断是否需要激活某个技能
5. **加载**：匹配后读取完整的 SKILL.md 内容，进入 Agent 上下文
6. **执行**：按照指令逐步执行任务

这六个阶段中，你只需要关心第 1 步（创建）和第 2 步（部署）。后面四步都是 Agent 自动完成的。

### 编写 Skill 的最佳实践

写好一个 Skill 的关键在于三点：

**description 要具体、要匹配真实的用户请求**

Agent 依赖 description 来决定是否激活技能。如果 description 写得太笼统（比如"帮助开发者"），Agent 很难准确匹配。好的写法是"当用户提交代码需要审查时使用"、"当用户需要编写 commit message 时使用"——直接描述触发场景。

**指令要分步骤、要具体**

不要写"请审查代码并给出建议"这种模糊指令。要拆成明确的步骤：第一步阅读代码理解意图，第二步逐项检查常见 Bug，第三步检查最佳实践，第四步按格式输出。每一步都说清楚要做什么、怎么做。

**包含输出格式**

告诉 Agent 应该按什么格式返回结果。这样 Agent 的输出更稳定、更可预测，后续处理也更方便。

一个核心原则：**一个技能只做一件事**。不要把代码审查和代码风格检查塞进同一个 Skill，它们应该是两个独立的技能。粒度越细，Agent 的匹配越准确，指令也越聚焦。

## Skills、Memory、Tools 对比

三种机制各有所长，用在不同的场景：

| 维度 | Tool | Skill | Memory（AGENTS.md） |
|------|------|-------|---------------------|
| 本质 | 原子操作 | 多步骤工作流程 | 项目上下文 |
| 加载时机 | 调用时执行 | 匹配时加载 | 启动时始终加载 |
| 上下文占用 | 几乎不占（调用完就返回） | 按需占用（匹配时才加载） | 始终占用 |
| 粒度 | 细（单个函数） | 中（一套流程） | 粗（全局背景） |
| 典型用途 | 搜索、计算、读写文件 | 代码审查、文档生成、Git 提交 | 项目约定、命名规范 |

什么时候用哪个？

- **需要大量上下文的专业知识** -> Skill。只有匹配到相关任务时才加载，不浪费上下文空间
- **少量始终需要的背景信息** -> Memory（AGENTS.md）。比如项目用 TypeScript、测试框架是 Jest，这类信息 Agent 每次都需要知道
- **单一的原子操作** -> Tool。比如搜索、计算、读写文件

三者可以组合使用。一个代码审查 Skill 的执行过程中，会调用 Tool（读文件、搜索代码），也会参考 Memory 中的项目约定（代码风格、技术选型）。它们不是互相替代的关系，而是互补的。

完整代码见 `deepagents-demo/step6_skills.py`，包含四个 Demo：Skills 目录结构演示、SKILL.md 格式详解、Agent 加载和使用技能、自定义技能创建。
