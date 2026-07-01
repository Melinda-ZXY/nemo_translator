import streamlit as st

from translator_core import translate, to_json


EXAMPLES = [
    "主人开心",
    "主人不开心",
    "主人开心吗",
    "主人想要苹果",
    "主人想吃苹果",
    "我想充电",
    "尼莫很开心",
    "Nemo很开心",
    "主人喜欢小狗",
    "主人快离开",
    "主人想和我玩吗",
    "我的电池",
]


st.set_page_config(page_title="Nemo Translator", layout="centered")

st.title("Nemo Language Demo Translator")
st.caption("A deterministic rule-based demo for short Chinese sentences.")

example = st.selectbox("Examples", EXAMPLES, index=0)
text = st.text_input("Chinese input", value=example, placeholder="输入一句短中文，例如：主人想吃苹果")

result = translate(text)

st.subheader("Nemo output")
st.code(result["nemo"] or " ", language=None)

st.subheader("Token list")
st.json(result["tokens"], expanded=True)

st.subheader("Parsed structure")
st.json(result["parsed"], expanded=True)

with st.expander("Raw JSON"):
    st.code(to_json(result), language="json")

st.info("Unknown Chinese words are converted into pinyin loanwords automatically.")
