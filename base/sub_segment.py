from base.api_request import api_request
import threading
import json
import time
import logging
import colorlog
import os
import jieba

split_char = " ,.;:!，。？：；！"


# 配置日志
def setup_logger():
    # 创建一个日志记录器
    logger = logging.getLogger("sub_segment")
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
    file_handler = logging.FileHandler(os.path.join(log_dir, "sub_segment.log"))
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # 将处理器添加到日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()

prompt_multi = """
The user will ask you to segment the subtitles into smaller parts in a way that is suitable for pauses and does not split individual grammatical structures. Each segmented part should not exceed the specified number of words. You must not add, delete, or modify any character. Any segment must not be empty or all spaces. Output in JSON format.

EXAMPLE JSON INPUT:
{
    "word_limit": 9,
    "input": "This is a sample sentence. You should process this sentence according to my instructions."
}

EXAMPLE JSON OUTPUT:
{
    "output": [
        "This is a sample sentence. ",
        "You should process this sentence ",
        "according to my instructions."
    ]
}
"""

prompt_spec = """
The user will ask you to convert a long sentence into a specified number of short sentences. The original meaning should not be altered. Do not use sentences with semantic repetition. Any short sentence must not be empty or all spaces. Output in JSON format.

EXAMPLE JSON INPUT:
{
    "input": "This is a sample sentence. You should process this sentence according to my instructions.",
    "count": 3
}

EXAMPLE JSON OUTPUT:
{
    "output": [
        "This is a sample sentence. ",
        "You should process this sentence ",
        "according to my instructions."
    ]
}
"""

prompt_duo = """
The user will ask you to split a long sentence into two parts in a way that is suitable for pauses and does not split individual grammatical structures. You must not add, delete, or modify any character. Output in JSON format.

EXAMPLE JSON INPUT:
{
    "input": "You should process this sentence according to my instructions."
}

EXAMPLE JSON OUTPUT:
{
    "output": [
        "You should process this sentence ",
        "according to my instructions."
    ]
}

"output" should include two string, which cannot be empty, consist entirely of spaces, or contain only punctuation marks.
"""


