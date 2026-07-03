from __future__ import annotations

import base64
from html import escape
from pathlib import Path


ASSET_DIR = Path(__file__).parent / "assets" / "nemo_lan"


def render_orthography_html(nemo_text: str) -> str:
    items = []
    for token in _orthography_tokens(nemo_text):
        asset_name = _asset_name(token)
        asset_path = ASSET_DIR / f"{asset_name}.svg"
        if asset_path.exists():
            encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
            items.append(
                "<span class='nemo-glyph' title='{title}'>"
                "<img src='data:image/svg+xml;base64,{encoded}' alt='{title}'/>"
                "</span>".format(title=escape(token), encoded=encoded)
            )
        else:
            items.append(
                "<span class='nemo-glyph nemo-missing' title='Missing glyph'>{token}</span>".format(
                    token=escape(token)
                )
            )

    if not items:
        items.append("<span class='nemo-glyph nemo-missing'> </span>")

    styles = """
<style>
.nemo-orthography {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 0 6px;
}
.nemo-glyph {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  height: 58px;
}
.nemo-glyph img {
  display: block;
  max-width: 58px;
  max-height: 58px;
  object-fit: contain;
}
.nemo-missing {
  height: auto;
  min-height: 34px;
  padding: 4px 8px;
  border: 1px dashed #888;
  border-radius: 4px;
  color: #555;
  font-size: 14px;
  line-height: 1.2;
}
</style>
"""
    return styles + '<div class="nemo-orthography">' + "".join(items) + "</div>"


def _orthography_tokens(nemo_text: str) -> list[str]:
    tokens: list[str] = []
    for token in (nemo_text or "").split():
        tokens.extend(part for part in token.split("-") if part)
    return tokens


def _asset_name(token: str) -> str:
    normalized = "".join(char for char in token if char.isalpha() or char == ":")
    normalized = _expand_long_vowels(normalized)
    if normalized.lower() == "nemo":
        return "nemo"
    return normalized[:1].upper() + normalized[1:].lower()


def _expand_long_vowels(token: str) -> str:
    for vowel in "aeiouAEIOU":
        token = token.replace(f"{vowel}:", vowel * 2)
    return token.replace(":", "")
