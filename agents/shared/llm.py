# agents/shared/llm.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenRouter 兼容 OpenAI 的接口格式
# 只需改 base_url 和 api_key，其他代码完全一样
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# 用 Claude Haiku：速度快、价格便宜，适合批量处理
DEFAULT_MODEL = "anthropic/claude-haiku-4-5"


def chat(prompt: str, system: str = "") -> str:
    """普通对话，返回纯文本"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
    )
    return response.choices[0].message.content


def chat_json(prompt: str, system: str = "") -> str:
    """要求返回 JSON，用于结构化输出"""
    # 在 prompt 里明确要求 JSON，比 response_format 更兼容
    json_prompt = prompt + "\n\n请只返回 JSON，不要有任何其他文字。"
    return chat(json_prompt, system)


# 直接运行验证配置
if __name__ == "__main__":
    print("正在测试 API 连接...")
    result = chat("用一句话介绍你自己")
    print(f"✅ 连接成功！\n回复：{result}")