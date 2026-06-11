from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",  # 换成你的 API 地址
    api_key="sk-5ab3bca60f72427298ecde72e0f4d0b4"              # 换成你的 API Key
)

messages = []

while True:
    user_input = input("你: ")
    if user_input.lower() in ("exit", "quit"):
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages
    )

    assistant_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_message})

    print(f"AI: {assistant_message}\n")