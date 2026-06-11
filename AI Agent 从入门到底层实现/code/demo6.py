from openai import OpenAI
import json

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-5ab3bca60f72427298ecde72e0f4d0b4"
)

# ---- 工具定义 ----
def get_weather(city: str) -> str:
    """模拟天气查询，返回固定的天气数据"""
    weather_data = {
        "北京": "晴天，气温 25°C，空气质量良好",
        "上海": "多云，气温 28°C，有轻微雾霾",
        "深圳": "雷阵雨，气温 32°C，湿度 85%",
        "成都": "阴天，气温 22°C，可能有小雨"
    }
    return weather_data.get(city, f"{city}：晴间多云，气温 26°C")

# ---- tools 定义 ----
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如：北京、上海、深圳"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

# 工具名 → 函数的映射
tool_map = {
    "get_weather": get_weather
}

# ---- 系统提示词 ----
SYSTEM_PROMPT = """你是一个智能助手，可以帮用户查询天气。
回答要简洁明了，查询天气时调用 get_weather 工具。"""

# ---- 流式处理函数（核心） ----
def stream_with_tools(messages: list, tools: list) -> str:
    """流式调用 LLM，支持文本回复和工具调用"""
    stream = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        tools=tools,
        stream=True
    )

    # tool_calls 用 dict 按 index 拼接，函数名和参数是分多个 chunk 增量到达的
    tool_calls = {}  # {index: {"id": "", "name": "", "arguments": ""}}
    content_parts = []
    finish_reason = None

    for chunk in stream:
        choice = chunk.choices[0]
        delta = choice.delta

        # 增量打印文本内容
        if delta.content:
            print(delta.content, end="", flush=True)
            content_parts.append(delta.content)
            
        # if delta.reasoning_content:
        #     print(delta.reasoning_content, end="", flush=True)

        # 增量拼接工具调用信息
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in tool_calls:
                    tool_calls[idx] = {"id": "", "name": "", "arguments": ""}
                if tc_delta.id:
                    tool_calls[idx]["id"] += tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tool_calls[idx]["name"] += tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_calls[idx]["arguments"] += tc_delta.function.arguments

        if choice.finish_reason:
            finish_reason = choice.finish_reason

    print()  # 换行

    # 情况 1：LLM 直接回复文本
    if finish_reason == "stop":
        content = "".join(content_parts)
        messages.append({"role": "assistant", "content": content})
        return content

    # 情况 2：LLM 决定调用工具
    if finish_reason == "tool_calls":
        # 构造完整的 tool_calls 消息
        tc_list = []
        for idx in sorted(tool_calls.keys()):
            tc = tool_calls[idx]
            tc_list.append({
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]}
            })

        messages.append({"role": "assistant", "tool_calls": tc_list})

        # 逐个执行工具
        for tc in tc_list:
            func_name = tc["function"]["name"]
            func_args = json.loads(tc["function"]["arguments"])
            print(f"  [调用工具: {func_name}({func_args})]")
            result = tool_map[func_name](**func_args)
            print(f"  [工具结果: {result}]")
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result
            })

        # 递归调用，让 LLM 根据工具结果继续生成
        print("\nAI: ", end="", flush=True)
        return stream_with_tools(messages, tools)

    return ""

# ---- 主循环 ----
messages = [{"role": "system", "content": SYSTEM_PROMPT}]

print("Agent 已启动（流式模式），输入 exit 退出\n")

while True:
    user_input = input("你: ").strip()
    if not user_input or user_input.lower() in ("exit", "quit"):
        print("再见！")
        break

    messages.append({"role": "user", "content": user_input})

    print("AI: ", end="", flush=True)
    stream_with_tools(messages, tools)
    print()  # 每轮对话后空一行