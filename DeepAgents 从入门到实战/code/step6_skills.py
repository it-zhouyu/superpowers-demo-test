"""
DeepAgents 教程 - Step 5: Skills 技能系统

本示例演示 Deep Agent 的 Skills（技能）系统:
1. Skills 目录结构与 SKILL.md 格式
2. Agent 加载和使用技能
3. 自定义技能的创建

Skills 是可复用的 Agent 能力，提供专门的工作流程和领域知识。
与 tools 不同，Skills 是一组指令+资源的组合，Agent 按需加载（渐进式披露）。

依赖: deepagents>=0.6.4, langchain-deepseek, langgraph>=1.2.2
"""

import os
import tempfile
from pathlib import Path

from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ---------- 辅助函数 ----------

def create_skills_directory(base_dir: str) -> str:
    """
    创建示例 Skills 目录结构。

    目录布局:
        skills/
        ├── code-reviewer/
        │   └── SKILL.md
        └── python-style-guide/
            └── SKILL.md

    每个 Skill 是一个目录，核心文件是 SKILL.md。
    """
    skills_dir = os.path.join(base_dir, "skills")
    os.makedirs(skills_dir, exist_ok=True)
    return skills_dir


def create_code_reviewer_skill(skills_dir: str) -> str:
    """创建 code-reviewer 技能的 SKILL.md 文件。"""
    skill_dir = os.path.join(skills_dir, "code-reviewer")
    os.makedirs(skill_dir, exist_ok=True)

    skill_content = """\
---
name: code-reviewer
description: 审查代码中的 bug 和最佳实践问题。当用户提交代码需要审查、或需要代码质量评估时使用此技能。
---

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
"""
    skill_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)

    return skill_path


def create_python_style_guide_skill(skills_dir: str) -> str:
    """创建 python-style-guide 技能的 SKILL.md 文件。"""
    skill_dir = os.path.join(skills_dir, "python-style-guide")
    os.makedirs(skill_dir, exist_ok=True)

    skill_content = """\
---
name: python-style-guide
description: 提供 Python 代码风格指南和规范建议。当用户询问代码风格、命名规范、项目结构时使用此技能。
---

# Python Style Guide Skill

## 概述
这个技能提供 Python 代码风格指导，帮助写出更规范、更易维护的代码。

## 指令

### 1. 命名规范
- 函数和变量: snake_case（如 calculate_total, user_name）
- 类名: PascalCase（如 UserService, DataProcessor）
- 常量: UPPER_SNAKE_CASE（如 MAX_RETRIES, DEFAULT_TIMEOUT）
- 私有成员: 前缀下划线（如 _internal_state）

### 2. 函数设计
- 单个函数不超过 30 行
- 参数不超过 5 个，超过时考虑使用数据类
- 必须有 docstring，说明参数和返回值
- 类型注解是必须的

### 3. 项目结构建议
- src/ 目录存放源码
- tests/ 目录存放测试
- docs/ 目录存放文档
- pyproject.toml 作为项目配置

### 4. 输出格式
根据用户的具体问题，给出针对性的建议和代码示例。
"""
    skill_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)

    return skill_path


# ---------- Demo 函数 ----------

