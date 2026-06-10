"""
DeepAgents 教程 - Step 3: 文件系统操作

本示例演示 Deep Agent 的文件系统能力，
包括 StateBackend（内存）、FilesystemBackend（真实磁盘）、SandboxBackend（沙箱）的使用，
以及文件读写、编辑、权限控制。

Demo 5 (SandboxBackend) 需要额外的沙箱提供商依赖，请参考函数内说明。

依赖: deepagents>=0.6.4, langchain-deepseek, langgraph>=1.2.2
"""

import os
import tempfile
import shutil

from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import StateBackend, FilesystemBackend
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


def demo1_state_backend():
    """
    Demo 1: StateBackend（默认后端）
    文件存储在 Agent 的内存状态中，不会写入真实磁盘。
    适合对话场景中临时创建和操作文件。
    """
    print("=" * 50)
    print("Demo 1: StateBackend - 内存文件系统")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # StateBackend 是默认后端，文件存在 LangGraph 的状态中
    # 不需要显式指定 backend 参数
    # 这里为了演示，显式传入
    agent = create_deep_agent(
        model=llm,
        backend=StateBackend(),
        system_prompt="你是一个文件管理助手。请用中文回复。",
    )

    task = "请在 notes.txt 中写入以下内容:\n- Deep Agent 是 LangChain 的 Agent 框架\n- 内置文件系统支持\n- 支持子 Agent 和上下文管理\n\n写完后读取文件确认内容。"
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})

    # StateBackend 的文件存在 result["files"] 中
    print("Agent 执行过程:")
    for msg in result["messages"]:
        msg_type = type(msg).__name__
        if msg_type == "AIMessage" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"  调用: {tc['name']}({tc['args']})")
        elif msg_type == "ToolMessage":
            content = msg.content[:150] if len(msg.content) > 150 else msg.content
            print(f"  结果: {content}")
    print()

    # 查看内存中的文件
    if "files" in result:
        print("内存中的文件:")
        for path, file_info in result["files"].items():
            if isinstance(file_info, dict):
                content = file_info.get("content", str(file_info))
            else:
                content = str(file_info)
            print(f"  {path}:")
            for line in str(content).split("\n"):
                print(f"    {line}")
    print()

    print("StateBackend 特点:")
    print("  - 文件存储在 Agent 的状态中（内存），不会写入磁盘")
    print("  - 文件在对话线程内持久，跨线程不共享")
    print("  - 适合临时文件操作、代码生成等场景")
    print()


def demo2_filesystem_backend():
    """
    Demo 2: FilesystemBackend - 真实磁盘文件系统
    Agent 可以直接读写真实文件系统中的文件。
    适合本地开发工具、CLI 工具等场景。
    """
    print("=" * 50)
    print("Demo 2: FilesystemBackend - 真实磁盘文件系统")
    print("=" * 50)

    # 创建临时目录用于演示（避免污染项目目录）
    temp_dir = tempfile.mkdtemp(prefix="deepagents_demo_")
    print(f"临时工作目录: {temp_dir}")

    # 在临时目录中创建一个示例文件
    sample_file = os.path.join(temp_dir, "project_info.txt")
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write("项目名称: DeepAgents 学习项目\n")
        f.write("版本: 1.0.0\n")
        f.write("作者: 学员\n")
        f.write("描述: 学习 Deep Agent 的文件系统能力\n")
    print(f"已创建示例文件: {sample_file}")
    print()

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 创建使用 FilesystemBackend 的 Agent
    # root_dir: Agent 的根目录，所有文件操作基于此目录
    # virtual_mode=True: 启用虚拟路径模式，阻止路径遍历（如 ../、~）
    agent = create_deep_agent(
        model=llm,
        backend=FilesystemBackend(root_dir=temp_dir, virtual_mode=True),
        system_prompt="你是一个文件管理助手，可以读写文件。请用中文回复。",
    )

    # 任务: 读取文件并总结
    task = f"请读取 project_info.txt 文件的内容，然后总结一下这个项目的信息。"
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})

    last_msg = result["messages"][-1]
    print("Agent 回复:")
    print(f"  {last_msg.content}")
    print()

    # 验证文件仍然存在且未被修改
    print("验证文件内容（未被修改）:")
    with open(sample_file, "r", encoding="utf-8") as f:
        print(f"  {f.read()}")
    print()

    # 清理临时目录
    shutil.rmtree(temp_dir)
    print("临时目录已清理")
    print()


