import logging
import sys

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
    file_handler = logging.FileHandler('app.log',encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger