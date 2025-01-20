import pysrt
import pysubs2


def convert_srt_to_ass(srt_file, ass_file, original_style, translated_style):
    # 读取SRT文件
    subs = pysrt.open(srt_file)

    # 创建ASS文件对象
    ass_subs = pysubs2.SSAFile()

    # 添加样式
    ass_subs.styles["Original"] = original_style
    ass_subs.styles["Translated"] = translated_style

    # 遍历SRT字幕
    for sub in subs:
        # 分割原文和译文
        lines = sub.text.strip().split("\n")
        original_text = lines[0]
        translated_text = lines[1]
        if original_text:
            event = pysubs2.SSAEvent(
                start=pysubs2.make_time(
                    h=sub.start.hours,
                    m=sub.start.minutes,
                    s=sub.start.seconds,
                    ms=sub.start.milliseconds,
                ),
                end=pysubs2.make_time(
                    h=sub.end.hours,
                    m=sub.end.minutes,
                    s=sub.end.seconds,
                    ms=sub.end.milliseconds,
                ),
                text=original_text,
                style="Original",
            )
            ass_subs.events.append(event)

        # 添加译文
        if translated_text:
            event = pysubs2.SSAEvent(
                start=pysubs2.make_time(
                    h=sub.start.hours,
                    m=sub.start.minutes,
                    s=sub.start.seconds,
                    ms=sub.start.milliseconds,
                ),
                end=pysubs2.make_time(
                    h=sub.end.hours,
                    m=sub.end.minutes,
                    s=sub.end.seconds,
                    ms=sub.end.milliseconds,
                ),
                text=translated_text,
                style="Translated",
            )
            ass_subs.events.append(event)

    # 保存ASS文件
    ass_subs.save(ass_file)


