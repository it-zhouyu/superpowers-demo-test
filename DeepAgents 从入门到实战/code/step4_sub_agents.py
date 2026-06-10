"""
DeepAgents 教程 - Step 4: Sub-Agents 与任务委派

本示例演示 Deep Agent 的子 Agent（Sub-Agent）机制:
1. 创建带子 Agent 的主 Agent（协调者）
2. 任务分解与委派流程
3. 子 Agent 的核心概念

子 Agent 解决"上下文膨胀"问题——主 Agent 只接收最终结果，
不会被大量中间工具调用输出撑满上下文窗口。

依赖: deepagents>=0.6.4, langchain-deepseek, langgraph>=1.2.2
"""

from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool
from deepagents import create_deep_agent
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ---------- 自定义工具 ----------

@tool
def search_web(query: str) -> str:
    """模拟网络搜索，返回搜索结果。在实际项目中可替换为 Tavily/Serper 等真实搜索 API。"""
    # 模拟搜索结果
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
        "asyncio 教程": (
            "asyncio 进阶主题:\n"
            "1. gather vs wait vs as_completed\n"
            "2. Semaphore 控制并发数\n"
            "3. Queue 实现生产者-消费者模式\n"
            "4. 子进程管理: asyncio.create_subprocess_exec\n"
            "5. 信号处理与优雅关闭"
        ),
    }
    # 简单匹配
    for key, value in mock_results.items():
        if key in query or any(word in query for word in key.split()):
            return value
    return f"搜索 '{query}' 的结果: 找到了 3 篇相关文章和 2 个示例项目。"


@tool
def write_document(title: str, content: str) -> str:
    """将内容写入文档（模拟）。在实际项目中可配合 Deep Agent 的文件系统后端使用。"""
    return f"文档 '{title}' 已写入完成，共 {len(content)} 字。内容:\n{content}"


def demo1_main_agent_with_subagents():
    """
    Demo 1: 创建带子 Agent 的主 Agent

    subagents 参数接受一个列表，列表中的每个元素是一个字典（SubAgent 规格）。
    每个 SubAgent 必须有:
      - name: 唯一标识符，主 Agent 通过 task() 工具调用时使用这个名称
      - description: 描述子 Agent 的能力，主 Agent 据此决定何时委派任务
      - system_prompt: 子 Agent 的系统提示词（不会继承主 Agent 的）

    可选字段:
      - tools: 子 Agent 可用的工具（不设置则继承主 Agent 的工具）
      - model: 覆盖主 Agent 的模型
      - middleware: 额外的中间件
      - skills: 子 Agent 专属的技能路径
    """
    print("=" * 50)
    print("Demo 1: 创建带子 Agent 的主 Agent")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 定义研究子 Agent —— 擅长搜索和整理信息
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

    # 定义写作子 Agent —— 擅长内容创作
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

    # 创建主 Agent（协调者）
    # 主 Agent 会获得一个内置的 task() 工具，用于调用子 Agent
    # 系统提示词中明确告诉主 Agent 何时委派任务
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

    print("主 Agent 创建成功，配置了以下子 Agent:")
    print("  - research-agent: 负责搜索和整理信息")
    print("  - writing-agent: 负责撰写文档和大纲")
    print()
    print("子 Agent 工作流程:")
    print("  1. 主 Agent 收到用户任务")
    print("  2. 主 Agent 通过 task() 工具委派任务给子 Agent")
    print("  3. 子 Agent 在隔离的上下文中执行任务")
    print("  4. 子 Agent 返回结果给主 Agent")
    print("  5. 主 Agent 汇总结果回复用户")
    print()

    # 给主 Agent 一个需要委派的任务
    task_text = "帮我简单了解一下 Python 异步编程的基本概念，用两三句话概括就行。"
    print(f"用户任务: {task_text}")
    print()

    result = agent.invoke({"messages": task_text})

    # 展示执行过程
    print("执行过程:")
    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__
        if msg_type == "HumanMessage":
            print(f"  [{i}] 用户: {msg.content}")
        elif msg_type == "AIMessage":
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc["name"]
                    # task() 工具调用表示委派给子 Agent
                    if tool_name == "task":
                        args = tc["args"]
                        subagent_name = args.get("name", "unknown")
                        subagent_task = args.get("description", "")
                        print(f"  [{i}] 主 Agent 委派任务给: {subagent_name}")
                        print(f"       任务描述: {subagent_task[:100]}")
                    else:
                        print(f"  [{i}] Agent 调用工具: {tool_name}")
            else:
                content = msg.content[:300] if len(msg.content) > 300 else msg.content
                print(f"  [{i}] Agent 回复: {content}")
        elif msg_type == "ToolMessage":
            content = msg.content[:200] if len(msg.content) > 200 else msg.content
            print(f"  [{i}] 工具结果: {content}")
    print()


