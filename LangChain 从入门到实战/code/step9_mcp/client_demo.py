"""
Step 9: MCP 模型上下文协议
演示通过 langchain-mcp-adapters 连接 MCP Server，将 MCP 工具接入 LangChain Agent

运行前确保已安装依赖：
    pip install mcp langchain-mcp-adapters

运行方式：
    python step9_mcp/client_demo.py
"""

import asyncio
import os
import sys

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

# 将 step9_mcp 目录加入路径，方便找到 math_server.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 使用环境变量中的 DeepSeek 配置
# 如果没有配置，也可以用字符串格式 "deepseek:deepseek-v4-flash"
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


async def demo_local_mcp():
    """连接本地 MCP Server（stdio 模式）"""
    # math_server.py 的绝对路径
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "math_server.py")

    client = MultiServerMCPClient(
        {
            "math": {
                "transport": "stdio",
                "command": "python",
                "args": [server_path],
            }
        }
    )

    # 获取 MCP Server 暴露的所有工具
    tools = await client.get_tools()
    print(f"MCP 工具列表: {[t.name for t in tools]}")

    # 创建 Agent，MCP 工具和 @tool 工具用法完全一样
    agent = create_agent(
        f"deepseek:{MODEL}",
        tools,
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "(3 + 5) x 12 等于多少？"}]}
    )
    print("\nAgent 回复:")
    print(result["messages"][-1].content)


async def main():
    print("=" * 50)
    print("Demo: 连接本地 MCP Server (stdio)")
    print("=" * 50)
    await demo_local_mcp()


if __name__ == "__main__":
    asyncio.run(main())
