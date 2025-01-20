from base.api_request import api_request
from base.language_code import get_language_name
import threading
import json
import time
import logging
import colorlog
import os

# 配置日志
def setup_logger():
    # 创建一个日志记录器
    logger = logging.getLogger('sub_translate')
    logger.setLevel(logging.DEBUG)

    # 创建日志目录（如果不存在）
    log_dir = 'log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

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
    file_handler = logging.FileHandler(os.path.join(log_dir,"sub_translate.log"))
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # 将处理器添加到日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

prompt_multi = """
The user will ask you to translate a video's subtitles. Please translate the original text reasonably based on the JSON provided. Output in JSON format.

Except for special instructions, do not translate personal names. Do not translate function names or code. For place names and book titles, if there is no conventional translation, do not translate them.

EXAMPLE JSON INPUT:
{
    "src_lang": "English",
    "dst_lang": "Simplified Chinese",
    "title": "01 - 1.1 Course Organization (8.20 Introduction to Special Relativity)",
    "preceding": [
        " Welcome to H20.",
        "Welcome to Special Relativity."
    ],
    "original": [
        "And let me start by wishing you all a Happy New Year 2021.",
        "I'm pretty sure this is going to be an exciting year with a lot of changes ahead and a lot of exciting events."
    ],
    "succeeding": [
        " My name is Markus Kluter, and I will guide you through this IAP lecture on special relativity."
    ]
}

EXAMPLE JSON OUTPUT:
{
    "translated": [
        "首先，让我祝大家2021年新年快乐。",
        "我敢肯定这将是一个令人激动的一年，伴随着许多变化和许多令人兴奋的事件。"
    ]
}

Your output "translated" contains elements that correspond one-to-one with the elements in user's input "original".
"""

prompt_mono = """
The user will ask you to translate a single subtitle. Output in JSON format.

Except for special instructions, do not translate personal names. Do not translate function names or code. For place names and book titles, if there is no conventional translation, do not translate them.

EXAMPLE JSON INPUT:
{
    "src_lang": "English",
    "dst_lang": "Simplified Chinese",
    "title": "01 - 1. Introduction and the geometric viewpoint on physics#",
    "preceding": [
        " Welcome to H20.",
        "Welcome to Special Relativity."
    ],
    "original": "And let me start by wishing you all a Happy New Year 2021.",
    "succeeding": [
        " My name is Markus Kluter, and I will guide you through this IAP lecture on special relativity.",
        "This is very likely my favorite class at MIT, A, because it's IAP, and B,"
    ]
}

EXAMPLE JSON OUTPUT:
{
    "translated": "首先，让我祝大家2021年新年快乐。"
}
"""

def translate_mono(api_key, base_url, model, src_lang, dst_lang, media_title, original, preceding, succeeding):
    message_mono = [
        {"role": "system", "content": prompt_mono},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "src_lang": get_language_name(src_lang),
                    "dst_lang": get_language_name(dst_lang),
                    "title": media_title,
                    "original": original,
                    "preceding": preceding,
                    "succeeding": succeeding,
                }
            ),
        },
    ]
    try:
        response_mono = json.loads(api_request(api_key, base_url, model, message_mono))
        if "translated" in response_mono:
            return response_mono["translated"]
        else:
            logger.error(f"单条翻译失败：输出格式不正确")
            return None
    except Exception as e:
        logger.error(f"单条翻译失败：{e}")
        return None

def translate_multi(api_key, base_url, model, src_lang, dst_lang, media_title, batch, preceding, succeeding):
    messages = [
        {"role": "system", "content": prompt_multi},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "src_lang": get_language_name(src_lang),
                    "dst_lang": get_language_name(dst_lang),
                    "title": media_title,
                    "original": batch,
                    "preceding": preceding,
                    "succeeding": succeeding,
                }
            ),
        },
    ]
    try:
        response_json = api_request(api_key, base_url, model, messages)
        response = json.loads(response_json)
        if "translated" in response and len(response["translated"]) == len(batch):
            return response["translated"]
        else:
            logger.warning(f"批量翻译：输出输入不匹配")
            return None
    except Exception as e:
        logger.error(f"批量翻译失败：{e}")
        return None

def sub_translate(
    dict,
    api_key,
    base_url,
    model,
    src_lang,
    dst_lang,
    media_title,
    context_window=3,
    batch_size=8,
    thread_count=10,
):
    """
    翻译字幕，处理所有数据前检测翻译是否存在，若是连续的没有翻译的原文就采用批量翻译进行翻译

    :param dict: 包含字幕信息的词典
    :param api_key: OpenAI API密钥
    :param base_url: API基础URL
    :param model: API模型
    :param src_lang: 源语言
    :param dst_lang: 目标语言
    :param media_title: 音视频标题
    :param context_window: 上下文长度
    :param batch_size: 每次处理的字幕数量
    :param thread_count: 并发线程数量
    """
    segments = dict["segments"]
    threads = []  # 初始化线程列表

    def worker(index):
        # 检查当前批次是否有缺失的翻译
        batch_indices = range(index, min(index + batch_size, len(segments)))
        batch_missing = [i for i in batch_indices if "translation" not in segments[i] or not segments[i]["translation"]]

        if len(batch_missing) == batch_size:
            # 如果整个批次都缺失翻译，尝试批量翻译
            batch = [segments[i]["text"] for i in batch_indices]
            preceding = [segments[i]["text"] for i in range(max(0, index - context_window), index)]
            succeeding = [segments[i]["text"] for i in range(index + batch_size, min(len(segments), index + batch_size + context_window))]
            translations = translate_multi(api_key, base_url, model, src_lang, dst_lang, media_title, batch, preceding, succeeding)
            if translations:
                for i, translation in zip(batch_indices, translations):
                    segments[i]["translation"] = translation
            else:
                # 如果批量翻译失败，逐条翻译
                for i in batch_indices:
                    preceding = [segments[j]["text"] for j in range(max(0, i - context_window), i)]
                    succeeding = [segments[j]["text"] for j in range(i + 1, min(len(segments), i + 1 + context_window))]
                    translation = translate_mono(api_key, base_url, model, src_lang, dst_lang, media_title, segments[i]["text"], preceding, succeeding)
                    if translation:
                        segments[i]["translation"] = translation
                    else:
                        logger.error(f"字幕翻译失败：{segments[i]["text"]}")
        else:
            # 如果有部分缺失，逐条翻译缺失的部分
            for i in batch_missing:
                preceding = [segments[j]["text"] for j in range(max(0, i - context_window), i)]
                succeeding = [segments[j]["text"] for j in range(i + 1, min(len(segments), i + 1 + context_window))]
                translation = translate_mono(api_key, base_url, model, src_lang, dst_lang, media_title, segments[i]["text"], preceding, succeeding)
                if translation:
                    segments[i]["translation"] = translation
                else:
                    logger.error(f"字幕翻译失败：{segments[i]["text"]}")

    for i in range(0, len(segments), batch_size):
        # 如果当前线程数达到上限，等待至少一个线程完成
        while len(threads) >= thread_count:
            for t in threads:
                if not t.is_alive():  # 检查线程是否完成
                    threads.remove(t)  # 从线程列表中移除
            time.sleep(0.1)  # 避免忙等待
        t = threading.Thread(target=worker, args=[i])
        threads.append(t)
        t.start()

    # 等待剩余线程完成
    for t in threads:
        t.join()