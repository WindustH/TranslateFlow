import re


def sub_optimize(dict, src_lang, dst_lang):
    """
    优化字幕到符合规范

    :param dict: 包含字幕信息的词典
    """
    segments = dict["segments"]
    match src_lang:
        case "en-US":
            for segment in segments:
                segment["segments"] = [en_US(seg) for seg in segment["segments"]]
        case "zh-CN":
            for segment in segments:
                segment["segments"] = [zh_CN(seg) for seg in segment["segments"]]
    match dst_lang:
        case "en-US":
            for segment in segments:
                segment["translation_segments"] = [en_US(seg) for seg in segment["translation_segments"]]
        case "zh-CN":
            for segment in segments:
                segment["translation_segments"] = [zh_CN(seg) for seg in segment["translation_segments"]]
    if src_lang == "en-US" and dst_lang == "zh-CN":
        for segment in segments:
            for segment in segments:
                segment["translation_segments"] = [en_US2zh_CN(seg) for seg in segment["translation_segments"]]


def en_US(sentence):
    """
    去除英文句子句末的句号
    :param sentence: 英文句子
    :return: 去除句末句号后的英文句子
    """
    if sentence.endswith(" "):
        sentence=sentence.rstrip()
    if sentence.endswith(".") or sentence.endswith(","):
        return sentence[:-1]
    else:
        return sentence


def zh_CN(sentence):
    """
    替换中文句子句中的逗号、顿号、分号、句号为空格，去除句末的句号
    :param sentence: 中文句子
    :return: 替换并去除句末句号后的中文句子
    """
    punctuation_list = ["，", "、", "；", "。"]
    for punctuation in punctuation_list:
        sentence = sentence.replace(punctuation, " ")
    if sentence.endswith(" "):
        return sentence.rstrip()
    else:
        return sentence

def en_US2zh_CN(sentence):
    # 英文单词与中文间前后均空格
    sentence = re.sub(r"([a-zA-Z]+)([\u4e00-\u9fa5])", r"\1 \2", sentence)
    sentence = re.sub(r"([\u4e00-\u9fa5])([a-zA-Z]+)", r"\1 \2", sentence)

    # 数字与中文或英文前后均空格
    sentence = re.sub(r"(\d+)([a-zA-Z\u4e00-\u9fa5])", r"\1 \2", sentence)
    sentence = re.sub(r"([a-zA-Z\u4e00-\u9fa5])(\d+)", r"\1 \2", sentence)

    # 数字与英文单位（1~2 个字母）间不空格
    sentence = re.sub(r"(\d+) ([a-zA-Z]{1,2}[^a-zA-Z])", r"\1\2", sentence)

    # 1~2 个英文字母后接数字不空格
    sentence = re.sub(r"([^a-zA-Z][a-zA-Z]{1,2}) (\d+)", r"\1\2", sentence)

    return sentence
