from langchain.agents.middleware.summarization import SummarizationMiddleware

from core.tools import model

def build_context_middleware(trigger:int = 4000,keep :int = 2000):
    """
    构建上下文压缩管理中间件
    中期记忆：对话超长时自动调用 LLM 压缩为摘要，保留最近对话。
    - trigger=("tokens", 4000)：对话累积超 4000 token 触发摘要
    - keep=("tokens", 2000)：保留最近 2000 token 的完整对话
    - token_counter=model：用 DeepSeek 精确数 token
    """
    return SummarizationMiddleware(
            model = model,
            trigger=("tokens",trigger),
            keep = ("tokens",keep),
        )
