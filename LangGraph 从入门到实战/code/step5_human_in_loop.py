"""
LangGraph 教程 - Step 5: Human-in-the-Loop（人工介入）

演示 interrupt + checkpoint + resume 模式：
1. 工具执行前暂停，等待人工审批
2. 审批通过后继续执行
3. 审批拒绝后取消操作
4. 用 get_state() 检查暂停状态
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 定义需要人工审批的工具
# ============================================================

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件（需要人工审批）

    Args:
        to: 收件人邮箱地址
        subject: 邮件主题
        body: 邮件正文
    """
    # 调用 interrupt 暂停图执行，向用户展示审批请求
    # 用户恢复时传入的值就是 interrupt 的返回值
    approval = interrupt(
        f"即将发送邮件:\n"
        f"  收件人: {to}\n"
        f"  主题: {subject}\n"
        f"  正文: {body}\n"
        f"是否确认发送？"
    )

    # 根据用户恢复时传入的决定执行不同逻辑
    if approval.get("action") == "approve":
        return f"邮件已成功发送至 {to}"
    else:
        return "邮件发送已取消"


@tool
def search_contacts(query: str) -> str:
    """搜索联系人"""
    contacts = {
        "张三": "zhangsan@example.com",
        "李四": "lisi@example.com",
        "王五": "wangwu@example.com",
    }
    results = []
    for name, email in contacts.items():
        if query in name or query in email:
            results.append(f"{name}: {email}")
    return "\n".join(results) if results else "未找到匹配的联系人"


# ============================================================
# 创建 LLM 实例
# ============================================================

llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    api_base=DEEPSEEK_BASE_URL,
)


# ============================================================
# Demo 1: 审批通过 - 发送邮件
# ============================================================

def demo1_approve():
    """Demo 1: 人工审批通过后发送邮件"""
    print("=" * 50)
    print("Demo 1: 人工审批 - 通过")
    print("=" * 50)

    # 创建带 checkpointer 的 agent（interrupt 必须启用 checkpointer）
    checkpointer = MemorySaver()
    tools = [send_email, search_contacts]

    app = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
    )

    # 配置线程 ID（每个独立对话使用不同的 thread_id）
    thread_id = "demo-1-approve"
    config = {"configurable": {"thread_id": thread_id}}

    # 第一次调用：LLM 会决定调用 send_email 工具，工具内部触发 interrupt 暂停
    print("\n--- 第一次调用: 触发工具调用 ---")
    result = app.invoke(
        {"messages": [{"role": "user", "content": "帮我给张三发一封邮件，主题是'项目进度更新'，正文是'本周项目进展顺利，已完成核心功能开发。'"}]},
        config,
    )
    print(f"结果类型: {type(result)}")

    # 检查暂停状态
    state = app.get_state(config)
    print(f"\n--- 暂停状态检查 ---")
    print(f"下一条待执行: {state.next}")
    if state.tasks:
        for task in state.tasks:
            print(f"任务 ID: {task.id}")
            if task.interrupts:
                for intr in task.interrupts:
                    print(f"中断信息: {intr.value}")

    # 恢复执行：传入审批通过的决定
    print("\n--- 恢复执行: 审批通过 ---")
    result = app.invoke(
        Command(resume={"action": "approve"}),
        config,
    )
    print(f"最终结果: {result['messages'][-1].content}")

    # 查看完整消息历史
    print(f"\n--- 完整消息历史（共 {len(result['messages'])} 条）---")
    for i, msg in enumerate(result["messages"]):
        role = type(msg).__name__
        content = msg.content[:100] if len(msg.content) > 100 else msg.content
        print(f"  [{i}] {role}: {content}")


# ============================================================
# Demo 2: 审批拒绝 - 取消发送
# ============================================================

def demo2_reject():
    """Demo 2: 人工审批拒绝，取消发送"""
    print("\n" + "=" * 50)
    print("Demo 2: 人工审批 - 拒绝")
    print("=" * 50)

    checkpointer = MemorySaver()
    tools = [send_email, search_contacts]

    app = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
    )

    # 使用不同的 thread_id 隔离对话
    thread_id = "demo-2-reject"
    config = {"configurable": {"thread_id": thread_id}}

    # 触发工具调用
    print("\n--- 第一次调用: 触发工具调用 ---")
    result = app.invoke(
        {"messages": [{"role": "user", "content": "帮我给李四发邮件，主题是'会议通知'，正文是'明天下午3点开项目评审会。'"}]},
        config,
    )

    # 检查暂停状态
    state = app.get_state(config)
    print(f"暂停状态 - next: {state.next}")
    if state.tasks:
        for task in state.tasks:
            if task.interrupts:
                for intr in task.interrupts:
                    print(f"中断信息: {intr.value}")

    # 恢复执行：传入拒绝决定
    print("\n--- 恢复执行: 审批拒绝 ---")
    result = app.invoke(
        Command(resume={"action": "reject"}),
        config,
    )
    print(f"最终结果: {result['messages'][-1].content}")


# ============================================================
# Demo 3: 用 get_state() 检查状态
# ============================================================

def demo3_inspect_state():
    """Demo 3: 使用 get_state() 检查暂停状态"""
    print("\n" + "=" * 50)
    print("Demo 3: 状态检查")
    print("=" * 50)

    checkpointer = MemorySaver()
    tools = [send_email]

    app = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
    )

    thread_id = "demo-3-inspect"
    config = {"configurable": {"thread_id": thread_id}}

    # 触发 interrupt
    print("\n--- 触发中断 ---")
    app.invoke(
        {"messages": [{"role": "user", "content": "发邮件给 test@example.com，主题'测试'，正文'这是一封测试邮件'"}]},
        config,
    )

    # 详细检查状态
    state = app.get_state(config)

    print(f"\n--- 状态详情 ---")
    print(f"当前待执行节点: {state.next}")
    print(f"已执行节点: {state.created_at}")
    print(f"父状态配置: {state.parent_config}")

    # 查看消息历史
    print(f"\n--- 已有消息 ---")
    for i, msg in enumerate(state.values.get("messages", [])):
        role = type(msg).__name__
        content = msg.content[:80] if len(msg.content) > 80 else msg.content
        print(f"  [{i}] {role}: {content}")

    # 查看 interrupt 详情
    print(f"\n--- 中断信息 ---")
    if state.tasks:
        for task in state.tasks:
            print(f"  任务: {task.name} (id: {task.id})")
            if task.interrupts:
                for intr in task.interrupts:
                    print(f"  中断值: {intr.value}")
                    print(f"  中断 ID: {intr.id}")
    else:
        print("  无活跃中断")

    # 查看状态历史
    print(f"\n--- 状态历史 ---")
    history_count = 0
    for hist_state in app.get_state_history(config):
        history_count += 1
        if history_count <= 5:
            print(f"  状态 {history_count}: next={hist_state.next}, "
                  f"消息数={len(hist_state.values.get('messages', []))}")
    print(f"  共 {history_count} 个历史状态")

    # 清理：恢复并取消
    print("\n--- 恢复并取消 ---")
    result = app.invoke(
        Command(resume={"action": "reject"}),
        config,
    )
    print(f"最终结果: {result['messages'][-1].content}")


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("LangGraph Step 5: Human-in-the-Loop（人工介入）")
    print("interrupt + checkpoint + resume 模式演示\n")

    # Demo 1: 审批通过
    demo1_approve()

    # Demo 2: 审批拒绝
    demo2_reject()

    # Demo 3: 状态检查
    demo3_inspect_state()

    print("\n" + "=" * 50)
    print("所有 Demo 执行完毕")
    print("=" * 50)