def demo2_task_decomposition():
    """
    Demo 2: 任务分解与委派

    复杂任务会被主 Agent 分解为多个子任务，分别委派给不同的子 Agent。
    这是 Deep Agent 处理多步骤任务的核心模式。

    本示例的任务: "研究 Python 的异步编程模型，然后写一份教程大纲"
    分解为:
      - 子任务 1: 研究异步编程（委派给 research-agent）
      - 子任务 2: 根据研究结果写教程大纲（委派给 writing-agent）
    """
    print("=" * 50)
    print("Demo 2: 任务分解与委派")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 研究子 Agent
    research_subagent = {
        "name": "research-agent",
        "description": (
            "深入调研特定技术主题。"
            "使用 search_web 搜索相关信息，整理成结构化的研究摘要。"
            "当需要了解某个技术领域、收集资料时使用。"
        ),
        "system_prompt": (
            "你是一个专业的研究员。\n"
            "根据给定的研究主题，使用 search_web 工具搜索相关信息。\n"
            "整理搜索结果，返回结构化的研究摘要。\n"
            "输出格式:\n"
            "  - 核心概念（3-5 条）\n"
            "  - 关键技术点（3-5 条）\n"
            "  - 推荐学习路径\n"
            "保持简洁，不超过 400 字。用中文回复。"
        ),
        "tools": [search_web],
    }

    # 写作子 Agent
    writing_subagent = {
        "name": "writing-agent",
        "description": (
            "根据研究资料撰写技术文档和教程大纲。"
            "当需要整理研究结果、生成结构化文档时使用。"
        ),
        "system_prompt": (
            "你是一个技术写作专家。\n"
            "根据提供的研究资料，撰写教程大纲。\n"
            "大纲要求:\n"
            "  - 由浅入深，从基础到进阶\n"
            "  - 每章包含 3-5 个小节\n"
            "  - 每个小节有简短说明（一句话）\n"
            "用中文回复。"
        ),
        "tools": [write_document],
    }

    # 主 Agent 作为协调者
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

    # 复杂任务
    complex_task = "研究 Python 的异步编程模型，然后写一份教程大纲"
    print(f"复杂任务: {complex_task}")
    print()
    print("预期的任务分解:")
    print("  步骤 1: research-agent 调研 Python 异步编程")
    print("  步骤 2: writing-agent 根据研究结果写教程大纲")
    print()

    result = agent.invoke({"messages": complex_task})

    # 分析委派流程
    print("实际执行流程:")
    delegation_count = 0
    tool_count = 0
    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "task":
                    delegation_count += 1
                    args = tc["args"]
                    subagent_name = args.get("name", "unknown")
                    print(f"  委派 #{delegation_count} -> {subagent_name}")
                else:
                    tool_count += 1
                    print(f"  直接调用工具: {tc['name']}")

    print()
    print(f"统计: 共委派 {delegation_count} 次子 Agent，直接调用 {tool_count} 次工具")
    print()

    # 打印最终回复
    last_msg = result["messages"][-1]
    content = last_msg.content
    if len(content) > 500:
        content = content[:500] + "..."
    print("最终回复:")
    print(f"  {content}")
    print()


