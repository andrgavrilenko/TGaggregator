import requests
import streamlit as st

from tgaggerator.config import settings

st.set_page_config(page_title="tgaggerator", layout="wide")
st.title("tgaggerator: Unified Telegram Feed")

api_base = settings.ui_api_base.rstrip("/")


def _api_get(path: str, *, timeout: int = 12):
    resp = requests.get(f"{api_base}{path}", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _api_post(path: str, payload: dict | None = None, *, timeout: int = 120):
    resp = requests.post(f"{api_base}{path}", json=payload or {}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _api_try_get(path: str, *, timeout: int = 8):
    try:
        return _api_get(path, timeout=timeout), None
    except Exception as exc:
        return None, str(exc)


def _http_error_text(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            return exc.response.text
        except Exception:
            return str(exc)
    return str(exc)


def _set_ops_ok(label: str, payload: dict):
    st.session_state["ops_message"] = f"{label}: OK"
    st.session_state["ops_payload"] = payload


def _set_ops_err(label: str, exc: Exception):
    st.session_state["ops_error"] = f"{label}: {_http_error_text(exc)}"


def _run_start_pipeline(bootstrap_limit: int):
    data = _api_post(
        "/ops/start",
        {"bootstrap_limit": bootstrap_limit, "run_ingest_once": True},
        timeout=600,
    )
    _set_ops_ok("Пуск", data)


channels_data, channels_err = _api_try_get("/channels")
status_data, status_err = _api_try_get("/status")
ops_data, ops_err = _api_try_get("/ops/status")

channel_options: list[dict] = channels_data or []

with st.sidebar:
    st.subheader("Quick Start")

    if "ops_error" in st.session_state:
        st.error(st.session_state.pop("ops_error"))
    if "ops_message" in st.session_state:
        st.success(st.session_state.pop("ops_message"))
    if "ops_payload" in st.session_state:
        with st.expander("Operation result", expanded=False):
            st.json(st.session_state.pop("ops_payload"))

    if ops_err:
        st.error(f"Ops API error: {ops_err}")
    else:
        env = ops_data.get("env", {})
        st.caption(
            f"TG API: {'OK' if env.get('tg_api_configured') else 'MISSING'} | "
            f"Authorized: {'YES' if ops_data.get('tg_authorized') else 'NO'} | "
            f"Public cfg: {env.get('public_channels_configured', 0)}"
        )

    public_handle = st.text_input("Public channel (@username)", value="", key="ops_public_handle")
    if st.button("Add public channel", use_container_width=True):
        try:
            payload = _api_post("/ops/public/add", {"handle": public_handle.strip()}, timeout=45)
            _set_ops_ok("Add public channel", payload)
            st.rerun()
        except Exception as exc:
            _set_ops_err("Add public channel", exc)
            st.rerun()

    bootstrap_limit = st.number_input("Bootstrap limit/ch", min_value=20, max_value=2000, value=200, step=20)
    auto_start = st.checkbox("Auto-start on page load", value=False)

    if st.button("Пуск", use_container_width=True, type="primary"):
        try:
            _run_start_pipeline(int(bootstrap_limit))
            st.rerun()
        except Exception as exc:
            _set_ops_err("Пуск", exc)
            st.rerun()

    if auto_start and not st.session_state.get("auto_started", False):
        try:
            _run_start_pipeline(int(bootstrap_limit))
            st.session_state["auto_started"] = True
            st.rerun()
        except Exception as exc:
            _set_ops_err("Auto-start", exc)
            st.session_state["auto_started"] = True
            st.rerun()

    if ops_data and not ops_data.get("tg_authorized", False):
        st.markdown("---")
        st.caption("Optional one-time Telegram login (only needed for private channels):")
        phone_default = settings.tg_phone or ""
        phone = st.text_input("Phone (+7...)", value=phone_default, key="ops_phone")
        if st.button("Send Telegram code", use_container_width=True):
            try:
                data = _api_post("/ops/login/request-code", {"phone": phone}, timeout=30)
                _set_ops_ok("Send code", data)
                st.rerun()
            except Exception as exc:
                _set_ops_err("Send code", exc)
                st.rerun()

        code = st.text_input("Telegram code", value="", key="ops_code")
        password = st.text_input("2FA password (optional)", value="", type="password", key="ops_pwd")
        if st.button("Confirm login", use_container_width=True):
            payload = {"phone": phone, "code": code.strip(), "password": password or None}
            try:
                data = _api_post("/ops/login/confirm", payload, timeout=30)
                _set_ops_ok("Confirm login", data)
                st.rerun()
            except Exception as exc:
                _set_ops_err("Confirm login", exc)
                st.rerun()

    st.markdown("---")
    st.subheader("Filters")
    q = st.text_input("Search text", value="")
    only_media = st.checkbox("Only media", value=False)
    limit = st.slider("Items", min_value=20, max_value=300, value=100, step=20)
    offset = st.number_input("Offset", min_value=0, value=0, step=20)

    channel_map = {f"{c['title']} ({c['id']})": c["id"] for c in channel_options}
    selected_labels = st.multiselect("Channels", options=list(channel_map.keys()))
    selected_ids = [channel_map[label] for label in selected_labels]

if status_err:
    st.error(f"Failed to load API data: {status_err}")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Channels", status_data.get("total_channels", 0))
col2.metric("Enabled", status_data.get("enabled_channels", 0))
col3.metric("Messages", status_data.get("total_messages", 0))

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
    resp = requests.get(f"{api_base}/feed", params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json()
except Exception as exc:
    st.error(f"Failed to load feed: {exc}")
    st.stop()

st.caption(f"Loaded {len(items)} items")
for item in items:
    header = f"{item['date_utc']} | {item['channel_title']} | #{item['tg_message_id']}"
    text = item.get("text") or "(no text)"

    st.markdown(f"**{header}**")
    if item.get("media_type"):
        st.caption(f"Media: {item['media_type']}")
    st.write(text)
    if item.get("link"):
        st.markdown(f"[Open message]({item['link']})")
    st.divider()