def demo3_file_edit():
    """
    Demo 3: Agent 编辑文件
    展示 Agent 的文件编辑能力（使用内置的 edit_file 工具）
    """
    print("=" * 50)
    print("Demo 3: Agent 编辑文件")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # 使用 StateBackend 进行文件编辑演示
    agent = create_deep_agent(
        model=llm,
        backend=StateBackend(),
        system_prompt="你是一个代码助手。请用中文回复。修改文件时保持格式整洁。",
    )

    # 先创建一个文件
    task1 = "请在 config.py 中写入以下内容:\n\ntitle = 'My App'\nversion = '1.0.0'\ndebug = True\nhost = 'localhost'\nport = 8000"
    print("步骤 1: 创建文件")
    print(f"  任务: {task1[:50]}...")
    result1 = agent.invoke({"messages": task1})
    print(f"  完成, 共 {len(result1['messages'])} 条消息")
    print()

    # 然后让 Agent 修改文件
    task2 = "请修改 config.py 文件: 把 debug 改为 False，把 port 改为 9000"
    print("步骤 2: 编辑文件")
    print(f"  任务: {task2}")
    result2 = agent.invoke({"messages": task2})
    print()

    # 查看编辑后的文件
    if "files" in result2:
        print("编辑后的文件内容:")
        for path, file_info in result2["files"].items():
            if isinstance(file_info, dict):
                content = file_info.get("content", str(file_info))
            else:
                content = str(file_info)
            print(f"  {path}:")
            for line in str(content).split("\n"):
                print(f"    {line}")
    print()

    # Agent 内置的文件编辑工具 edit_file 支持:
    # - 指定行范围替换
    # - 查找替换特定内容
    # - 追加内容
    print("Agent 文件编辑工具 (edit_file) 的能力:")
    print("  - 替换指定行的内容")
    print("  - 查找并替换文本")
    print("  - 在文件末尾追加内容")
    print("  - 删除指定行")
    print()


def demo4_permissions():
    """
    Demo 4: 文件权限控制
    展示 FilesystemPermission 的用法，控制 Agent 对文件的访问权限
    """
    print("=" * 50)
    print("Demo 4: 文件权限控制")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    temp_dir = tempfile.mkdtemp(prefix="deepagents_perm_")

    # 创建一些文件
    with open(os.path.join(temp_dir, "public.txt"), "w") as f:
        f.write("公开信息")
    with open(os.path.join(temp_dir, "secret.txt"), "w") as f:
        f.write("机密信息")

    print(f"工作目录: {temp_dir}")
    print("文件:")
    print("  - public.txt: 公开信息")
    print("  - secret.txt: 机密信息")
    print()

    # 设置权限: 只允许读写 public.txt，禁止访问 secret.txt
    permissions = [
        # 允许读写 public 开头的文件
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/public*"],
            mode="allow",
        ),
        # 禁止访问 secret 开头的文件
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/secret*"],
            mode="deny",
        ),
    ]

    agent = create_deep_agent(
        model=llm,
        backend=FilesystemBackend(root_dir=temp_dir, virtual_mode=True),
        permissions=permissions,
        system_prompt="你是一个助手。请用中文回复。",
    )

    print("权限配置:")
    print("  - 允许: 读写 public* 文件")
    print("  - 拒绝: 读写 secret* 文件")
    print()

    # 让 Agent 尝试读取两个文件
    task = "请读取 public.txt 和 secret.txt 的内容"
    print(f"用户任务: {task}")
    print()

    result = agent.invoke({"messages": task})

    last_msg = result["messages"][-1]
    print("Agent 回复:")
    print(f"  {last_msg.content}")
    print()

    # 清理
    shutil.rmtree(temp_dir)

    print("FilesystemPermission 规则:")
    print("  - operations: 控制的操作类型，'read'（读）或 'write'（写）")
    print("  - paths: 路径匹配模式，支持通配符 *")
    print("  - mode: 'allow'（允许）或 'deny'（拒绝）")
    print("  - 规则按声明顺序匹配，第一条匹配的规则生效")
    print("  - 如果没有规则匹配，默认允许")
    print()


