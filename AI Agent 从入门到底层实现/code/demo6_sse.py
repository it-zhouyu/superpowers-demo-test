"""
demo6_sse.py —— 在 demo6.py 的基础上增加 Web 前端，通过 SSE 展示流式输出

SSE（Server-Sent Events）是一种服务端向浏览器单向推送消息的机制。
与 WebSocket 的双向通信不同，SSE 是单向的（服务端 → 客户端），
但它的优势是：基于标准 HTTP 协议，浏览器原生支持 EventSource API，
非常适合 LLM 流式输出这种"服务端持续发送数据"的场景。

运行方式：
    pip install flask
    python demo6_sse.py
    然后浏览器打开 http://localhost:5000
"""

from openai import OpenAI
from flask import Flask, request, Response, render_template, jsonify
import json

app = Flask(__name__)

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


def sse_event(event: str, data: dict) -> str:
    """
    构造一个 SSE 事件字符串

    SSE 协议格式：
        event: 事件名\n
        data: JSON 数据\n
        \n

    每个事件以两个换行符结尾，浏览器 EventSource API 会自动解析这个格式
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_with_tools_sse(messages: list, tools: list):
    """
    流式调用 LLM，通过 SSE 将结果逐步推送给前端

    和 demo6.py 中的 stream_with_tools 逻辑相同，区别在于：
    - 不用 print 打印，而是 yield SSE 事件
    - 工具调用和工具结果也通过 SSE 推送，让前端可以展示

    SSE 事件类型：
    - content：文本内容增量
    - tool_call：LLM 决定调用某个工具
    - tool_result：工具执行结果
    - done：整轮对话完成
    - error：发生错误
    """
    stream = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        tools=tools,
        stream=True
    )

    tool_calls = {}
    content_parts = []
    finish_reason = None

    for chunk in stream:
        choice = chunk.choices[0]
        delta = choice.delta

        # 增量推送文本内容
        if delta.content:
            content_parts.append(delta.content)
            yield sse_event("content", {"text": delta.content})

        # 增量拼接工具调用信息（和 demo6.py 逻辑一致）
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

    # 情况 1：LLM 直接回复文本
    if finish_reason == "stop":
        content = "".join(content_parts)
        messages.append({"role": "assistant", "content": content})
        yield sse_event("done", {"content": content})

    # 情况 2：LLM 决定调用工具
    elif finish_reason == "tool_calls":
        tc_list = []
        for idx in sorted(tool_calls.keys()):
            tc = tool_calls[idx]
            tc_list.append({
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]}
            })

        messages.append({"role": "assistant", "tool_calls": tc_list})

        # 逐个执行工具，并通过 SSE 推送工具调用信息
        for tc in tc_list:
            func_name = tc["function"]["name"]
            func_args = json.loads(tc["function"]["arguments"])

            # 推送工具调用事件
            yield sse_event("tool_call", {
                "name": func_name,
                "arguments": func_args
            })

            result = tool_map[func_name](**func_args)

            # 推送工具结果事件
            yield sse_event("tool_result", {
                "name": func_name,
                "result": result
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result
            })

        # 递归调用，让 LLM 根据工具结果继续生成
        yield from stream_with_tools_sse(messages, tools)


# ---- 会话存储 ----
# 用字典存储每个会话的消息历史，key 是 session_id
# 实际生产中应该用 Redis 或数据库，这里为了演示简单用内存字典
sessions = {}


# ---- 路由 ----

@app.route("/")
def index():
    """返回前端页面"""
    return render_template("demo6_sse.html")


@app.route("/chat", methods=["POST"])
def chat():
    """
    SSE 聊天接口

    前端通过 fetch 请求这个接口，后端返回 Content-Type: text/event-stream，
    浏览器会保持连接，持续接收 SSE 事件，直到连接关闭

    请求体：
        {
            "message": "用户输入",
            "session_id": "会话ID"
        }
    """
    data = request.json
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    # 获取或创建会话
    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    messages = sessions[session_id]
    messages.append({"role": "user", "content": user_message})

    def generate():
        """SSE 生成器函数，Flask 会将 yield 的内容作为流式响应发送"""
        try:
            for event_str in stream_with_tools_sse(messages, tools):
                yield event_str
        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    # Response 设置：
    # - Content-Type: text/event-stream 是 SSE 的标准 MIME 类型
    # - Cache-Control: no-cache 防止浏览器缓存 SSE 响应
    # - X-Accel-Buffering: no 让 Nginx（如果有的话）不做缓冲，立即转发
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.route("/clear", methods=["POST"])
def clear():
    """清除会话历史"""
    data = request.json
    session_id = data.get("session_id", "default")
    if session_id in sessions:
        del sessions[session_id]
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("SSE Demo 已启动，浏览器打开 http://localhost:5001")
    app.run(debug=True, port=5001)
