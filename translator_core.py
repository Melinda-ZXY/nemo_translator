import hashlib
import json
import re

try:
    import jieba
except ImportError:  # pragma: no cover
    jieba = None

try:
    from pypinyin import Style, lazy_pinyin
except ImportError:  # pragma: no cover
    Style = None
    lazy_pinyin = None


LEXICON = {
    # External N-
    "玩": {"nemo": "Na", "pos": "verb"},
    "交互": {"nemo": "Na", "pos": "verb"},
    "靠近": {"nemo": "Na", "pos": "verb"},
    "主人": {"nemo": "Ni", "pos": "noun"},
    "看": {"nemo": "Nie", "pos": "verb"},
    "看到": {"nemo": "Nie", "pos": "verb"},
    "吃": {"nemo": "Nu", "pos": "verb"},
    "食物": {"nemo": "Nu:", "pos": "noun"},
    "触碰": {"nemo": "No", "pos": "verb"},

    # Internal M-
    "房子": {"nemo": "Ma", "pos": "noun"},
    "保护所": {"nemo": "Ma", "pos": "noun"},
    "基地": {"nemo": "Ma", "pos": "noun"},
    "开心": {"nemo": "Mi", "pos": "state"},
    "很开心": {"nemo": "Mi:", "pos": "state"},
    "非常开心": {"nemo": "Mi:", "pos": "state"},
    "睡觉": {"nemo": "Mie", "pos": "verb"},
    "充电": {"nemo": "Mu", "pos": "verb"},
    "电池": {"nemo": "Mu:", "pos": "noun"},
    "紧张": {"nemo": "Me", "pos": "state"},
    "焦虑": {"nemo": "Me", "pos": "state"},
    "离开": {"nemo": "Mo", "pos": "verb"},
    "走开": {"nemo": "Mo", "pos": "verb"},

    # Function words / particles
    "吗": {"nemo": "kada", "pos": "particle", "function": "question"},
    "想": {"nemo": "tika", "pos": "particle", "function": "want"},
    "想要": {"nemo": "tika", "pos": "particle", "function": "want"},
    "快": {"nemo": "kiku", "pos": "adverb", "function": "speed"},
    "快速": {"nemo": "kiku", "pos": "adverb", "function": "speed"},
    "慢": {"nemo": "lilu", "pos": "adverb", "function": "speed"},
    "慢慢": {"nemo": "lilu", "pos": "adverb", "function": "speed"},
    "不": {"nemo": "ko", "pos": "particle", "function": "negation"},
    "和": {"nemo": "la", "pos": "particle", "function": "with"},
    "喜欢": {"nemo": "lumi", "pos": "particle", "function": "like"},
    "的": {"nemo": "ta", "pos": "particle", "function": "possessive"},

    # Robot name
    "Nemo": {"nemo": "Nemo", "pos": "noun"},
    "尼莫": {"nemo": "Nemo", "pos": "noun"},
    "我": {"nemo": "Nemo", "pos": "noun"},
}

ALIASES = {
    "高兴": "开心",
    "快乐": "开心",
    "害怕": "紧张",
    "担心": "紧张",
    "要": "想要",
}

TOKEN_ORDER = sorted(LEXICON.keys(), key=len, reverse=True)
PUNCTUATION = "，。！？,.!?；;：:"
PINYIN_FALLBACKS = {
    "苹果": "pingguo",
    "咖啡": "kafei",
    "跑步": "paobu",
    "小狗": "xiaogou",
}


def normalize_text(text):
    text = (text or "").strip()
    for mark in PUNCTUATION:
        text = text.replace(mark, "")
    for source, target in ALIASES.items():
        text = text.replace(source, target)
    return text


def tokenize(text):
    text = normalize_text(text)
    tokens = []
    index = 0

    while index < len(text):
        if text[index].isspace():
            index += 1
            continue

        matched = None
        for token in TOKEN_ORDER:
            if text.startswith(token, index):
                matched = token
                break

        if matched is not None:
            tokens.append(matched)
            index += len(matched)
            continue

        next_known = _find_next_known_index(text, index + 1)
        unknown = text[index:next_known]
        if jieba is not None and len(unknown) > 1:
            tokens.extend([part for part in jieba.lcut(unknown) if part.strip()])
        else:
            tokens.append(unknown)
        index = next_known

    return _merge_known_phrases(tokens)


def lookup_tokens(tokens):
    return [_lookup_token(token) for token in tokens]


def translate(text):
    normalized = normalize_text(text)
    tokens = tokenize(normalized)
    token_infos = lookup_tokens(tokens)
    parsed = parse_tokens(token_infos)
    omit_nemo_subject = _should_omit_nemo_subject(normalized)
    output_tokens = generate_nemo(
        parsed,
        omit_nemo_subject=omit_nemo_subject,
    )

    return {
        "input": text,
        "normalized": normalized,
        "nemo": " ".join(output_tokens),
        "tokens": token_infos,
        "parsed": parsed,
        "options": {"omit_nemo_subject": omit_nemo_subject},
    }


