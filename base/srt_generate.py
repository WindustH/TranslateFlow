import json

def generate_bilingual_srt(json_data, output_file):
    """
    将 JSON 数据生成双语 SRT 字幕文件

    :param json_data: 包含字幕信息的 JSON 数据
    :param output_file: 输出的 SRT 文件路径
    """
    segments = json_data["segments"]
    srt_content = []
    segment_index = 1  # SRT 字幕序号从 1 开始

    for segment in segments:
        # 获取原文和译文的分段
        original_segments = segment.get("segments", [segment["text"]])
        translation_segments = segment.get("translation_segments", [segment["translation"]])

        # 获取单词列表
        words = segment.get("words", [])

        # 初始化单词索引
        word_index = 0

        # 遍历每个小分段
        for i in range(len(original_segments)):
            original_text = original_segments[i].strip()
            translation_text = translation_segments[i].strip() if i < len(translation_segments) else ""

            # 计算小分段的单词数量
            word_count = len(original_text.split())

            # 计算小分段的开始时间和结束时间
            if words and word_index + word_count <= len(words):
                start_time = words[word_index]["start"]
                end_time = words[word_index + word_count - 1]["end"]
                word_index += word_count  # 更新单词索引
            else:
                # 如果没有单词信息或单词数量不匹配，使用分段的全局时间
                start_time = segment["start"]
                end_time = segment["end"]

            # 将时间格式化为 SRT 时间格式 (HH:MM:SS,ms)
            start_time_str = format_time(start_time)
            end_time_str = format_time(end_time)

            # 生成 SRT 字幕块
            srt_block = f"{segment_index}\n{start_time_str} --> {end_time_str}\n{original_text}\n{translation_text}\n"
            srt_content.append(srt_block)
            segment_index += 1

    # 将 SRT 内容写入文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_content))

def format_time(seconds):
    """
    将秒数格式化为 SRT 时间格式 (HH:MM:SS,ms)

    :param seconds: 秒数
    :return: 格式化后的时间字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{int(seconds):02},{milliseconds:03}"