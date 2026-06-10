"""
DeepAgents 教程 - Step 6: 生产级 Agent

本示例演示如何构建一个生产级的 Deep Agent:
1. 完整的生产 Agent 配置（自定义工具 + 文件后端 + 角色定义）
2. 流式输出（Streaming）
3. 持久化记忆
4. 上下文管理
5. 完整的研究助手 Agent 示例
6. 部署概述

依赖: deepagents>=0.6.4, langchain-deepseek, langgraph>=1.2.2
"""

import os
import tempfile
import json
from pathlib import Path

from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ---------- 自定义工具 ----------

@tool
def search_info(query: str) -> str:
    """搜索信息。在实际项目中替换为真实的搜索 API（如 Tavily、Serper 等）。"""
    # 模拟搜索结果
    mock_data = {
        "LangChain": (
            "LangChain 最新版本更新:\n"
            "1. deepagents 0.6: 新增代码解释器、Harness Profiles、Streaming v3\n"
            "2. ContextHub: 自动上下文压缩和管理\n"
            "3. Delta Channels: 流式输出的增量更新\n"
            "4. langchain-deepseek: 官方 DeepSeek 集成包\n"
            "发布时间: 2026 年"
        ),
        "LangGraph": (
            "LangGraph 最新版本更新:\n"
            "1. 改进的状态管理机制\n"
            "2. 更高效的检查点序列化\n"
            "3. 新增 async subagent 支持\n"
            "4. 改进的流式输出性能"
        ),
    }
    for key, value in mock_data.items():
        if key.lower() in query.lower():
            return value
    return f"搜索 '{query}': 找到了若干相关结果。"


@tool
def calculate(expression: str) -> str:
    """执行数学计算。输入一个数学表达式，返回计算结果。"""
    try:
        # 安全起见，只允许基本的数学运算
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "错误: 表达式包含不允许的字符"
        result = eval(expression)  # noqa: S307
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


# ---------- Demo 函数 ----------

def demo1_production_agent_setup():
    """
    Demo 1: 完整的生产 Agent 配置

    生产级 Agent 的关键要素:
    - 清晰的角色定义（system_prompt）
    - 自定义工具集
    - FilesystemBackend（真实的文件读写）
    - Checkpointer（对话持久化）
    """
    print("=" * 50)
    print("Demo 1: 生产级 Agent 配置")
    print("=" * 50)

    # 工作目录
    work_dir = tempfile.mkdtemp(prefix="deepagent_production_")
    print(f"工作目录: {work_dir}")

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # FilesystemBackend: 文件读写操作作用于真实磁盘
    backend = FilesystemBackend(root_dir=work_dir)

    # MemorySaver: 内存检查点，用于对话持久化和 human-in-the-loop
    checkpointer = MemorySaver()

    # 创建生产级 Agent
    agent = create_deep_agent(
        model=llm,
        system_prompt=(
            "你是一个专业的研究助手。\n"
            "你的职责:\n"
            "  1. 根据用户的研究需求，使用 search_info 搜索信息\n"
            "  2. 使用 calculate 工具处理数值计算\n"
            "  3. 将研究结果整理成文档，保存到文件中\n"
            "  4. 输出结构清晰、引用准确的报告\n"
            "请用中文回复。保持专业和简洁。"
        ),
        tools=[search_info, calculate],
        backend=backend,
        checkpointer=checkpointer,
    )

    print()
    print("Agent 配置:")
    print("  - 模型: DeepSeek V4 Flash (deepseek-chat)")
    print("  - 自定义工具: search_info, calculate")
    print("  - 文件后端: FilesystemBackend（真实磁盘读写）")
    print("  - 检查点: MemorySaver（内存持久化）")
    print("  - 内置工具: write_todos, read_file, write_file, ls, glob, grep, edit_file, task")
    print()

    # 执行一个简单的任务
    task = "搜索一下 LangChain 的最新版本更新，然后告诉我主要的新特性。"
    print(f"任务: {task}")
    print()

    result = agent.invoke(
        {"messages": task},
        config={"configurable": {"thread_id": "demo1-session"}},
    )

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

    last_msg = result["messages"][-1]
    content = last_msg.content
    if len(content) > 500:
        content = content[:500] + "..."
    print("Agent 回复:")
    print(content)
    print()

    # 检查是否生成了文件
    print("工作目录中的文件:")
    for root, dirs, files in os.walk(work_dir):
        level = root.replace(work_dir, "").count(os.sep)
        indent = "  " * level
        print(f"  {indent}{os.path.basename(root)}/")
        for f in files[:10]:  # 最多显示 10 个文件
            print(f"  {indent}  {f}")
    print()


