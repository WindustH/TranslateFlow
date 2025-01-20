from base.media_transcribe import transcribe_batch
from base.sub_translate import sub_translate
from base.sub_segment import sub_segment
from base.sub_optimize import sub_optimize
from base.path_request import Directory
from base.files_find import Files
from base.srt_generate import generate_bilingual_srt
from base.srt2ass import convert_srt_to_ass
import whisperX.whisperx as wsx
from config import *

import os
import json
import threading
import logging
import colorlog  # 引入 colorlog 模块


# 配置日志
def setup_logger():
    # 创建一个日志记录器
    logger = logging.getLogger("pipline")
    logger.setLevel(logging.DEBUG)

    # 创建日志目录（如果不存在）
    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建一个控制台处理器，并设置颜色格式
    console_handler = logging.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    console_handler.setFormatter(console_formatter)

    # 创建一个文件处理器，并设置格式
    file_handler = logging.FileHandler(os.path.join(log_dir, "pipline.log"))
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # 将处理器添加到日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()




# 使用锁来确保只有一个 process_transcript 在运行
process_lock = threading.Lock()


def process_transcript(aligned_transcript, input_path, output_path):
    with process_lock:
        logging.info(f"文件 {input_path} 字幕翻译开始")
        sub_translate(
            aligned_transcript,
            api_key=api_key,
            base_url=base_url,
            model=llm_model,
            src_lang=src_lang,
            dst_lang=dst_lang,
            media_title=os.path.basename(input_path),
            context_window=10,
            batch_size=10,
            thread_count=10,
        )
        logging.info(f"文件 {input_path} 字幕翻译结束")
        with open(
            os.path.join("output/translated_transcripts", output_path) + ".json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(aligned_transcript, f, ensure_ascii=False)

        logging.info(f"文件 {input_path} 字幕分割开始")
        sub_segment(
            aligned_transcript,
            api_key=api_key,
            base_url=base_url,
            model=llm_model,
            word_limit=12,
            thread_count=20,
        )
        logging.info(f"文件 {input_path} 字幕分割结束")

        sub_optimize(aligned_transcript, src_lang=src_lang, dst_lang=dst_lang)
        logging.info(f"文件 {input_path} 字幕翻译优化")

        with open(
            os.path.join("output/segmented_transcripts", output_path) + ".json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(aligned_transcript, f, ensure_ascii=False)
        srt_path = os.path.join("output/srt", output_path) + ".srt"
        generate_bilingual_srt(aligned_transcript, srt_path)
        logging.info(f"文件 {input_path} 生成 srt 字幕")
        convert_srt_to_ass(
            srt_path,
            os.path.join("output/ass", output_path) + ".ass",
            original_style=original_style,
            translated_style=translated_style,
        )
        logging.info(f"文件 {input_path} 生成 ass 字幕")


def run():
    src_dir = Directory("选择视频文件所在文件夹")
    input_paths, output_paths = Files(
        src_dir,
        "",
        extensions=[".webm", ".mkv", ".flv", ".mp4", ".mp3", ".flac", ".ogg", ".wav"],
        mkdir=False,
    )
    file_count = len(input_paths)

    # 创建输出需要的文件夹
    for output_path in output_paths:
        output_dir = os.path.dirname(os.path.join("output/transcripts", output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_dir = os.path.dirname(
            os.path.join("output/aligned_transcripts", output_path)
        )
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_dir = os.path.dirname(
            os.path.join("output/translated_transcripts", output_path)
        )
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_dir = os.path.dirname(
            os.path.join("output/segmented_transcripts", output_path)
        )
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_dir = os.path.dirname(os.path.join("output/srt", output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_dir = os.path.dirname(os.path.join("output/ass", output_path))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    # 去除路径的扩展名
    for i in range(file_count):
        output_paths[i], _ = os.path.splitext(output_paths[i])

    whisper_model = wsx.load_model(
        whisper_model_type,
        device,
        compute_type=compute_type,
        download_root=whisper_model_dir,
    )
    align_model, metadata = wsx.load_align_model(
        language_code=transcibe_lang, device=device, model_dir=align_model_dir
    )

    for i in range(file_count):
        transcript_path = os.path.join("output/transcripts", output_paths[i]) + ".json"
        aligned_transcript_path = (
            os.path.join("output/aligned_transcripts", output_paths[i]) + ".json"
        )

        # 检查转录文件是否已经存在
        if os.path.exists(transcript_path) and os.path.exists(aligned_transcript_path):
            logging.info(f"文件 {input_paths[i]} 的转录结果已存在，直接读取")
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = json.load(f)
            with open(aligned_transcript_path, "r", encoding="utf-8") as f:
                aligned_transcript = json.load(f)
        else:
            logging.info(f"文件 {input_paths[i]} Whisper 转录开始")
            transcript, aligned_transcript = transcribe_batch(
                input_paths[i],
                device=device,
                whisper_model=whisper_model,
                align_model=align_model,
                metadata=metadata,
                batch_size=10,
                language=transcibe_lang,
            )
            logging.info(f"文件 {input_paths[i]} Whisper 转录结束")
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(transcript, f, ensure_ascii=False)
            with open(aligned_transcript_path, "w", encoding="utf-8") as f:
                json.dump(aligned_transcript, f, ensure_ascii=False)
        # 启动一个新线程来处理转录后的任务
        threading.Thread(
            target=process_transcript,
            args=(aligned_transcript, input_paths[i], output_paths[i]),
        ).start()
