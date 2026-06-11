# 运行方式：pip install openai
# 将 your-api-key 替换为你的 DeepSeek API Key，保存为 thinking_agent.py 后运行：python thinking_agent.py

import json
from openai import OpenAI

# 创建客户端
client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-5ab3bca60f72427298ecde72e0f4d0b4"  # 替换为你的 DeepSeek API Key
)

# 模拟天气查询工具
def get_weather(city: str) -> str:
    """查询指定城市的天气信息"""
    mock_data = {
        "北京": "晴，18-28°C",
        "上海": "多云，20-26°C",
        "深圳": "阵雨，25-32°C",
        "成都": "阴，16-22°C",
    }
    return mock_data.get(city, f"{city}：暂无天气数据")

# 工具定义（JSON Schema 格式，告诉模型有哪些工具可用）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息，包括天气状况和温度范围",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "要查询天气的城市名称，例如：北京、上海、深圳"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

# 工具名 -> 工具函数的映射
tool_map = {
    "get_weather": get_weather
}

SYSTEM_PROMPT = """你是一个智能助手，可以根据用户的问题调用合适的工具来获取信息，然后给出回答。
回答时要基于工具返回的实际数据，不要编造信息。"""

def run_agent(user_input: str, messages: list) -> str:
    """执行一轮 Agent 对话，返回最终回复文本"""
    messages.append({"role": "user", "content": user_input})

    while True:
        # 开启思考模式：reasoning_effort="high" + thinking enabled
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=tools,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}}
        )

        choice = response.choices[0]
        msg = choice.message

        # 打印推理过程
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            print(f"[思考过程]\n{reasoning}\n")

        # 模型直接给出最终回答
        if choice.finish_reason == "stop":
            # 直接 append 整个 msg 对象，reasoning_content 会一同保留
            messages.append(msg)
            return msg.content

        # 模型决定调用工具
        if choice.finish_reason == "tool_calls":
            # 关键：必须 append 整个 msg，工具调用轮次的 reasoning_content 不能丢弃
            # 否则 API 会返回 400 错误
            messages.append(msg)

            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                print(f"  [调用工具: {func_name}({func_args})]")
                result = tool_map[func_name](**func_args)
                print(f"  [工具结果: {result}]")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result)
                })

            # 循环继续，把工具结果再次发给模型，模型会继续推理

if __name__ == "__main__":
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("=== 带思考模式的 Agent（输入 exit 退出）===\n")

    while True:
        user_input = input("你: ")
        if user_input.strip().lower() == "exit":
            print("再见！")
            break

        reply = run_agent(user_input, messages)
        print(f"AI: {reply}\n")