import streamlit as st

from tts_client import synthesize_tts
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


st.set_page_config(page_title="Nemo Translator", layout="centered")

st.title("Nemo Language Demo Translator")
st.caption("A deterministic rule-based demo for short Chinese sentences.")

example = st.selectbox("Examples", EXAMPLES, index=0)
text = st.text_input("Chinese input", value=example, placeholder="输入一句短中文，例如：主人想吃苹果")

result = translate(text)

st.subheader("Nemo output")
st.code(result["nemo"] or " ", language=None)

st.subheader("TTS output")
default_tts_url = st.secrets.get("TTS_URL", "http://172.16.60.69:7874")
tts_url = st.text_input("TTS server", value=default_tts_url)
if st.session_state.get("last_nemo_output") != result["nemo"]:
    st.session_state["tts_text"] = result["nemo"]
    st.session_state["last_nemo_output"] = result["nemo"]
tts_text = st.text_input("TTS input", key="tts_text")
tts_emotion = st.selectbox("Emotion", TTS_EMOTIONS, index=0)

if st.button("Generate TTS audio", disabled=not bool(result["nemo"].strip())):
    try:
        with st.spinner("Generating audio..."):
            audio = synthesize_tts(
                tts_text,
                base_url=tts_url,
                emotion=tts_emotion,
                temperature=0.5,
            )
        st.audio(audio.wav_bytes, format="audio/wav")
        st.caption(f"{audio.status} Sample rate: {audio.sample_rate} Hz")
    except Exception as exc:
        st.error(f"TTS failed: {exc}")

st.subheader("Token list")
st.json(result["tokens"], expanded=True)

st.subheader("Parsed structure")
st.json(result["parsed"], expanded=True)

with st.expander("Raw JSON"):
    st.code(to_json(result), language="json")

st.info("Unknown Chinese words are converted into pinyin loanwords automatically.")