def align_segments(source_text, segments):
    """
    对齐分割后的小段与原字符串，确保每个小段与原字符串的重合字符最多。
    处理重叠时，将重叠部分留给邻近较短的片段，并去除较长片段的重合部分。
    修正小段中与原字符串不一致的字符。

    :param original_text: 原始字符串
    :param segments: 分割后的小段列表
    :return: 对齐后的小段列表
    """
    aligned_segments = []
    original_length = len(source_text)
    segment_positions = []  # 记录每个小段的起始和结束位置

    # 计算每个片段的预期起始位置（累加长度）
    expected_starts = []
    current_start = 0
    for segment in segments:
        expected_starts.append(current_start)
        current_start += len(segment)

    # 找到每个小段在原字符串中的最佳匹配位置
    for idx, segment in enumerate(segments):
        segment_length = len(segment)
        max_overlap = -1
        best_start = 0
        best_positions = []  # 存储所有最大重合的位置

        # 遍历所有可能的位置，找到最大重合的位置
        for start in range(original_length - segment_length + 1):
            overlap = 0
            for i in range(segment_length):
                if segment[i] == source_text[start + i]:
                    overlap += 1
            if overlap > max_overlap:
                max_overlap = overlap
                best_positions = [start]  # 重置最佳位置列表
            elif overlap == max_overlap:
                best_positions.append(start)  # 添加相同最大重合的位置

        # 如果有多个最大重合位置，选择与预期起始位置最接近的一个
        if len(best_positions) > 1:
            expected_start = expected_starts[idx]  # 预期起始位置
            min_offset = float("inf")
            best_start = best_positions[0]  # 默认选择第一个
            for pos in best_positions:
                offset = abs(pos - expected_start)
                if offset < min_offset:
                    min_offset = offset
                    best_start = pos
        else:
            best_start = best_positions[0]  # 只有一个最大重合位置

        segment_positions.append((best_start, best_start + segment_length))

    # 处理小段之间的重叠
    segment_positions.sort()  # 按起始位置排序
    for i in range(len(segment_positions) - 1):
        current_start, current_end = segment_positions[i]
        next_start, next_end = segment_positions[i + 1]

        if current_end > next_start:
            # 比较当前片段和下一个片段的长度
            current_length = current_end - current_start
            next_length = next_end - next_start

            if current_length > next_length:
                # 当前片段较长，去除重叠部分
                segment_positions[i] = (current_start, next_start)
            else:
                # 下一个片段较长，去除重叠部分
                segment_positions[i + 1] = (current_end, next_end)

    # 根据调整后的位置生成对齐后的小段
    for start, end in segment_positions:
        # 获取原字符串的对应部分
        original_segment = source_text[start:end]
        aligned_segments.append(original_segment)  # 直接使用原字符串的对应部分

    # 处理未分配的字符
    all_covered = [False] * original_length
    for start, end in segment_positions:
        for i in range(start, end):
            all_covered[i] = True

    # 找到未分配的字符，并分配给邻近的最短小段
    for i in range(original_length):
        if not all_covered[i]:
            # 找到最近的已分配字符
            left = i - 1
            right = i + 1
            while left >= 0 and not all_covered[left]:
                left -= 1
            while right < original_length and not all_covered[right]:
                right += 1

            # 如果左右都有片段，选择较短的片段
            if left >= 0 and right < original_length:
                # 找到左边片段的长度
                left_segment_index = next(
                    (
                        idx
                        for idx, (start, end) in enumerate(segment_positions)
                        if start <= left < end
                    ),
                    None,
                )
                if left_segment_index is not None:
                    left_length = (
                        segment_positions[left_segment_index][1]
                        - segment_positions[left_segment_index][0]
                    )
                else:
                    left_length = float("inf")  # 如果没有找到左边片段，设为无穷大

                # 找到右边片段的长度
                right_segment_index = next(
                    (
                        idx
                        for idx, (start, end) in enumerate(segment_positions)
                        if start <= right < end
                    ),
                    None,
                )
                if right_segment_index is not None:
                    right_length = (
                        segment_positions[right_segment_index][1]
                        - segment_positions[right_segment_index][0]
                    )
                else:
                    right_length = float("inf")  # 如果没有找到右边片段，设为无穷大

                if left_length <= right_length:
                    # 分配给左边的小段
                    aligned_segments[left_segment_index] += source_text[i]
                    all_covered[i] = True
                else:
                    # 分配给右边的小段
                    aligned_segments[right_segment_index] = (
                        source_text[i] + aligned_segments[right_segment_index]
                    )
                    all_covered[i] = True
            elif left >= 0:
                # 只有左边有片段，分配给左边
                left_segment_index = next(
                    (
                        idx
                        for idx, (start, end) in enumerate(segment_positions)
                        if start <= left < end
                    ),
                    None,
                )
                if left_segment_index is not None:
                    aligned_segments[left_segment_index] += source_text[i]
                    all_covered[i] = True
            elif right < original_length:
                # 只有右边有片段，分配给右边
                right_segment_index = next(
                    (
                        idx
                        for idx, (start, end) in enumerate(segment_positions)
                        if start <= right < end
                    ),
                    None,
                )
                if right_segment_index is not None:
                    aligned_segments[right_segment_index] = (
                        source_text[i] + aligned_segments[right_segment_index]
                    )
                    all_covered[i] = True
            else:
                # 如果没有左右片段（理论上不会发生），直接分配给第一个片段
                aligned_segments[0] += source_text[i]
                all_covered[i] = True

    return aligned_segments


