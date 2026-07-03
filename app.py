import streamlit as st

from orthography import render_orthography_html
from tts_client import nemo_to_tts_text, synthesize_tts
from translator_core import translate, to_json


TTS_EMOTIONS = [
    "happiness",
    "neutral",
    "sadness",
    "anger",
    "surprise",
    "fear",
    "disgust",
]

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


st.set_page_config(page_title="Nemo 翻译器", layout="centered")

st.title("Nemo 语言翻译器")
st.caption("用于短中文句子的规则翻译演示。")

example = st.selectbox("示例", EXAMPLES, index=0)
text = st.text_input("中文输入", value=example, placeholder="输入一句短中文，例如：主人想吃苹果")

result = translate(text)

st.subheader("Nemo 输出")
st.code(result["nemo"] or " ", language=None)

st.subheader("Nemo 字形输出")
st.markdown(render_orthography_html(result["nemo"]), unsafe_allow_html=True)

st.subheader("语音输出")
default_tts_url = st.secrets.get("TTS_URL", "http://172.16.60.69:7874")
tts_url = st.text_input("TTS 服务器", value=default_tts_url)
tts_default = nemo_to_tts_text(result["nemo"])
if st.session_state.get("last_nemo_output") != tts_default:
    st.session_state["tts_text"] = tts_default
    st.session_state["last_nemo_output"] = tts_default
tts_text = st.text_input("TTS 输入", key="tts_text")
tts_emotion_labels = {
    "happiness": "开心",
    "neutral": "中性",
    "sadness": "难过",
    "anger": "生气",
    "surprise": "惊讶",
    "fear": "害怕",
    "disgust": "厌恶",
}
tts_emotion = st.selectbox("情绪", TTS_EMOTIONS, index=0, format_func=tts_emotion_labels.get)

if st.button("生成语音", disabled=not bool(result["nemo"].strip())):
    try:
        with st.spinner("正在生成语音..."):
            audio = synthesize_tts(
                tts_text,
                base_url=tts_url,
                emotion=tts_emotion,
                temperature=0.5,
            )
        st.audio(audio.wav_bytes, format="audio/wav")
        st.caption(f"{audio.status} 采样率：{audio.sample_rate} Hz")
    except Exception as exc:
        st.error(f"TTS 生成失败：{exc}")

st.subheader("Token list")
st.json(result["tokens"], expanded=True)

st.subheader("Parsed structure")
st.json(result["parsed"], expanded=True)

with st.expander("Raw JSON"):
    st.code(to_json(result), language="json")

st.info("不认识的中文词会自动转成拼音借词。")
