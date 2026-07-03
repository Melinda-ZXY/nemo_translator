import streamlit as st

from dysarthria_core import convert_text
from tts_client import synthesize_tts


TTS_URL = "https://opinions-society-mining-dramatically.trycloudflare.com/"
TTS_EMOTIONS = [
    "happiness",
    "neutral",
    "sadness",
    "anger",
    "surprise",
    "fear",
    "disgust",
]
EMOTION_LABELS = {
    "happiness": "开心",
    "neutral": "中性",
    "sadness": "难过",
    "anger": "生气",
    "surprise": "惊讶",
    "fear": "害怕",
    "disgust": "厌恶",
}
EXAMPLES = [
    "你好",
    "老师知道这是谁的水杯",
    "哥哥可以给我一个杯子",
    "小狗喜欢睡觉",
]


st.set_page_config(page_title="构音障碍语音转换", layout="centered")

st.title("构音障碍语音转换")
st.caption("中文输入会先转成拼音，再套用构音障碍音变规则。")

example = st.selectbox("示例", EXAMPLES, index=0)
text = st.text_area("中文输入", value=example, height=110, placeholder="输入中文，例如：老师知道这是谁的水杯")

converted = convert_text(text)

st.subheader("转换后拼音")
st.code(converted["converted_pinyin"] or " ", language=None)

st.subheader("TTS 输入")
if st.session_state.get("last_dysarthria_input") != converted["tts_input"]:
    st.session_state["dysarthria_tts_text"] = converted["tts_input"]
    st.session_state["last_dysarthria_input"] = converted["tts_input"]
tts_text = st.text_input("构音障碍 TTS 输入", key="dysarthria_tts_text")

st.subheader("语音输出")
tts_url = st.text_input("TTS 服务器", value=st.secrets.get("DYSARTHRIA_TTS_URL", TTS_URL))
emotion = st.selectbox("情绪", TTS_EMOTIONS, index=0, format_func=EMOTION_LABELS.get)
speed = st.slider("语速", min_value=0.5, max_value=1.8, value=1.0, step=0.05)

if st.button("生成语音", disabled=not bool(tts_text.strip())):
    try:
        with st.spinner("正在生成语音..."):
            audio = synthesize_tts(
                tts_text,
                base_url=tts_url,
                emotion=emotion,
                temperature=0.5,
                playback_speed=speed,
            )
        st.audio(audio.wav_bytes, format="audio/wav")
        st.caption(f"{audio.status} 语速：{speed:.2f}x")
    except Exception as exc:
        st.error(f"TTS 生成失败：{exc}")

with st.expander("音节转换"):
    st.dataframe(converted["syllables"], hide_index=True, use_container_width=True)
