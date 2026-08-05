from pathlib import Path
from langchain_chroma import Chroma

from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader, Docx2txtLoader, JSONLoader, \
    PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.logger import setup_logger

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# ========== 全局变量（定义在这里） ==========
vectorstore = None

# 自动创建当前模块的 logger
logger = setup_logger(__name__)

# 加载 文档:
def load_file(filepath):
    """
    加载文档，将文档处理为list字符串列表
    """
    logger.info(f"开始加载文件：{filepath}")
    path = Path(filepath)

    #获取后缀名
    suffixes = path.suffix.lower()

    #按后缀操作
    #单个：
    # if suffixes == '.txt':
    #     #加载txt：
    #     txt_loder= TextLoader(file_path = filepath ,encoding = 'utf-8')
    #     #转为list列表
    #     docs = txt_loder.load() #返回List列表(Document对象)
    #     return docs
    if suffixes == '.txt':
        loder = TextLoader(filepath, encoding='utf-8')
    elif suffixes == '.md':
        loder = TextLoader(filepath, encoding='utf-8')
    elif suffixes == '.docx':
        loder = Docx2txtLoader(filepath)
    elif suffixes == '.json':
        loder = JSONLoader(filepath, "." ,False)
    elif suffixes == '.pdf':
        loder = PyPDFLoader(filepath,extraction_mode= "plain")
    elif suffixes == '.png' or suffixes == '.jpg' or suffixes == '.jpeg':
        return load_image(filepath)
    docs = loder.load()
    #todo ：添加一次性读取多个文件的内容，读File Directory

    logger.info(f"加载完毕")
    return docs

def load_image(filepath):
    """读取图片，返回 Document 列表"""
    # TODO: 用 pytesseract 或 多模态大模型
    raise NotImplementedError("图片OCR功能开发中")

#递归字符文本切分器
def splitter_documents(docs):
    """
    文本切割器，使用递归字符文本切割器
    """
    logger.info(f"开始进行文本切分")
    #1.创建分割器对象
    text_split = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=10,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )
    #2.切割
    chunks = text_split.split_documents(docs)  # ← 注意是 split_documents
    logger.info(f"切分完毕")
    return chunks

#向量化
def get_embeddings():
    """获取 Embedding 模型（单例模式，只加载一次）"""

    local_model_path = "./models/bge-small-zh-v1.5"

    # 检查本地模型是否存在
    if os.path.exists(local_model_path):
        # 检查关键文件是否存在
        model_file = os.path.join(local_model_path, "model.safetensors")
        if os.path.exists(model_file):
            logger.info(f"使用本地模型：{local_model_path}")
            return HuggingFaceEmbeddings(
                model_name=local_model_path,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        else:
            logger.warning(f"本地模型文件不完整（缺少 model.safetensors），将重新下载")
    else:
        logger.info("本地模型不存在，开始下载...")

    # 如果本地不存在或文件不完整，从镜像站下载
    # 设置镜像站环境变量
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

    logger.info("从 Hugging Face 镜像站下载模型...")

    # 用模型名直接加载（会自动下载并缓存到 .cache/huggingface/）
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
def store_to_vectorstore(chuns):
    """
    存入向量数据库
    """
    logger.info(f"进行向量化")
    global vectorstore
    #如果没有向量库就创建一个
    if vectorstore is None:
        vectorstore = Chroma(
            collection_name="mvp_knowledge",
            embedding_function=get_embeddings(),
            persist_directory="./chroma_db"
        )
    vectorstore.add_documents(chuns)

    logger.info(f"文件向量化存入完毕")

def search_knowledge_base(query:str, k: int = 3) -> list:
    """
    从向量库中检索与 query 最相关的 k 个文本块
    返回 List[Document]
    """
    #先判断在这里有没有vectorstore
    global vectorstore
    if vectorstore is None:
        logger.info(f"向量库为空，文件不存在，请先存入")
        return []

    #检索
    logger.info(f"检索问题：{query[:50]}...")
    results = vectorstore.similarity_search(query, k=k)
    logger.info(f"检索到了{len(results)}个相关的文本块")

    return results

def process_and_store(filepath: str) -> int:
  """加载文件 → 切分 → 入库，返回文本块数量"""
  docs = load_file(filepath)
  chunks = splitter_documents(docs)
  store_to_vectorstore(chunks)
  return len(chunks)

