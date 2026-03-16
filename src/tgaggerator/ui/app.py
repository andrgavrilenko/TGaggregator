import requests
import streamlit as st

from tgaggerator.config import settings

st.set_page_config(page_title="tgaggerator", layout="wide")
st.title("tgaggerator: Unified Telegram Feed")

api_base = settings.ui_api_base.rstrip("/")

channel_options: list[dict] = []
try:
    channels_resp = requests.get(f"{api_base}/channels", timeout=8)
    channels_resp.raise_for_status()
    channel_options = channels_resp.json()
except Exception:
    channel_options = []

with st.sidebar:
    st.subheader("Filters")
    q = st.text_input("Search text", value="")
    only_media = st.checkbox("Only media", value=False)
    limit = st.slider("Items", min_value=20, max_value=300, value=100, step=20)
    offset = st.number_input("Offset", min_value=0, value=0, step=20)

    channel_map = {f"{c['title']} ({c['id']})": c["id"] for c in channel_options}
    selected_labels = st.multiselect("Channels", options=list(channel_map.keys()))
    selected_ids = [channel_map[label] for label in selected_labels]

params = {
    "q": q or None,
    "only_media": str(only_media).lower(),
    "limit": limit,
    "offset": offset,
}
params = {k: v for k, v in params.items() if v is not None}

for cid in selected_ids:
    params.setdefault("channel_ids", []).append(cid)

try:
    status_resp = requests.get(f"{api_base}/status", timeout=8)
    status_resp.raise_for_status()
    status_data = status_resp.json()

    col1, col2, col3 = st.columns(3)
    col1.metric("Channels", status_data.get("total_channels", 0))
    col2.metric("Enabled", status_data.get("enabled_channels", 0))
    col3.metric("Messages", status_data.get("total_messages", 0))

    resp = requests.get(f"{api_base}/feed", params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json()

    st.caption(f"Loaded {len(items)} items")
    for item in items:
        header = f"{item['date_utc']} | {item['channel_title']} | #{item['tg_message_id']}"
        with st.expander(header, expanded=False):
            if item.get("media_type"):
                st.write(f"Media: {item['media_type']}")
            st.write(item.get("text") or "(no text)")
            if item.get("link"):
                st.markdown(f"[Open message]({item['link']})")
except Exception as exc:
    st.error(f"Failed to load API data: {exc}")
