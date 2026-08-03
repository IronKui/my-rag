import logging
import sys
from pathlib import Path

def setup_logger(name:str = None):
    """
    配置日志
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    #判断有无handler
    if logger.handlers:
        return logger

    #格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    #输入到终端
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    #到文件
    BASE_DIR = Path(__file__).resolve().parent.parent  # core/ 的上级 = backend/
    file_handler = logging.FileHandler(BASE_DIR / 'app.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger