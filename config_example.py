import pysubs2

api_key = ""
base_url = "https://api.deepseek.com"
llm_model = "deepseek-chat"
device = "cuda"
compute_type = "float16"
transcibe_lang = "en"
src_lang = "en-US"
dst_lang = "zh-CN"
whisper_model_type = "medium"
whisper_model_dir = "models/whisper"
align_model_dir = "models/align"

# 定义样式
original_style = pysubs2.SSAStyle(
    fontname="Source Han Sans SC Heavy",
    fontsize=20,
    primarycolor=pysubs2.Color(216, 222, 233, 0),
    outlinecolor=pysubs2.Color(46, 52, 64, 0),
    backcolor=pysubs2.Color(46, 52, 64, 200),
    bold=True,
    outline=1.2,
    alignment=2,  # 底部居中
    marginv=25,
)

translated_style = pysubs2.SSAStyle(
    fontname="Source Han Sans SC Heavy",
    fontsize=16,
    primarycolor=pysubs2.Color(143, 188, 187, 0),
    outlinecolor=pysubs2.Color(46, 52, 64, 0),
    backcolor=pysubs2.Color(46, 52, 64, 200),
    italic=True,
    outline=1.2,
    alignment=2,
    marginv=5,
)