def demo1_skills_directory_structure():
    """
    Demo 1: Skills 目录结构

    展示如何组织 Skills 目录，以及 SKILL.md 的基本格式。
    """
    print("=" * 50)
    print("Demo 1: Skills 目录结构")
    print("=" * 50)

    # 创建临时目录作为工作区
    work_dir = tempfile.mkdtemp(prefix="deepagent_skills_")
    print(f"工作目录: {work_dir}")

    # 创建 Skills 目录和示例技能
    skills_dir = create_skills_directory(work_dir)
    create_code_reviewer_skill(skills_dir)
    create_python_style_guide_skill(skills_dir)

    # 展示目录结构
    print()
    print("Skills 目录结构:")
    for root, dirs, files in os.walk(os.path.join(work_dir, "skills")):
        level = root.replace(os.path.join(work_dir, "skills"), "").count(os.sep)
        indent = "  " * level
        folder_name = os.path.basename(root)
        print(f"  {indent}{folder_name}/")
        sub_indent = "  " * (level + 1)
        for file in files:
            print(f"  {sub_indent}{file}")

    print()
    print("SKILL.md 文件由两部分组成:")
    print("  1. Frontmatter（YAML 格式）: 元数据，包括 name、description 等")
    print("  2. 正文（Markdown 格式）: 技能的详细指令和使用说明")
    print()

    # 展示 SKILL.md 的内容结构
    skill_path = os.path.join(skills_dir, "code-reviewer", "SKILL.md")
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    print("code-reviewer/SKILL.md 的 Frontmatter 部分:")
    # 提取 frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            frontmatter = content[3:end].strip()
            print(frontmatter)
    print()

    print("Skills 工作原理（渐进式披露）:")
    print("  1. Agent 启动时，只读取每个 SKILL.md 的 frontmatter（name + description）")
    print("  2. 收到用户请求时，Agent 判断哪个 Skill 匹配当前任务")
    print("  3. 匹配后，Agent 读取完整的 SKILL.md 内容")
    print("  4. 按照指令执行任务")
    print("  - 这种按需加载的方式称为'渐进式披露'（Progressive Disclosure）")
    print("  - 好处: 节省上下文空间，只在需要时才加载完整指令")
    print()

    return work_dir


def demo2_skill_md_format():
    """
    Demo 2: SKILL.md 格式详解

    展示 SKILL.md 的完整格式和各字段含义。
    """
    print("=" * 50)
    print("Demo 2: SKILL.md 格式详解")
    print("=" * 50)

    print("SKILL.md 的 Frontmatter 字段:")
    print()
    print("  必需字段:")
    print("    - name: 技能名称（唯一标识符）")
    print("    - description: 技能描述（Agent 根据这个判断是否匹配任务）")
    print()
    print("  可选字段:")
    print("    - license: 许可证信息")
    print("    - compatibility: 兼容性说明")
    print("    - metadata: 额外元数据（如 author, version）")
    print("    - allowed-tools: 允许使用的工具列表")
    print("    - module: 可导入的代码模块文件名（用于 Interpreter Skills）")
    print()

    print("SKILL.md 的正文结构（建议遵循）:")
    print()
    print("  # 技能名称")
    print("  ## 概述")
    print("  简要说明这个技能做什么")
    print()
    print("  ## 指令")
    print("  分步骤描述执行流程，每步说明要做什么")
    print()
    print("  ## 输出格式")
    print("  说明 Agent 应该按什么格式返回结果")
    print()

    # 展示一个完整的 SKILL.md 示例
    sample_skill = """\
---
name: api-doc-writer
description: 根据 API 接口定义自动生成 API 文档。当需要编写或更新 REST API 文档时使用。
license: MIT
metadata:
  author: demo-team
  version: "1.0"
---

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
"""
    print("完整示例:")
    print(sample_skill)
    print()


def demo3_agent_loads_skill():
    """
    Demo 3: Agent 加载和使用技能

    创建一个使用 FilesystemBackend 的 Agent，配置 skills 目录，
    然后给它一个触发 code-reviewer 技能的任务。
    """
    print("=" * 50)
    print("Demo 3: Agent 加载和使用技能")
    print("=" * 50)

    # 准备工作目录和技能文件
    work_dir = tempfile.mkdtemp(prefix="deepagent_skill_demo_")
    skills_dir = create_skills_directory(work_dir)
    create_code_reviewer_skill(skills_dir)
    print(f"工作目录: {work_dir}")

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 使用 FilesystemBackend，技能从磁盘加载
    # skills 参数接受一个路径列表，路径相对于 backend 的 root_dir
    backend = FilesystemBackend(root_dir=work_dir)

    agent = create_deep_agent(
        model=llm,
        system_prompt=(
            "你是一个代码审查助手。当收到代码需要审查时，使用你的 code-reviewer 技能。\n"
            "按照技能中的指令逐步执行审查。\n"
            "请用中文回复。"
        ),
        backend=backend,
        skills=["/skills/"],
    )

    print("Agent 配置:")
    print("  - Backend: FilesystemBackend（从磁盘读写文件）")
    print("  - Skills 目录: /skills/（相对于 root_dir）")
    print("  - 已配置技能: code-reviewer, python-style-guide")
    print()

    # 给 Agent 一个会触发 code-reviewer 技能的任务
    code_to_review = """\
def get_user_data(user_id):
    conn = db.connect()
    result = conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
    data = result.fetchone()
    return data
"""
    task_text = f"请审查以下代码并给出建议:\n```\n{code_to_review}\n```"
    print(f"用户任务: 审查一段代码")
    print()

    result = agent.invoke({"messages": task_text})

    # 统计工具调用
    tool_calls = {}
    for msg in result["messages"]:
        if type(msg).__name__ == "AIMessage" and hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                name = tc["name"]
                tool_calls[name] = tool_calls.get(name, 0) + 1

    print("工具调用统计:")
    for name, count in tool_calls.items():
        print(f"  - {name}: {count} 次")
    print()

    # 打印最终回复
    last_msg = result["messages"][-1]
    content = last_msg.content
    if len(content) > 600:
        content = content[:600] + "..."
    print("Agent 审查结果:")
    print(content)
    print()


