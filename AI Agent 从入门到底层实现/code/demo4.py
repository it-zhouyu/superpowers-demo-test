# 运行方式：pip install openai tiktoken numpy
# 将 your-api-key 替换为你的 DeepSeek API Key，保存为 agent_with_memory.py 后运行：python agent_with_memory.py

"""
整合了短期记忆、长期记忆、自动记忆
"""

import json
import os
import tiktoken
import numpy as np
from openai import OpenAI

# ============ 客户端配置 ============

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-5ab3bca60f72427298ecde72e0f4d0b4"  # 替换为你的 DeepSeek API Key
)

embedding_client = OpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="sk-01505a5c36804a80abaf78eaa70f4852"  # 替换为你的阿里云 API Key
)

MODEL = "deepseek-v4-flash"

# ============ 短期记忆：对话历史管理 ============

MAX_TOKENS = 4000  # Token 预算，超过就触发摘要压缩


def count_tokens(messages: list) -> int:
    """计算 messages 列表的总 Token 数"""
    encoding = tiktoken.get_encoding("cl100k_base")
    total = 0
    for msg in messages:
        total += 4  # 每条消息的固定开销
        for key, value in msg.items():
            if isinstance(value, str):
                total += len(encoding.encode(value))
            elif isinstance(value, list):
                total += len(encoding.encode(json.dumps(value)))
        total += 2  # 消息分隔符
    return total


def summarize_messages(messages: list, keep_recent: int = 4) -> list:
    """把早期对话压缩成摘要，保留最近几轮"""
    system_messages = [m for m in messages if m["role"] == "system"]
    conversation = [m for m in messages if m["role"] != "system"]

    if len(conversation) <= keep_recent:
        return messages

    old_messages = conversation[:-keep_recent]
    recent_messages = conversation[-keep_recent:]

    summary_prompt = "请将以下对话历史压缩成一段简洁的摘要，保留关键信息：\n\n"
    for msg in old_messages:
        content = msg.get("content", "")
        if content:
            summary_prompt += f"{msg['role']}: {content}\n"

    summary_response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": summary_prompt}],
        temperature=0
    )

    summary = summary_response.choices[0].message.content
    summary_message = {"role": "system", "content": f"[之前的对话摘要]\n{summary}"}

    return system_messages + [summary_message] + recent_messages


# ============ 长期记忆：文件存储 + 向量检索 ============

MEMORY_FILE = "memory.json"


def load_memory() -> list:
    """从文件加载记忆"""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_memory_to_file(memories: list):
    """把记忆写入文件"""
    with open(MEMORY_FILE, "w") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def add_memory(fact: str) -> str:
    """添加一条记忆"""
    memories = load_memory()
    memories.append({"content": fact})
    save_memory_to_file(memories)
    return "已记住"


def get_embedding(text: str) -> list:
    """调用 Embedding API 将文本转为向量"""
    response = embedding_client.embeddings.create(
        model="text-embedding-v4",
        input=text
    )
    return response.data[0].embedding


def cosine_similarity(a: list, b: list) -> float:
    """计算两个向量的余弦相似度"""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search_memory(query: str, memories: list, top_k: int = 3) -> list:
    """从记忆中检索跟 query 最相关的 top_k 条"""
    if not memories:
        return []

    query_embedding = get_embedding(query)

    scored = []
    for mem in memories:
        if "embedding" not in mem:
            mem["embedding"] = get_embedding(mem["content"])
        score = cosine_similarity(query_embedding, mem["embedding"])
        scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [mem for _, mem in scored[:top_k]]


# ============ 自动记忆工具定义 ============

MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_memory",
            "description": "保存一条值得记住的信息，比如用户的个人信息、偏好、重要决策等",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "要记住的信息"
                    }
                },
                "required": ["fact"]
            }
        }
    }
]

SYSTEM_PROMPT = """你是一个智能助手。

在对话中，如果用户告诉你重要的个人信息、偏好或关键决策，
主动调用 add_memory 工具把它们记下来。
不要记住琐碎的对话内容。
回答要简洁直接。"""


# ============ 示例工具：查天气 ============

WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                }
            },
            "required": ["city"]
        }
    }
}


def get_weather(city: str) -> str:
    """模拟天气查询，实际项目中调用真实天气 API"""
    weather_data = {
        "北京": "晴，气温 18-28°C",
        "上海": "多云，气温 22-30°C",
        "深圳": "阵雨，气温 25-32°C",
    }
    return weather_data.get(city, f"{city}：晴，气温 20-25°C")


# 工具名 → 函数的映射
tool_map = {
    "get_weather": get_weather,
    "add_memory": add_memory,
}


# ============ 主循环 ============

def run():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("Agent 已启动，输入消息开始对话，输入 exit 退出\n")

    while True:
        user_input = input("你: ").strip()
        if not user_input or user_input.lower() in ("exit", "quit"):
            break

        # 1. 加载长期记忆，检索相关条目
        all_memories = load_memory()
        relevant = search_memory(user_input, all_memories, top_k=3)
        memory_text = "\n".join([f"- {m['content']}" for m in relevant])

        # 2. 更新 system prompt（带上相关记忆）
        if memory_text:
            messages[0] = {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\n\n相关记忆:\n{memory_text}"
            }

        # 3. 添加用户消息
        messages.append({"role": "user", "content": user_input})

        # 4. 短期记忆管理：超出预算就压缩
        if count_tokens(messages) > MAX_TOKENS:
            messages = summarize_messages(messages)

        # 5. 执行 Agent 循环
        while True:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=[WEATHER_TOOL] + MEMORY_TOOLS
            )

            choice = response.choices[0]

            if choice.finish_reason == "stop":
                messages.append({"role": "assistant", "content": choice.message.content})
                print(f"AI: {choice.message.content}\n")
                break

            if choice.finish_reason == "tool_calls":
                messages.append(choice.message.model_dump())

                for tool_call in choice.message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    result = tool_map[func_name](**func_args)
                    print(f"  [调用工具: {func_name}({func_args})]")
                    print(f"  [工具结果: {result}]")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })


if __name__ == "__main__":
    run()