def demo2_streaming_output():
    """
    Demo 2: 流式输出

    agent.stream() 返回一个迭代器，可以实时获取 Agent 的执行过程。
    流式事件包括:
    - agent: Agent 的思考/回复
    - tools: 工具调用和结果
    每个事件带有 metadata，包含 lc_agent_name（Agent 名称）。
    """
    print("=" * 50)
    print("Demo 2: 流式输出 (Streaming)")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    work_dir = tempfile.mkdtemp(prefix="deepagent_stream_")
    backend = FilesystemBackend(root_dir=work_dir)

    agent = create_deep_agent(
        model=llm,
        system_prompt="你是一个简洁的助手。请用中文简短回复。",
        tools=[search_info],
        backend=backend,
        name="stream-demo-agent",
    )

    print("Agent 配置了 name='stream-demo-agent'")
    print("流式输出时，每个事件的 metadata 中包含 lc_agent_name 字段")
    print()

    task = "简单搜索一下 LangChain 的信息"
    print(f"任务: {task}")
    print()
    print("流式事件:")
    print("-" * 40)

    # agent.stream() 返回一个迭代器
    # 每次迭代返回一个字典，key 是节点名称，value 是该节点的输出
    event_count = 0
    for event in agent.stream({"messages": task}):
        event_count += 1
        for node_name, node_output in event.items():
            # node_name 可能是 "agent", "tools" 等
            if node_name == "agent":
                messages = node_output.get("messages", [])
                for msg in messages:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"  [事件 {event_count}] agent -> 调用工具: {tc['name']}")
                    elif msg.content:
                        content = msg.content[:100] if len(msg.content) > 100 else msg.content
                        print(f"  [事件 {event_count}] agent -> 回复: {content}")
            elif node_name == "tools":
                messages = node_output.get("messages", [])
                for msg in messages:
                    content = msg.content[:100] if len(msg.content) > 100 else msg.content
                    print(f"  [事件 {event_count}] tools -> 结果: {content}")

    print()
    print(f"共收到 {event_count} 个流式事件")
    print()

    print("流式输出的关键参数:")
    print("  - stream_mode: 控制返回的事件类型")
    print("    - 'values': 完整状态（默认）")
    print("    - 'updates': 增量更新")
    print("    - 'messages': 只返回消息增量")
    print("  - 子 Agent 流式: 子 Agent 的执行也会产生流式事件")
    print("    通过 lc_agent_name 区分不同 Agent 的事件")
    print()


