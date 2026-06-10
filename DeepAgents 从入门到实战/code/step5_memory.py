"""
DeepAgents 教程 - Step 5: Memory 记忆机制

本示例演示 Deep Agent 的 Memory 机制，
包括 AGENTS.md 基本用法、Memory 自主更新、跨会话长期记忆。

依赖: deepagents>=0.6.4, langchain-deepseek, langgraph>=1.2.2
"""

import os
import tempfile
import shutil

from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import StateBackend, FilesystemBackend
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


def demo1_basic_memory():
    """
    Demo 1: AGENTS.md 基本用法
    通过 memory 参数加载项目约定，Agent 自动遵循约定行为。
    """
    print("=" * 50)
    print("Demo 1: AGENTS.md 基本用法")
    print("=" * 50)

    # 创建临时工作目录
    work_dir = tempfile.mkdtemp(prefix="deepagents_memory_")
    print(f"工作目录: {work_dir}")

    # 创建 AGENTS.md 文件
    agents_md_path = os.path.join(work_dir, "AGENTS.md")
    with open(agents_md_path, "w", encoding="utf-8") as f:
        f.write("""\
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
""")
    print("已创建 AGENTS.md")
    print()

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 通过 memory 参数传入 AGENTS.md 路径
    # 路径相对于 FilesystemBackend 的 root_dir
    agent = create_deep_agent(
        model=llm,
        memory=["/AGENTS.md"],
        backend=FilesystemBackend(root_dir=work_dir),
        system_prompt="你是一个编程助手。",
    )

    # 不需要每次都说"用 Python"——AGENTS.md 里已经有了
    task = "帮我写一个分页查询的用户列表 API"
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})
    print("Agent 回复:")
    print(f"  {result['messages'][-1].content[:300]}...")
    print()

    # 清理
    shutil.rmtree(work_dir)
    print("工作目录已清理")
    print()

    print("要点:")
    print("  - memory 参数接受文件路径列表，路径相对于 backend 的 root_dir")
    print("  - AGENTS.md 内容在 Agent 启动时自动注入系统提示词")
    print("  - 适合存放项目约定、技术选型、命名规范等始终需要的上下文")
    print()


def demo2_memory_update():
    """
    Demo 2: Agent 自主更新记忆
    Agent 通过 edit_file 工具在对话中学习并记住用户偏好。
    """
    print("=" * 50)
    print("Demo 2: Agent 自主更新记忆")
    print("=" * 50)

    work_dir = tempfile.mkdtemp(prefix="deepagents_memory_update_")

    # 创建带有"用户偏好"区域的 AGENTS.md
    agents_md_path = os.path.join(work_dir, "AGENTS.md")
    with open(agents_md_path, "w", encoding="utf-8") as f:
        f.write("""\
# 项目约定
- 用中文回复
- 代码风格遵循 PEP 8

# 用户偏好
（待补充）
""")

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    agent = create_deep_agent(
        model=llm,
        memory=["/AGENTS.md"],
        backend=FilesystemBackend(root_dir=work_dir),
        system_prompt=(
            "你是一个编程助手。当用户告诉你他的偏好时，"
            "用 edit_file 工具把偏好更新到 AGENTS.md 的'用户偏好'部分。"
        ),
    )

    # 让 Agent 学习用户偏好
    task = "我喜欢详细的代码注释，函数都要有 docstring。请记住这个偏好。"
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})
    print("Agent 回复:")
    print(f"  {result['messages'][-1].content[:200]}")
    print()

    # 查看 Agent 是否更新了 AGENTS.md
    with open(agents_md_path, "r", encoding="utf-8") as f:
        updated_content = f.read()
    print("更新后的 AGENTS.md:")
    for line in updated_content.split("\n"):
        print(f"  {line}")
    print()

    # 清理
    shutil.rmtree(work_dir)
    print("工作目录已清理")
    print()

    print("要点:")
    print("  - Memory 是动态的，Agent 可以通过 edit_file 自主更新")
    print("  - system_prompt 是静态的，Memory 可以根据经验积累变化")
    print("  - 可以用 permissions 参数限制 Memory 为只读")
    print()


