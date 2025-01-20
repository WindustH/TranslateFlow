import whisperX.whisperx as wsx


def fill_missing_times(segment):
    """
    填充缺失的 'start' 和 'end'，并处理连续缺失的情况。
    """
    words = segment["words"]
    n = len(words)
    i = 0
    while i < n:
        # 找到连续缺失 'start' 和 'end' 的单词范围
        if "start" not in words[i] or "end" not in words[i]:
            start_index = i
            end_index = i

            # 找到连续缺失的范围
            while end_index < n and (
                "start" not in words[end_index] or "end" not in words[end_index]
            ):
                end_index += 1

            # 计算前一个单词的 'end' 和后一个单词的 'start'
            prev_end = (
                words[start_index - 1]["end"] if start_index > 0 else segment["start"]
            )
            next_start = words[end_index]["start"] if end_index < n else segment["end"]

            # 均匀分配时间
            total_time = next_start - prev_end
            time_per_word = total_time / (end_index - start_index + 1)

            # 填充缺失的 'start' 和 'end'
            for j in range(start_index, end_index):
                words[j]["start"] = prev_end + (j - start_index) * time_per_word
                words[j]["end"] = prev_end + (j - start_index + 1) * time_per_word

            i = end_index  # 跳过已处理的范围
        else:
            i += 1


def transcribe(
    audio_file,
    device="cuda",
    batch_size=16,
    compute_type="float16",
    language="en",
    whisper_model_dir="models/whisper",
    align_model_dir="models/align",
    whisper_model_type="medium"
):
    model = wsx.load_model(
        whisper_model_type, device, compute_type=compute_type, download_root=whisper_model_dir
    )
    align_model, metadata = wsx.load_align_model(
        language_code=language, device=device, model_dir=align_model_dir
    )

    audio = wsx.load_audio(audio_file)
    transcript = model.transcribe(audio, language=language, batch_size=batch_size)
    aligned = wsx.align(
        transcript["segments"],
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    for segment in aligned["segments"]:
        fill_missing_times(segment)
    aligned = {"segments": aligned["segments"]}
    return transcript, aligned


def transcribe_batch(
    audio_file, device, whisper_model, align_model, metadata, batch_size=16, language="en"
):
    audio = wsx.load_audio(audio_file)
    transcript = whisper_model.transcribe(audio, language=language, batch_size=batch_size)
    aligned = wsx.align(
        transcript["segments"],
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    for segment in aligned["segments"]:
        fill_missing_times(segment)
    aligned = {"segments": aligned["segments"]}
    return transcript, aligned