def demo3_persistent_memory():
    """
    Demo 3: 持久化记忆概念

    Deep Agents 支持跨会话的持久化记忆:
    - StateBackend: 默认内存存储（简单，重启丢失）
    - FilesystemBackend: 真实文件系统（持久，适合单机）
    - StoreBackend: 键值存储（可接入外部数据库）
    - Checkpointer: 对话状态持久化（MemorySaver / 数据库）
    """
    print("=" * 50)
    print("Demo 3: 持久化记忆")
    print("=" * 50)

    print("Deep Agents 的记忆分为两层:")
    print()

    print("1. 对话状态持久化（Checkpointer）")
    print("-" * 40)
    print("通过 checkpointer 参数配置。")
    print("  - MemorySaver: 内存存储（默认，重启丢失）")
    print("  - SqliteSaver: SQLite 数据库（轻量持久化）")
    print("  - PostgresSaver: PostgreSQL（生产推荐）")
    print()
    print("配置示例:")
    print("  from langgraph.checkpoint.memory import MemorySaver")
    print("  agent = create_deep_agent(")
    print("      model=...,")
    print("      checkpointer=MemorySaver(),  # 或 PostgresSaver(conn_string)")
    print("  )")
    print("  # 使用 thread_id 区分不同会话")
    print("  result = agent.invoke(")
    print("      {'messages': '你好'},")
    print("      config={'configurable': {'thread_id': 'user-123'}},")
    print("  )")
    print()

    print("2. 跨会话记忆（Memory / AGENTS.md）")
    print("-" * 40)
    print("AGENTS.md 文件是持久化的项目级记忆:")
    print("  - 类似 Claude Code 的 CLAUDE.md")
    print("  - Agent 可以读写 AGENTS.md 来记住项目约定")
    print("  - 每次启动时自动加载")
    print()
    print("Memory 与 Skills 的区别:")
    print("  - Memory: 始终加载的上下文（AGENTS.md）")
    print("  - Skills: 按需加载的能力（SKILL.md）")
    print()

    print("3. Store 后端")
    print("-" * 40)
    print("StoreBackend 提供键值对存储:")
    print("  - InMemoryStore: 内存存储")
    print("  - 外部数据库: 可接入 Redis、PostgreSQL 等")
    print("  - 适合存储结构化的用户数据、配置信息")
    print()

    print("生产环境推荐方案:")
    print("  - Checkpointer: PostgresSaver（对话状态持久化）")
    print("  - Backend: FilesystemBackend 或 StoreBackend（文件/数据存储）")
    print("  - Memory: AGENTS.md + 项目级 Skills")
    print()


def demo4_context_management():
    """
    Demo 4: 上下文管理

    Deep Agents 内置上下文管理机制:
    - 自动压缩长对话
    - 工具输出可以卸载到磁盘
    - 通过子 Agent 隔离上下文
    """
    print("=" * 50)
    print("Demo 4: 上下文管理")
    print("=" * 50)

    print("Deep Agents 的上下文管理策略:")
    print()

    print("1. 自动上下文压缩")
    print("-" * 40)
    print("当对话历史超过上下文窗口限制时:")
    print("  - Deep Agents 自动压缩较早的对话历史")
    print("  - 保留关键信息的摘要，而不是丢弃")
    print("  - 压缩对用户透明，不需要手动干预")
    print("  - 0.6 版本的 ContextHub 统一管理上下文生命周期")
    print()

    print("2. 工具输出卸载到磁盘")
    print("-" * 40)
    print("工具调用可能返回大量数据（如搜索结果、文件内容）。")
    print("Deep Agents 可以:")
    print("  - 将大型工具输出保存到文件")
    print("  - 在上下文中只保留文件路径和摘要")
    print("  - 后续需要时通过文件路径重新读取")
    print()
    print("配置示例:")
    print("  # 在子 Agent 的 system_prompt 中指示保存大文件")
    print("  system_prompt = '''")
    print("  当你收集到大量数据时:")
    print("  1. 将原始数据保存到 /data/raw_results.txt")
    print("  2. 处理和分析数据")
    print("  3. 只返回分析摘要")
    print("  '''")
    print()

    print("3. 子 Agent 上下文隔离")
    print("-" * 40)
    print("子 Agent 是控制上下文的核心机制:")
    print("  - 每个子 Agent 有独立的上下文窗口")
    print("  - 大量中间输出不会影响主 Agent")
    print("  - 主 Agent 只接收子 Agent 的最终结果")
    print("  - 适合搜索、代码分析等产生大量中间结果的场景")
    print()

    print("4. 上下文管理最佳实践")
    print("-" * 40)
    print("  - 要求子 Agent 返回简洁摘要（如限制 300-500 字）")
    print("  - 大文件内容写入磁盘，不在上下文中保留全文")
    print("  - 复杂任务分解给子 Agent，保持主 Agent 上下文干净")
    print("  - 使用 response_format 让子 Agent 返回结构化数据")
    print("  - 合理使用 checkpointer 支持长对话的断点续传")
    print()