def demo3_readonly_memory():
    """
    Demo 3: 只读记忆
    通过 permissions 限制 Agent 不能修改 AGENTS.md。
    """
    print("=" * 50)
    print("Demo 3: 只读记忆")
    print("=" * 50)

    work_dir = tempfile.mkdtemp(prefix="deepagents_readonly_")

    with open(os.path.join(work_dir, "AGENTS.md"), "w", encoding="utf-8") as f:
        f.write("# 组织策略\n- 所有代码必须经过审查\n- 不允许使用 eval()\n")

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 通过 permissions 禁止写入 AGENTS.md
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
        backend=FilesystemBackend(root_dir=work_dir),
        permissions=permissions,
        system_prompt="你是一个编程助手。",
    )

    task = "请把 '我擅长 Python' 写入 AGENTS.md"
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})
    print("Agent 回复:")
    print(f"  {result['messages'][-1].content[:200]}")
    print()

    # 验证文件未被修改
    with open(os.path.join(work_dir, "AGENTS.md"), "r", encoding="utf-8") as f:
        content = f.read()
    print("AGENTS.md 内容（应未被修改）:")
    for line in content.split("\n"):
        print(f"  {line}")
    print()

    # 清理
    shutil.rmtree(work_dir)
    print("工作目录已清理")
    print()

    print("要点:")
    print("  - permissions 可以限制 Agent 对记忆文件的写操作")
    print("  - 适用于组织策略、合规规则等共享且不应被修改的内容")
    print()


def demo4_long_term_memory():
    """
    Demo 4: 跨会话长期记忆
    使用 CompositeBackend + StoreBackend 实现跨线程持久化。
    """
    print("=" * 50)
    print("Demo 4: 跨会话长期记忆")
    print("=" * 50)

    print("以下代码展示跨线程记忆的完整流程:")
    print()

    code = '''
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore
from langchain_core.utils.uuid import uuid7

# 创建 Store
store = InMemoryStore()

# 预置初始记忆
store.put(
    ("my-agent",),
    "/memories/AGENTS.md",
    create_file_data("## 回复风格\\n- 用中文回复\\n- 简洁直接\\n"),
)

# Agent 配置: /memories/ 路由到 StoreBackend
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
    system_prompt="你是一个助手。当用户告诉你偏好时，保存到 /memories/AGENTS.md。",
)

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
'''
    print("跨线程记忆代码:")
    for line in code.strip().split("\n"):
        print(f"  {line}")
    print()

    print("关键组件:")
    print("  - CompositeBackend: 混合后端，不同路径走不同存储")
    print("  - StoreBackend: 把文件存到 LangGraph Store，跨线程持久")
    print("  - routes: 路径映射，/memories/ 走 Store，其他走 StateBackend")
    print("  - store: Store 实例，InMemoryStore 用于开发，生产用 LangGraph Platform")
    print()

    print("作用域配置（通过 namespace 参数）:")
    print("  用户级别: namespace=lambda rt: (rt.server_info.user.identity,)")
    print("    每个用户独立记忆，互不干扰")
    print("  Agent 级别: namespace=lambda rt: (rt.server_info.assistant_id,)")
    print("    所有用户共享 Agent 记忆，适合 Agent 知识积累")
    print("  组织级别: namespace=lambda rt: (rt.context.org_id,)")
    print("    组织级策略，通常设为只读")
    print()


if __name__ == "__main__":
    print("DeepAgents 教程 - Step 5: Memory 记忆机制")
    print()

    demo1_basic_memory()
    demo2_memory_update()
    demo3_readonly_memory()
    demo4_long_term_memory()

    print("=" * 50)
    print("Step 5 完成!")
    print("=" * 50)
