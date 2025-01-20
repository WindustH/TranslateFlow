from openai import OpenAI
import time
import logging
from logging.handlers import RotatingFileHandler
import colorlog
import os
import json  # 导入 json 模块

# 配置日志
def setup_logger():
    # 创建一个日志记录器
    logger = logging.getLogger('api_request')
    logger.setLevel(logging.DEBUG)

    # 创建一个控制台处理器，并设置颜色格式
    console_handler = logging.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)

    # 创建一个文件处理器，并设置格式
    log_dir = 'log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "api_request.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # 将处理器添加到日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

def is_valid_json(json_str):
    try:
        json.loads(json_str)
        return True
    except ValueError:
        return False

def api_request(api_key, base_url, model, messages, max_retries=10, retry_delay=120):
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    for attempt in range(max_retries):
        try:
            logger.info(f"第 {attempt + 1} 次尝试：正在发送请求到 API")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            response_content = response.choices[0].message.content

            # 检测响应是否是合法的 JSON
            if is_valid_json(response_content):
                logger.info("API 请求成功，且响应是合法的 JSON")
                return response_content  # 返回 JSON 字符串
            else:
                logger.warning(f"第 {attempt + 1} 次尝试：响应不是合法的 JSON，正在重试...")
                # 在 messages 中加入额外的提示信息（英文）
                messages.append({
                    "role": "user",
                    "content": "Please ensure the response is a valid JSON format."
                })
                if attempt < max_retries - 1:
                    logger.warning(f"{retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.critical(f"API 请求失败，已达到最大重试次数 {max_retries} 次：响应不是合法的 JSON")
                    raise Exception(f"API 请求失败，已达到最大重试次数 {max_retries} 次：响应不是合法的 JSON")

        except Exception as e:
            logger.error(f"第 {attempt + 1} 次尝试失败：{e}")
            if attempt < max_retries - 1:
                logger.warning(f"{retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                logger.critical(f"API 请求失败，已达到最大重试次数 {max_retries} 次")
                raise Exception(f"API 请求失败，已达到最大重试次数 {max_retries} 次")