def demo5_research_assistant():
    """
    Demo 5: 完整的研究助手 Agent

    综合运用所有特性:
    - 自定义工具（search_info, calculate）
    - 任务规划（内置 TodoList）
    - 文件管理（FilesystemBackend）
    - 子 Agent（内置 general-purpose）
    - Checkpointer（对话持久化）
    """
    print("=" * 50)
    print("Demo 5: 完整的研究助手 Agent")
    print("=" * 50)

    # 准备工作目录
    work_dir = tempfile.mkdtemp(prefix="deepagent_research_")
    # 创建输出目录
    os.makedirs(os.path.join(work_dir, "output"), exist_ok=True)

    print(f"工作目录: {work_dir}")
    print()

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    backend = FilesystemBackend(root_dir=work_dir)
    checkpointer = MemorySaver()

    # 创建完整的研究助手
    agent = create_deep_agent(
        model=llm,
        system_prompt=(
            "你是一个专业的研究助手。\n\n"
            "工作流程:\n"
            "  1. 收到研究任务后，先用 write_todos 规划研究步骤\n"
            "  2. 使用 search_info 搜索相关信息\n"
            "  3. 整理搜索结果，提取关键信息\n"
            "  4. 将研究报告保存到 /output/report.md 文件\n"
            "  5. 向用户简要总结研究发现\n\n"
            "报告格式:\n"
            "  - 标题\n"
            "  - 概述\n"
            "  - 主要发现\n"
            "  - 结论\n"
            "请用中文撰写报告。"
        ),
        tools=[search_info, calculate],
        backend=backend,
        checkpointer=checkpointer,
        name="research-assistant",
    )

    print("研究助手 Agent 配置:")
    print("  - 角色: 专业研究助手")
    print("  - 工具: search_info, calculate + 内置文件工具")
    print("  - 后端: FilesystemBackend")
    print("  - 检查点: MemorySaver")
    print("  - 名称: research-assistant（用于流式追踪）")
    print()

    # 执行完整的研究任务
    task = "研究 LangChain 的最新版本更新，写一份摘要报告保存到 /output/report.md"
    print(f"任务: {task}")
    print()
    print("执行过程:")
    print("-" * 40)

    result = agent.invoke(
        {"messages": task},
        config={"configurable": {"thread_id": "research-session-1"}},
    )

    # 详细展示执行过程
    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__
        if msg_type == "HumanMessage":
            print(f"  [{i}] 用户: {msg.content}")
        elif msg_type == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    args_preview = str(tc.get("args", ""))
                    if len(args_preview) > 80:
                        args_preview = args_preview[:80] + "..."
                    print(f"  [{i}] Agent 调用: {tc['name']}({args_preview})")
            else:
                content = msg.content[:200] if len(msg.content) > 200 else msg.content
                print(f"  [{i}] Agent 回复: {content}")
        elif msg_type == "ToolMessage":
            content = msg.content[:120] if len(msg.content) > 120 else msg.content
            print(f"  [{i}] 工具结果: {content}")

    print()

    # 检查生成的文件
    output_dir = os.path.join(work_dir, "output")
    if os.path.exists(output_dir):
        print("生成的文件:")
        for f in os.listdir(output_dir):
            file_path = os.path.join(output_dir, f)
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                    size = len(content)
                    print(f"  - {f} ({size} 字)")
                    # 显示文件前几行
                    lines = content.split("\n")[:10]
                    for line in lines:
                        print(f"    {line}")
                    if len(content.split("\n")) > 10:
                        print(f"    ... (共 {len(content.split(chr(10)))} 行)")
    print()

    # 统计
    tool_calls = {}
    for msg in result["messages"]:
        if type(msg).__name__ == "AIMessage" and hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                name = tc["name"]
                tool_calls[name] = tool_calls.get(name, 0) + 1

    print("工具调用统计:")
    for name, count in tool_calls.items():
        print(f"  - {name}: {count} 次")
    print(f"  - 总消息数: {len(result['messages'])}")
    print()


