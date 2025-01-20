import pycountry

def get_language_name(lang_code):
    # 分割语言代码和国家代码
    parts = lang_code.split('-')
    lang_part = parts[0]
    if len(parts) > 1:
        country_part = parts[1]
    else:
        country_part = None

    # 查找语言
    language = pycountry.languages.get(alpha_2=lang_part)
    if language:
        lang_name = language.name
    else:
        return f'未找到语言代码 {lang_part} 对应的语言'

    # 如果有国家代码，查找国家
    if country_part:
        country = pycountry.countries.get(alpha_2=country_part)
        if country:
            return f'{lang_name}({country.name})'
        else:
            return f'{lang_name}(未知国家代码 {country_part})'
    else:
        return lang_name