def demo5_sandbox_backend():
    """
    Demo 5: SandboxBackend - 沙箱文件系统
    在远程沙箱中执行文件操作和 shell 命令，与本机完全隔离。
    需要第三方沙箱提供商（Daytona、Modal、Runloop、LangSmith）。

    本示例以 Daytona 为例，运行前需安装:
        pip install daytona-sdk langchain-daytona
    并配置 Daytona 的认证信息。
    """
    print("=" * 50)
    print("Demo 5: SandboxBackend - 沙箱文件系统")
    print("=" * 50)

    print("SandboxBackend 将文件操作和命令执行放在远程沙箱中。")
    print("支持四个沙箱提供商: Daytona、Modal、Runloop、LangSmith")
    print()

    # 以下代码以 Daytona 为例展示完整用法
    # 运行前需要: pip install daytona-sdk langchain-daytona
    sandbox_code = '''
from daytona import Daytona
from deepagents import create_deep_agent
from langchain_daytona import DaytonaSandbox

llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# 创建沙箱实例
sandbox = Daytona().create()
backend = DaytonaSandbox(sandbox=sandbox)

agent = create_deep_agent(
    model=llm,
    backend=backend,
    system_prompt="你是一个编程助手，可以在沙箱中创建和运行代码。请用中文回复。",
)

try:
    task = "创建一个 hello.py 文件，写入打印 Hello World 的代码，然后运行它"
    result = agent.invoke({"messages": task})
    print(result["messages"][-1].content)
finally:
    # 沙箱用完必须关闭，否则持续计费
    sandbox.stop()
'''
    print("Daytona 示例代码:")
    for line in sandbox_code.strip().split("\\n"):
        print(f"  {line}")
    print()

    # 文件传输示例
    transfer_code = '''
# 上传文件到沙箱（Agent 运行前准备环境）
backend.upload_files([
    ("/src/main.py", b"print('Hello from host')"),
    ("/requirements.txt", b"flask\\nrequests\\n"),
])

# 从沙箱下载文件（Agent 运行后获取产物）
results = backend.download_files(["/output/report.pdf"])
for r in results:
    if r.content is not None:
        print(f"下载成功: {r.path}, 大小: {len(r.content)} bytes")
'''
    print("文件传输示例（upload_files / download_files）:")
    for line in transfer_code.strip().split("\\n"):
        print(f"  {line}")
    print()

    # 其他提供商的示例
    print("其他沙箱提供商的用法结构相同，只是创建沙箱的方式不同:")
    print()
    print("  Modal:")
    print("    pip install modal langchain-modal")
    print("    sandbox = modal.Sandbox.create(app=modal.App.lookup('your-app'))")
    print("    backend = ModalSandbox(sandbox=sandbox)")
    print()
    print("  Runloop:")
    print("    pip install runloop langchain-runloop")
    print("    devbox = RunloopSDK(bearer_token=api_key).devbox.create()")
    print("    backend = RunloopSandbox(devbox=devbox)")
    print()
    print("  LangSmith:")
    print("    pip install langsmith")
    print("    ls_sandbox = SandboxClient().create_sandbox()")
    print("    backend = LangSmithSandbox(sandbox=ls_sandbox)")
    print()

    print("SandboxBackend 与其他后端的关键区别:")
    print("  - 提供 execute 工具，可在沙箱中执行任意 shell 命令")
    print("  - 文件操作和命令执行都在远程沙箱中，碰不到本机文件")
    print("  - 沙箱是远程资源，用完必须关闭（try/finally）")
    print()
    print("沙箱生命周期管理:")
    print("  - 线程级别: 每个对话一个沙箱，对话结束销毁")
    print("  - 助手级别: 同一助手共享一个沙箱，跨对话保持")
    print()


if __name__ == "__main__":
    print("DeepAgents 教程 - Step 3: 文件系统操作")
    print()

    demo1_state_backend()
    demo2_filesystem_backend()
    demo3_file_edit()
    demo4_permissions()
    demo5_sandbox_backend()

    print("=" * 50)
    print("Step 3 完成!")
    print("=" * 50)