def demo6_deployment_overview():
    """
    Demo 6: 部署概述

    介绍 Deep Agent 从开发到生产的部署路径。
    """
    print("=" * 50)
    print("Demo 6: 部署概述")
    print("=" * 50)

    print("Deep Agent 的部署路径:")
    print()

    print("1. 本地开发")
    print("-" * 40)
    print("  - 直接 Python 运行: python agent.py")
    print("  - 适合快速迭代和调试")
    print("  - 使用 MemorySaver + StateBackend 即可")
    print()

    print("2. LangGraph 开发服务器")
    print("-" * 40)
    print("  - 命令: langgraph dev")
    print("  - 提供热重载、Web UI、API 端点")
    print("  - 适合在类生产环境中测试")
    print("  - 自动生成 REST API 和 WebSocket 端点")
    print()

    print("3. 生产部署")
    print("-" * 40)
    print("  - 命令: langgraph deploy")
    print("  - 部署到 LangGraph Cloud（LangChain 官方托管）")
    print("  - 或使用 LangGraph Server 自行部署到 Kubernetes 等")
    print("  - 支持水平扩展、自动容错")
    print("  - 关键配置:")
    print("    * Checkpointer: PostgresSaver（持久化对话状态）")
    print("    * Store: PostgreSQL 或 Redis（持久化数据）")
    print("    * Backend: FilesystemBackend 或 StoreBackend")
    print()

    print("4. LangSmith 集成")
    print("-" * 40)
    print("LangSmith 是 LangChain 的可观测性平台:")
    print("  - Tracing: 追踪每次 Agent 调用的完整链路")
    print("  - Evaluation: 自动评估 Agent 输出质量")
    print("  - Monitoring: 实时监控延迟、成本、错误率")
    print("  - 支持子 Agent 的独立追踪（通过 lc_agent_name）")
    print()
    print("配置示例:")
    print("  export LANGSMITH_API_KEY=your-key")
    print("  export LANGSMITH_TRACING=true")
    print("  # Agent 运行时会自动上报追踪数据到 LangSmith")
    print()

    print("5. 生产环境关键考量")
    print("-" * 40)
    print("  - 安全: 在工具/沙箱层面限制 Agent 权限，不要期望模型自我约束")
    print("  - 成本: 监控 token 使用量，合理使用上下文管理和子 Agent")
    print("  - 可靠性: 使用 Checkpointer 支持断点续传和重试")
    print("  - 可观测: 集成 LangSmith 追踪每次调用")
    print("  - 扩展性: 无状态设计 + 持久化存储，支持水平扩展")
    print("  - 人机协作: 通过 interrupt_on 配置需要人工确认的操作")
    print("  - 模型选择: 不同子 Agent 可以用不同模型（如推理用强模型，写作用快模型）")
    print()

    print("6. 配置文件结构（生产推荐）")
    print("-" * 40)
    print("  project/")
    print("    agent.py              # Agent 定义")
    print("    tools/                # 自定义工具")
    print("    skills/               # 技能文件")
    print("    langgraph.json        # LangGraph 部署配置")
    print("    requirements.txt      # 依赖")
    print("    .env                  # 环境变量（API keys 等）")
    print()

    print("langgraph.json 配置示例:")
    config_example = {
        "python_version": "3.11",
        "dependencies": ["."],
        "graphs": {
            "research_agent": "./agent.py:graph"
        },
        "env": ".env"
    }
    print(f"  {json.dumps(config_example, indent=4, ensure_ascii=False)}")


if __name__ == "__main__":
    print("DeepAgents 教程 - Step 6: 生产级 Agent")
    print()

    demo1_production_agent_setup()
    demo2_streaming_output()
    demo3_persistent_memory()
    demo4_context_management()
    demo5_research_assistant()
    demo6_deployment_overview()

    print("=" * 50)
    print("Step 6 完成! DeepAgents 教程全部结束!")
    print("=" * 50)