def demo4_custom_skill_creation():
    """
    Demo 4: 自定义技能创建

    演示如何创建一个新的技能，并让 Agent 发现和使用它。
    展示技能的完整生命周期: 创建 -> 部署 -> 发现 -> 使用。
    """
    print("=" * 50)
    print("Demo 4: 自定义技能创建")
    print("=" * 50)

    # 步骤 1: 创建新技能
    work_dir = tempfile.mkdtemp(prefix="deepagent_custom_skill_")
    skills_dir = os.path.join(work_dir, "skills", "git-commit-helper")
    os.makedirs(skills_dir, exist_ok=True)

    print("步骤 1: 创建自定义技能")
    print(f"  技能目录: skills/git-commit-helper/")
    print()

    skill_content = """\
---
name: git-commit-helper
description: 帮助编写规范的 Git Commit Message。当用户需要提交代码、编写 commit message 时使用。
---

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
"""
    skill_path = os.path.join(skills_dir, "SKILL.md")
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)

    print("  SKILL.md 已创建")
    print()

    # 步骤 2: 配置 Agent 使用新技能
    print("步骤 2: 配置 Agent 使用新技能")

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
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

    print("  Agent 已配置，skills 目录包含: git-commit-helper")
    print()

    # 步骤 3: Agent 发现并使用技能
    print("步骤 3: 测试技能")

    task_text = (
        "我修改了用户登录模块，添加了 OAuth2 第三方登录支持，"
        "同时修复了密码校验的一个空指针异常。"
        "帮我写一个 commit message。"
    )
    print(f"  用户任务: {task_text}")
    print()

    result = agent.invoke({"messages": task_text})

    last_msg = result["messages"][-1]
    content = last_msg.content
    if len(content) > 500:
        content = content[:500] + "..."
    print("  Agent 回复:")
    print(f"  {content}")
    print()

    # 步骤 4: 技能生命周期总结
    print("步骤 4: 技能生命周期总结")
    print("  1. 创建: 编写 SKILL.md 文件，定义 name/description/指令")
    print("  2. 部署: 放到 skills/ 目录下")
    print("  3. 发现: Agent 启动时读取 frontmatter，注册到技能列表")
    print("  4. 匹配: 收到任务时，Agent 根据 description 判断是否使用")
    print("  5. 加载: 匹配后读取完整 SKILL.md 内容")
    print("  6. 执行: 按照指令执行任务")
    print()

    print("Skills 与 Memory 的区别:")
    print("  - Skills: 按需加载的任务指令，适合特定场景的专业知识")
    print("  - Memory (AGENTS.md): 启动时始终加载的持久上下文")
    print("  - Tools: 单个函数调用，粒度更细")
    print("  - 建议: 大量上下文用 Skills，少量始终需要的用 Memory，原子操作用 Tools")


if __name__ == "__main__":
    print("DeepAgents 教程 - Step 5: Skills 技能系统")
    print()

    demo1_skills_directory_structure()
    demo2_skill_md_format()
    demo3_agent_loads_skill()
    demo4_custom_skill_creation()

    print("=" * 50)
    print("Step 5 完成!")
    print("=" * 50)