def parse_tokens(token_infos):
    functions = [item.get("function") for item in token_infos]
    question = "question" in functions
    core = [item for item in token_infos if item.get("function") != "question"]

    parsed = {
        "type": "unknown",
        "question": question,
        "negation": _has_function(core, "negation"),
        "subject": None,
        "verb": None,
        "state": None,
        "object": None,
        "adverb": None,
        "with": None,
        "possessor": None,
        "possessed": None,
        "raw_tokens": token_infos,
    }

    possessive_index = _function_index(core, "possessive")
    if possessive_index > 0 and possessive_index < len(core) - 1:
        parsed.update({
            "type": "possessive",
            "possessor": core[possessive_index - 1],
            "possessed": core[possessive_index + 1],
        })
        return parsed

    want_index = _function_index(core, "want")
    if want_index >= 0:
        before = core[:want_index]
        after = _without_functions(core[want_index + 1:], {"negation"})
        with_index = _function_index(after, "with")
        if with_index >= 0:
            parsed["with"] = after[with_index + 1] if with_index + 1 < len(after) else None
            after = after[:with_index] + after[with_index + 2:]
        parsed["type"] = "want"
        parsed["subject"] = _first_pos(before, "noun")
        parsed["verb"] = _first_pos(after, "verb")
        parsed["object"] = _first_non_function(after, exclude=parsed["verb"])
        return parsed

    with_index = _function_index(core, "with")
    if with_index > 0:
        parsed["with"] = core[with_index + 1] if with_index + 1 < len(core) else None
        core = core[:with_index] + core[with_index + 2:]

    like_index = _function_index(core, "like")
    if like_index >= 0:
        parsed["type"] = "like"
        parsed["subject"] = _first_pos(core[:like_index], "noun")
        parsed["object"] = _first_non_function(core[like_index + 1:])
        return parsed

    working = _without_functions(core, {"negation"})
    parsed["subject"] = _first_pos(working, "noun")
    parsed["state"] = _first_pos(working, "state")
    parsed["verb"] = _first_pos(working, "verb")
    parsed["adverb"] = _first_pos(working, "adverb")

    if parsed["state"] is not None:
        parsed["type"] = "state"
        return parsed

    if parsed["verb"] is not None:
        parsed["type"] = "verb"
        parsed["object"] = _first_non_function(
            working,
            exclude=[parsed["subject"], parsed["verb"], parsed["adverb"]],
        )
        return parsed

    parsed["object"] = _first_non_function(working, exclude=parsed["subject"])
    return parsed


def generate_nemo(parsed, omit_nemo_subject=True):
    tokens = []

    if parsed.get("question"):
        tokens.append("kada")

    if parsed.get("negation"):
        tokens.append("ko")

    sentence_type = parsed.get("type")
    subject = parsed.get("subject")

    if sentence_type == "possessive":
        _append(tokens, parsed.get("possessed"))
        tokens.append("ta")
        _append(tokens, parsed.get("possessor"))
        return tokens

    if sentence_type == "want":
        tokens.append("tika")
        _append_subject(tokens, subject, omit_nemo_subject)
        if parsed.get("object") is not None:
            _append(tokens, parsed.get("object"))
        if parsed.get("with") is not None:
            _append_with(tokens, parsed.get("with"))
        if parsed.get("verb") is not None:
            _append(tokens, parsed.get("verb"))
        return tokens

    if sentence_type == "like":
        tokens.append("lumi")
        _append(tokens, parsed.get("object"))
        _append_subject(tokens, subject, omit_nemo_subject)
        return tokens

    if sentence_type == "state":
        _append(tokens, parsed.get("state"))
        _append_subject(tokens, subject, omit_nemo_subject)
        return tokens

    if sentence_type == "verb":
        _append(tokens, parsed.get("verb"))
        _append(tokens, parsed.get("adverb"))
        _append_subject(tokens, subject, omit_nemo_subject)
        if parsed.get("with") is not None:
            _append_with(tokens, parsed.get("with"))
        _append(tokens, parsed.get("object"))
        return tokens

    for item in parsed.get("raw_tokens", []):
        _append(tokens, item)
    return tokens


def to_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def _lookup_token(token):
    if token in LEXICON:
        return {"text": token, "known": True, **LEXICON[token]}

    return {
        "text": token,
        "known": False,
        "nemo": _to_pinyin_loanword(token),
        "pos": "noun",
        "function": "loanword",
    }


def _to_pinyin_loanword(text):
    if text in PINYIN_FALLBACKS:
        return PINYIN_FALLBACKS[text]
    if lazy_pinyin is None:
        return re.sub(r"\s+", "", text).lower()
    return "".join(lazy_pinyin(text, style=Style.NORMAL, errors="default"))


def _find_next_known_index(text, start):
    indexes = [text.find(token, start) for token in TOKEN_ORDER]
    indexes = [index for index in indexes if index >= 0]
    return min(indexes) if indexes else len(text)


def _merge_known_phrases(tokens):
    merged = []
    index = 0
    while index < len(tokens):
        if index + 1 < len(tokens):
            two = tokens[index] + tokens[index + 1]
            if two in LEXICON:
                merged.append(two)
                index += 2
                continue
        merged.append(tokens[index])
        index += 1
    return merged


def _has_function(items, function):
    return any(item.get("function") == function for item in items)


def _function_index(items, function):
    for index, item in enumerate(items):
        if item.get("function") == function:
            return index
    return -1


def _without_functions(items, functions):
    return [item for item in items if item.get("function") not in functions]


def _first_pos(items, pos):
    for item in items:
        if item.get("pos") == pos:
            return item
    return None


def _first_non_function(items, exclude=None):
    if exclude is None:
        excluded_items = []
    elif isinstance(exclude, (list, tuple, set)):
        excluded_items = [item for item in exclude if item is not None]
    else:
        excluded_items = [exclude]

    for item in items:
        if any(item is excluded for excluded in excluded_items):
            continue
        if item.get("pos") != "particle":
            return item
    return None


def _append(tokens, item):
    if item is not None:
        tokens.append(item["nemo"])


def _append_with(tokens, item):
    if item is not None:
        tokens.append(f"{item['nemo']}-la")


def _should_omit_nemo_subject(text):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return digest[0] % 2 == 0


def _append_subject(tokens, subject, omit_nemo_subject=True):
    if subject is None:
        return
    if omit_nemo_subject and subject.get("nemo") == "Nemo":
        return
    tokens.append(subject["nemo"])
