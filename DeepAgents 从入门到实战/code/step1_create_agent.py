"""
DeepAgents 教程 - Step 1: 创建你的第一个 Deep Agent

本示例演示如何使用 deepagents 库创建一个 Deep Agent，
包括最基础的创建方式、带规划能力的 Agent，以及展示内置能力。

依赖: deepagents>=0.6.4, langchain-deepseek, langgraph>=1.2.2
"""

from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


def demo1_minimal_agent():
    """
    Demo 1: 最简 Agent
    只需要 model 和 system_prompt 就能创建一个可用的 Deep Agent
    """
    print("=" * 50)
    print("Demo 1: 最简 Deep Agent")
    print("=" * 50)

    # 创建 DeepSeek LLM 实例
    # Deep Agent 的 model 参数支持两种形式:
    #   1. "provider:model_name" 字符串，如 "deepseek:deepseek-chat"
    #   2. 直接传入 BaseChatModel 实例（我们用这种方式，因为 langchain-deepseek 需要单独配置 base_url）
    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 创建最简 Agent
    # create_deep_agent 返回一个 LangGraph 的 CompiledStateGraph
    # 默认自带工具: write_todos(任务清单), ls/read_file/write_file/edit_file/glob/grep(文件操作), execute(命令执行), task(子Agent调用)
    agent = create_deep_agent(
        model=llm,
        system_prompt="你是一个友好的中文助手，请用简洁的中文回答问题。",
    )

    print(f"Agent 类型: {type(agent).__name__}")
    print("Agent 创建成功，默认自带以下工具:")
    print("  - write_todos: 任务清单管理")
    print("  - ls, read_file, write_file, edit_file, glob, grep: 文件操作")
    print("  - execute: 执行命令(需要沙箱后端)")
    print("  - task: 调用子 Agent")
    print()

    # 调用 Agent
    # 输入格式和 LangGraph 的 StateGraph 一致，传 {"messages": "..."} 即可
    result = agent.invoke({"messages": "你好，请用一句话介绍一下你自己"})

    # result 是一个字典，包含 messages 等字段
    # messages 是完整对话历史（包括用户的输入和 Agent 的所有回复）
    print("Agent 回复:")
    # 最后一条消息就是 Agent 的最终回复
    last_message = result["messages"][-1]
    print(f"  {last_message.content}")
    print()
    print(f"完整对话包含 {len(result['messages'])} 条消息")
    print()


def demo2_planning_agent():
    """
    Demo 2: 展示 Agent 的规划能力
    Deep Agent 自带 TodoListMiddleware，会在处理复杂任务时自动规划步骤
    """
    print("=" * 50)
    print("Demo 2: Agent 的规划能力")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    agent = create_deep_agent(
        model=llm,
        system_prompt="你是一个项目经理助手，擅长拆分任务和制定计划。请用中文回复。",
    )

    # 给 Agent 一个多步骤任务
    # Agent 会自动使用 write_todos 工具来规划任务步骤
    task = (
        "我需要准备一个技术分享的演讲，主题是'Deep Agent 入门'。"
        "请帮我规划一下准备工作的步骤，包括: 调研主题、编写大纲、准备代码示例、制作 PPT。"
    )
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})

    # 遍历消息，展示 Agent 的思考过程
    print("Agent 执行过程:")
    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__
        # HumanMessage: 用户输入
        # AIMessage: Agent 的回复（包括工具调用）
        # ToolMessage: 工具执行结果
        if msg_type == "HumanMessage":
            print(f"  [{i}] 用户: {msg.content}")
        elif msg_type == "AIMessage":
            # 检查是否有工具调用
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"  [{i}] Agent 调用工具: {tc['name']}")
                    # 简化显示参数
                    args_str = str(tc["args"])
                    if len(args_str) > 100:
                        args_str = args_str[:100] + "..."
                    print(f"       参数: {args_str}")
            else:
                content = msg.content[:200] if len(msg.content) > 200 else msg.content
                print(f"  [{i}] Agent 回复: {content}")
        elif msg_type == "ToolMessage":
            content = msg.content[:150] if len(msg.content) > 150 else msg.content
            print(f"  [{i}] 工具结果: {content}")
    print()


def demo3_builtin_capabilities():
    """
    Demo 3: 展示 Agent 的内置能力
    Deep Agent 默认使用 StateBackend（内存存储），文件操作在内存中进行
    """
    print("=" * 50)
    print("Demo 3: Agent 内置能力展示")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 默认使用 StateBackend，文件存储在 Agent 的状态中（内存）
    agent = create_deep_agent(
        model=llm,
        system_prompt="你是一个开发助手。请用中文回复。当需要管理任务时，使用 write_todos 工具。",
    )

    # 给一个需要规划和文件操作的任务
    task = (
        "请帮我完成以下工作:\n"
        "1. 创建一个名为 notes.txt 的文件，写入三行笔记，内容是关于 Deep Agent 的核心特性\n"
        "2. 然后读取这个文件，确认内容正确\n"
        "3. 最后总结一下你刚才做了什么"
    )
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})

    # 统计工具调用情况
    tool_calls = {}
    for msg in result["messages"]:
        if type(msg).__name__ == "AIMessage" and hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                name = tc["name"]
                tool_calls[name] = tool_calls.get(name, 0) + 1

    print("工具调用统计:")
    for name, count in tool_calls.items():
        print(f"  - {name}: 调用了 {count} 次")
    print()

    # 打印最终回复
    last_msg = result["messages"][-1]
    print("Agent 最终回复:")
    print(f"  {last_msg.content}")
    print()

    # 展示结果中的文件状态
    # StateBackend 的文件存在 result 的 files 字段中
    if "files" in result:
        print("Agent 创建的文件:")
        for path, content in result["files"].items():
            print(f"  {path}:")
            content_str = str(content)
            print(f"    {content_str[:200]}")
    print()

    print("总结:")
    print("  - Deep Agent 默认使用 StateBackend，文件存在内存中，不会写入真实磁盘")
    print("  - Agent 会自动规划任务步骤、调用工具、管理上下文")
    print("  - 如果需要真实的文件操作，可以使用 FilesystemBackend（后续示例会演示）")


if __name__ == "__main__":
    print("DeepAgents 教程 - Step 1: 创建你的第一个 Deep Agent")
    print()

    demo1_minimal_agent()
    demo2_planning_agent()
    demo3_builtin_capabilities()

    print("=" * 50)
    print("Step 1 完成!")
    print("=" * 50)
