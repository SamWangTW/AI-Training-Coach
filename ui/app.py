"""Streamlit chat interface for the Garmin Training Coach.

Run with:
    streamlit run ui/app.py
"""
import httpx
import streamlit as st

API_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 120.0  # Garmin MCP calls can be slow

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Garmin Training Coach",
    page_icon="🏃",
    layout="centered",
)

st.title("🏃 Garmin Training Coach")
st.caption("Personalized advice powered by your real Garmin data")

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "default"

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")
    user_id = st.text_input("User ID", value=st.session_state.user_id, help="Keeps memory separate per user")
    if user_id != st.session_state.user_id:
        st.session_state.user_id = user_id
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("**Try asking:**")
    examples = [
        "Am I overtraining this week?",
        "Should I run hard tomorrow?",
        "How does this week compare to last?",
        "What are my personal records?",
        "What's my fitness trend over the past month?",
        "My heart rate has been higher than usual — what's going on?",
    ]
    for example in examples:
        if st.button(example, use_container_width=True, key=f"ex_{example[:20]}"):
            st.session_state._pending = example
            st.rerun()

    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # Backend status
    try:
        r = httpx.get(f"{API_URL}/health", timeout=2)
        st.success("Backend connected", icon="✅")
    except Exception:
        st.error("Backend offline — run: `uvicorn api.main:app --reload`", icon="🔴")


# ── Chat history ──────────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ── Send a message (handles both text input and sidebar buttons) ──────────────

def send_message(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with httpx.stream(
                "POST",
                f"{API_URL}/chat/stream",
                json={"message": prompt, "user_id": st.session_state.user_id},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                reply = st.write_stream(resp.iter_text())
        except httpx.ConnectError:
            reply = (
                "Could not reach the backend. Make sure it's running:\n\n"
                "```\nuvicorn api.main:app --reload\n```"
            )
            st.markdown(reply)
        except httpx.HTTPStatusError as e:
            reply = f"Backend error {e.response.status_code}: {e.response.text}"
            st.markdown(reply)
        except Exception as e:
            reply = f"Unexpected error: {e}"
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})


# Handle sidebar button clicks
if "_pending" in st.session_state:
    prompt = st.session_state.pop("_pending")
    send_message(prompt)
    st.rerun()

# Handle chat input
if prompt := st.chat_input("Ask about your training…"):
    send_message(prompt)