def split_original(text, api_key, base_url, model, word_limit):
    """
    分割原文字幕
    :param text: 原文字幕
    :param api_key: OpenAI API密钥
    :param base_url: API基础URL
    :param model: API模型
    :param word_limit: 分割后词数限制
    :return: 分割后的原文字幕列表
    """
    # 检测原文词数是否已经低于最大词数
    if len(text.split()) <= word_limit:
        # 如果词数已经低于限制，直接返回原文
        return [text]

    # 分割原始字幕
    messages_prim = [
        {"role": "system", "content": prompt_multi},
        {
            "role": "user",
            "content": json.dumps({"word_limit": word_limit, "input": text}),
        },
    ]

    try:
        response_prim = json.loads(api_request(api_key, base_url, model, messages_prim))
        segments = [seg for seg in response_prim["output"] if seg.strip(split_char)]

        # 检测是否有分段超过最大长度
        i = 0
        while i < len(segments):
            if len(segments[i].split()) > word_limit:
                logger.warning(
                    f"""
                    原文分割：分段 {i} 超过最大长度
                    发生在：{text}
                    初次响应：{response_prim}
                    """
                )
                messages_duo = [
                    {"role": "system", "content": prompt_duo},
                    {"role": "user", "content": json.dumps({"input": segments[i]})},
                ]
                try:
                    response_duo = json.loads(
                        api_request(api_key, base_url, model, messages_duo)
                    )
                    if "output" in response_duo:
                        response_duo["output"] = [
                            str
                            for str in response_duo["output"]
                            if str.strip(split_char)
                        ]
                        if len(response_duo["output"]) > 1:
                            segments[i : i + 1] = response_duo["output"]
                        else:
                            raise Exception(
                                f"""
                                原文分割：api 返回结果无效
                                响应：{response_duo}
                                """
                            )
                    else:
                        raise Exception(
                            f"""
                            原文分割：api 返回的 JSON 无效
                            响应：{response_duo}
                            """
                        )
                except Exception as e:
                    logger.error(
                        f"""
                        原文分割：分割最大片段失败：{e}
                        发生在：{text}
                        按照长度分割
                        """
                    )
                    mid = len(segments[i]) // 2
                    segments[i : i + 1] = [segments[i][:mid], segments[i][mid:]]
            else:
                i += 1
    except Exception as e:
        logger.error(
            f"""
            原文分割失败： {e}
            发生在：{text}
            """
        )
        segments = [text]

    # 调用 align_segments 函数，确保原文分割结果与原字符串对齐
    aligned_segments = align_segments(text, segments)

    return aligned_segments


def merge_punctuation(words):
    """
    将标点符号与前一个词合并
    :param words: 分词结果列表
    :return: 合并后的分词结果列表
    """
    merged_words = []
    for word in words:
        if word in split_char:
            # 如果当前词是标点符号，将其与前一个词合并
            if merged_words:
                merged_words[-1] += word
        else:
            # 否则直接添加到结果中
            merged_words.append(word)
    return merged_words


def dist_prop(arr,sum_dist,mini):
    """
    按比例分配
    :param arr：待分配数组
    :param mini：最小分配量
    :return: 分配数组
    """
    sum_etc = sum_dist - len(arr) * mini
    sum_arr = sum(arr)
    dist_etc = [a / sum_arr - mini / sum_dist for a in arr]
    dist_etc = [max(x, 0) for x in dist_etc]
    dist_etc = [x / sum(dist_etc) for x in dist_etc]
    indices_arr = [int(sum(dist_etc[0:x]) * sum_etc) for x in range(1, len(arr))]
    indices_arr = [0] + indices_arr + [sum_etc]
    dist_arr = [mini + indices_arr[i + 1] - indices_arr[i] for i in range(len(arr))]
    return dist_arr

