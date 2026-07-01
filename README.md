# Nemo Language Demo Translator

A small deterministic Streamlit demo that translates short Chinese sentences into Nemo-style output using a lexicon, pinyin loanwords, and simple word-order rules.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

The translator is rule-based and does not use an LLM.

## Deploy

This app is ready for Streamlit Community Cloud:

1. Push this folder to a public GitHub repository.
2. In Streamlit Community Cloud, create a new app from that repository.
3. Set the app entry point to `app.py`.

Notes:
- `我`, `尼莫`, and `Nemo` are treated as Nemo.
- Long vowels use colon notation, such as `Mi:` and `Nu:`.