def demo3_subagent_concepts():
    """
    Demo 3: 子 Agent 核心概念讲解

    通过 print 展示子 Agent 机制的关键概念和设计原则。
    """
    print("=" * 50)
    print("Demo 3: 子 Agent 核心概念")
    print("=" * 50)

    print("1. 独立的上下文窗口")
    print("-" * 40)
    print("每个子 Agent 拥有独立的上下文窗口（Context Window），与主 Agent 隔离。")
    print("这意味着:")
    print("  - 子 Agent 执行过程中的工具调用、中间结果不会占用主 Agent 的上下文")
    print("  - 主 Agent 只接收子 Agent 的最终结果（一条 ToolMessage）")
    print("  - 适合处理会产生大量中间输出的任务（如搜索、代码分析）")
    print()

    print("2. 主 Agent 管理整体计划")
    print("-" * 40)
    print("主 Agent 是协调者，负责:")
    print("  - 分析用户任务，决定是否需要委派")
    print("  - 选择合适的子 Agent（基于 description 字段）")
    print("  - 通过 task() 工具传递任务描述给子 Agent")
    print("  - 汇总多个子 Agent 的结果")
    print("  - 如果子 Agent 结果不满意，可以重新委派")
    print()

    print("3. 子 Agent 的类型")
    print("-" * 40)
    print("Deep Agents 提供两种子 Agent:")
    print()
    print("  (1) 字典型 SubAgent（常用）:")
    print("      通过字典定义，指定 name/description/system_prompt/tools 等")
    print("      适合大多数场景，代码简洁")
    print()
    print("  (2) CompiledSubAgent（高级）:")
    print("      通过 LangGraph 的 CompiledStateGraph 定义")
    print("      适合需要自定义工作流图的复杂场景")
    print("      可以用 create_agent() 或自定义 StateGraph 构建")
    print()

    print("4. 内置的 general-purpose 子 Agent")
    print("-" * 40)
    print("每个 Deep Agent 自动拥有一个名为 'general-purpose' 的子 Agent。")
    print("  - 自动继承主 Agent 的工具和技能")
    print("  - 用于通用的上下文隔离（不需要专门配置）")
    print("  - 可以通过在 subagents 中定义 name='general-purpose' 来覆盖")
    print("  - 可以通过 harness profile 配置禁用它")
    print()

    print("5. 何时使用子 Agent")
    print("-" * 40)
    print("适合使用的场景:")
    print("  - 多步骤任务，会产出大量中间结果")
    print("  - 需要专门的指令或工具集")
    print("  - 不同子任务需要不同的模型能力")
    print("  - 希望主 Agent 专注于高层协调")
    print()
    print("不适合使用的场景:")
    print("  - 简单的单步任务")
    print("  - 需要保留中间上下文的场景")
    print("  - 委派的开销大于收益的情况")
    print()

    print("6. 结构化输出（response_format）")
    print("-" * 40)
    print("子 Agent 支持 response_format 参数，让返回结果是结构化的 JSON。")
    print("主 Agent 可以更可靠地解析子 Agent 的输出。")
    print("支持 Pydantic 模型、ToolStrategy、ProviderStrategy 等。")
    print()

    print("7. 最佳实践")
    print("-" * 40)
    print("  - description 要具体，主 Agent 据此选择子 Agent")
    print("  - system_prompt 要详细，包含工具使用指导和输出格式要求")
    print("  - tools 尽量精简，只给子 Agent 必要的工具")
    print("  - 要求子 Agent 返回简洁摘要，不要返回原始数据")
    print("  - 可以给不同子 Agent 指定不同模型（如推理用强模型、写作用快模型）")


if __name__ == "__main__":
    print("DeepAgents 教程 - Step 4: Sub-Agents 与任务委派")
    print()

    demo1_main_agent_with_subagents()
    demo2_task_decomposition()
    demo3_subagent_concepts()

    print("=" * 50)
    print("Step 4 完成!")
    print("=" * 50)