def split_translated(text, count):
    """
    分割译文字幕
    :param text: 译文字幕
    :param count: 预期的分割段数
    :return: 分割后的译文字幕列表
    """
    # 初次分段：根据 split_char 中的字符进行分段
    segments = []
    start = 0
    for i, char in enumerate(text):
        if char in split_char:
            # 如果遇到分隔符，将前面的部分作为一个分段
            segment = text[start : i + 1]  # 包含分隔符
            # 检查分段是否只包含分隔符
            if segment.strip(split_char):  # 如果分段去除分隔符后不为空
                segments.append(segment)
            else:
                # 如果分段只包含分隔符，则将其与前一个分段合并
                if segments:
                    segments[-1] += segment
                else:
                    segments.append(segment)  # 如果这是第一个分段，直接添加
            start = i + 1
    # 添加最后一段（如果没有以分隔符结尾）
    if start < len(text):
        segments.append(text[start:])

    # 检查初次分段的数量是否已经满足要求
    if len(segments) == count:
        return segments  # 直接返回结果
    elif len(segments) < count:
        # 如果初次分段数量不足，继续按原逻辑进行进一步分割
        pass
    else:
        # 如果初次分段数量超过要求，合并相邻片段
        while len(segments) > count:
            # 找到合并后长度最短的两个相邻片段
            min_length = float("inf")
            merge_index = 0
            for i in range(len(segments) - 1):
                # 计算合并后的长度
                merged_length = len(segments[i]) + len(segments[i + 1])
                if merged_length < min_length:
                    min_length = merged_length
                    merge_index = i
            # 合并这两个片段
            segments[merge_index] = segments[merge_index] + segments[merge_index + 1]
            # 删除被合并的片段
            segments.pop(merge_index + 1)
        return segments  # 返回合并后的结果

    # 对每个初次分段调用 jieba.cut 进行分词，并缓存分词结果
    segment_words = []  # 缓存每个初次分段的分词结果
    word_counts = []  # 每个初次分段的词数
    for segment in segments:
        # 使用 jieba 进行精确分词
        words = list(jieba.cut(segment, cut_all=False))
        # 将标点符号与前一个词合并
        merged_words = merge_punctuation(words)
        segment_words.append(merged_words)  # 缓存分词结果
        word_counts.append(len(merged_words))  # 记录词数

    # 按照比例分配分割数 最小为 1
    count_dist = dist_prop(word_counts,count,1)
    # 对每个初次分段进行进一步分割
    segments_final = []
    for segment, words, count_segment in zip(segments, segment_words, count_dist):
        if count_segment <= 1:
            # 如果分配的分割数小于等于 1，直接添加到结果中
            segments_final.append(segment)
            continue
        # 计算每个分割点的位置
        segment_length = len(words) / count_segment
        word_split_indices = [int(i * segment_length) for i in range(1, count_segment)]
        # 根据分割点进行分割
        start = 0
        for index in word_split_indices:
            sub_segment = "".join(words[start:index])
            segments_final.append(sub_segment)
            start = index
        # 添加最后一段
        segments_final.append("".join(words[start:]))

    return segments_final


def split_segment(segment_text, translation_text, api_key, base_url, model, word_limit):
    # 分割原文字幕
    aligned_segments = split_original(
        segment_text, api_key, base_url, model, word_limit
    )

    # 分割译文字幕
    segment_count = len(aligned_segments)
    translation_segments = split_translated(translation_text, segment_count)

    return aligned_segments, translation_segments


def sub_segment(
    dict,
    api_key,
    base_url,
    model,
    word_limit=12,
    thread_count=20,
):
    """
    将字幕分割成不超过特定词数的小段
    把翻译分割成相同段数

    :param dict: 包含字幕信息的词典
    :param api_key: OpenAI API密钥
    :param base_url: API基础URL
    :param model: API模型
    :param word_limit: 分割后词数限制
    :param thread_count: 并发线程数量
    """
    segments = dict["segments"]
    threads = []  # 初始化线程列表

    def worker(index):
        segment = segments[index]
        # 检查是否已经有合法的分割
        if "segments" in segment and "translation_segments" in segment:
            if all(seg.strip() for seg in segment["segments"]) and all(
                seg.strip() for seg in segment["translation_segments"]
            ):
                logger.info(f"字幕 {index} 已有合法分割，跳过处理")
                return

        # 获取当前字幕
        segment_text = segment["text"]
        translation_text = segment["translation"]

        # 调用分割函数
        segments[index]["segments"], segments[index]["translation_segments"] = (
            split_segment(
                segment_text, translation_text, api_key, base_url, model, word_limit
            )
        )

    for i in range(len(segments)):
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
