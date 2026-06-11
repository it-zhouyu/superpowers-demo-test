from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-5ab3bca60f72427298ecde72e0f4d0b4"
)

SYSTEM_PROMPT = """你是一个智能助手。回答要简洁直接。
如果用户的问题你不确定，就说"我不确定"，不要编造答案。"""

messages = [{"role": "system", "content": SYSTEM_PROMPT}]

print("Agent 已启动，输入消息开始对话，输入 exit 退出\n")

while True:
    user_input = input("你: ").strip()
    if not user_input or user_input.lower() in ("exit", "quit"):
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        temperature=0.7
    )

    assistant_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_message})

    print(f"AI: {assistant_message}\n")

    # 显示本次消耗的 Token 数
    usage = response.usage
    print(f"[本次消耗: 输入 {usage.prompt_tokens} + 输出 {usage.completion_tokens} = {usage.total_tokens} tokens]")
    print(f"[对话历史: {len(messages)} 条消息]\n")