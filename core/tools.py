import os
import uuid

from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from dotenv import load_dotenv

from core.rag import search_knowledge_base
from core.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

# ========== DeepSeek LLM ==========
model = init_chat_model(
    model="deepseek-v4-flash",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base=os.getenv("DEEPSEEK_BASE_URL"),
)
# ========== 题目缓存（question_id → 标准答案） ==========
quiz_cache: dict[str, str] = {}



def make_retrieve_tool(user_id:str):
    """
    创建检索工具工厂，调用检索工具时闭包传入user_id

    Args:
        user_id: 用户账号信息
    """

    @tool
    def retrieve_tool(query: str, ) -> str:
        """
        从用户已上传的知识库中检索相关内容，用于回答问题。
        当用户询问知识库中的内容时，请优先调用此工具。

        Args:
            query: 用户提出的问题，将用于向量检索

        Returns:
            检索到的相关文本片段
        """
        logger.info(f"[retrieve_tool] 检索：{query[:50]}...")
        docs = search_knowledge_base(query, k=3,user_id=user_id )

        if not docs:
            return "知识库中未检索到相关内容，请提醒用户先上传文件。"

        result = "\n\n".join(
            f"[参考片段{i + 1}]出自《{doc.metadata.get('source', '未知')}》：{doc.page_content}"
            for i, doc in enumerate(docs)
        )
        return result
    return retrieve_tool



@tool
def quiz_tool(topic: str = "") -> str:
    """
    根据知识库内容，出一道题目来测试用户掌握程度。
    用户说"出题""考考我""来道题"时调用此工具。

    Args:
        topic: 出题的主题或范围，如果为空则从知识库随机抽取内容出题

    Returns:
        一道题目（不含答案），附带 question_id 供后续评判使用
    """
    logger.info(f"[quiz_tool] 出题，主题：{topic if topic else '随机'}")

    # 1. 检索知识库相关内容
    search_query = topic if topic else "关键概念 知识点"
    docs = search_knowledge_base(search_query, k=3)

    if not docs:
        return "知识库为空，请提醒用户先上传文件后再出题。"

    reference = "\n".join(doc.page_content for doc in docs)

    # 2. 让 大模型 根据检索内容出题（附带标准答案）
    prompt = f"""你是一名严格的出题老师。请根据以下知识库内容出一道题目，难度适中。

【知识库内容】
{reference}

【要求】
1. 根据上述内容出一道简答题（不是选择题）
2. 同时给出该题的标准答案（不要告诉用户）
3. 按以下格式返回（严格按格式）：

【题目】
（此处写题目）

【标准答案】
（此处写标准答案）"""

    response = model.invoke(prompt)
    content = response.content.strip()

    # 3. 解析出题目和标准答案
    if "【题目】" in content and "【标准答案】" in content:
        question_part = content.split("【题目】")[1].split("【标准答案】")[0].strip()
        answer_part = content.split("【标准答案】")[1].strip()
    else:
        # 格式不对，兜底
        question_part = content
        answer_part = "暂无标准答案"

    # 4. 存入缓存，返回题目
    question_id = str(uuid.uuid4())[:8]
    quiz_cache[question_id] = answer_part
    logger.info(f"[quiz_tool] 题目已生成，ID：{question_id}")

    return f"题目ID：{question_id}\n\n{question_part}"


@tool
def evaluate_tool(question_id: str, user_answer: str) -> str:
    """
    根据知识库中的标准答案，评判用户对某道题目的回答。
    当用户提交答案后调用此工具，给出得分和解析反馈。

    Args:
        question_id: 题目ID（出题时返回的那个ID）
        user_answer: 用户提交的答案

    Returns:
        得分（0-10）和详细评价
    """
    logger.info(f"[evaluate_tool] 评判，题目ID：{question_id}")

    # 1. 取标准答案
    standard_answer = quiz_cache.get(question_id)
    if not standard_answer:
        return "未找到对应的题目，可能已过期。请重新出题。"

    # 2. 让 DeepSeek 评判
    prompt = f"""你是一名公正的评分老师。请根据标准答案评判学生的回答。

【标准答案】
{standard_answer}

【学生回答】
{user_answer}

【要求】
1. 给出0-10分的评分
2. 指出学生回答正确的部分和错误/遗漏的部分
3. 给出补充说明
4. 按以下格式回复：

得分：X分
评价：（详细评价）"""

    response = model.invoke(prompt)
    return response.content.strip()
