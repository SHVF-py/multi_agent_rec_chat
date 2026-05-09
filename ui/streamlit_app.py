import streamlit as st
import httpx
from typing import Dict, Any

# Config
API_URL = "http://localhost:8080"
TENANT_ID = "default"

# No ngrok headers needed for local requests — header is harmless but not required.
_NGROK_HEADERS: dict = {}

# ---------------------------------------------------------------------------
# Helper functions must be defined BEFORE they are referenced in the UI loop
# ---------------------------------------------------------------------------

def display_products(products):
    """Display ranked products."""
    for product in products[:3]:  # Top 3
        meta = product['metadata']
        col1, col2, col3 = st.columns([1, 3, 1])

        with col1:
            image_url = meta.get('image', '')
            if image_url:
                st.image(image_url, width=90)
            else:
                st.markdown(f"### #{product['rank']}")

        with col2:
            st.markdown(f"**#{product['rank']} — {meta.get('name', product['product_id'])}**")
            rating = meta.get('rating', 0)
            stars = '⭐' * round(rating) if rating else ''
            st.caption(f"{stars} {rating}/5  ·  Category: {meta.get('category', 'N/A')}")

            with st.expander("Scoring details"):
                breakdown = product['scoring']
                st.write(f"- Relevance: {breakdown['relevance_score']:.2f}")
                st.write(f"- Constraints: {breakdown['constraint_match_score']:.2f}")
                st.write(f"- Rating: {breakdown['rating_score']:.2f}")

        with col3:
            price = meta.get('price', 'N/A')
            st.metric("Price", f"${price}")

        st.divider()


def display_comparison(comparison):
    """Display comparison table."""
    import pandas as pd
    table = comparison["comparison_table"]
    df = pd.DataFrame(table["rows"])
    st.dataframe(df, use_container_width=True)
    st.caption(comparison["narrative_summary"])


def display_cross_sell(items):
    """Display cross-sell items."""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            st.markdown(f"**{item['product_id']}**")
            st.caption(f"Confidence: {item['confidence']:.0%}")


def _extract_text_history(messages: list) -> list:
    """
    Convert Streamlit message history into the text-only format expected by the API.
    Extracts role + content for user messages and role + text for assistant messages.
    Returns the last 10 entries (5 turns) to keep token usage reasonable.
    """
    history = []
    for msg in messages:
        if msg["role"] == "user":
            history.append({"role": "user", "content": msg.get("content", "")})
        elif msg["role"] == "assistant" and msg.get("text"):
            history.append({"role": "assistant", "content": msg["text"]})
    return history[-10:]


def query_api(query_text: str, chat_history: list = None) -> Dict[str, Any]:
    """
    Call Quiribot API synchronously.
    Uses httpx.Client (synchronous) to avoid asyncio conflicts with Streamlit.
    """
    # connect_timeout: time to establish TCP connection (5s is plenty for localhost)
    # read_timeout: time to wait for the server to send a response byte.
    #   phi3 on CPU can take 60-180s to produce the first token, so use 360s.
    _timeout = httpx.Timeout(connect=5.0, read=360.0, write=30.0, pool=5.0)
    try:
        with httpx.Client(timeout=_timeout) as client:
            response = client.post(
                f"{API_URL}/query",
                headers=_NGROK_HEADERS,
                json={
                    "query_text": query_text,
                    "session_id": st.session_state.session_id,
                    "tenant_id": TENANT_ID,
                    "chat_history": chat_history or [],
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        st.error("Cannot reach backend — make sure gateway (port 9000) and API (port 8080) are running.")
        return {"errors": ["Backend not reachable"]}
    except httpx.ReadTimeout:
        st.error("The request timed out waiting for the LLM. phi3 on CPU is slow — try a shorter query or wait longer.")
        return {"errors": ["LLM response timed out"]}
    except httpx.HTTPError as e:
        st.error(f"API Error: {e}")
        return {"errors": [str(e)]}


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Quiribot",
    page_icon="🛒",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# Sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    debug_mode = st.toggle("Debug Mode", value=False)
    st.markdown("---")
    if st.button("🗑️ New Chat"):
        st.session_state.messages = []
        import uuid as _uuid
        st.session_state.session_id = str(_uuid.uuid4())
        st.rerun()
    st.markdown("---")
    st.caption(f"Session: {st.session_state.session_id[:8]}")

# Main UI
st.title("🛒 Quiribot")
st.caption("Multi-Agent E-Commerce Assistant")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
            if "text" in message:
                st.write(message["text"])
            if "products" in message:
                display_products(message["products"])
            if "comparison" in message:
                display_comparison(message["comparison"])
            if "cross_sell" in message:
                display_cross_sell(message["cross_sell"])
# Chat input
if prompt := st.chat_input("Ask me anything about products..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Build text-only history from all turns BEFORE the current prompt
            prior_history = _extract_text_history(st.session_state.messages[:-1])
            response = query_api(prompt, prior_history)

        assistant_message = {"role": "assistant"}

        if response.get("errors") and not response.get("ranked_products"):
            st.warning(response["errors"][0])
            assistant_message["text"] = response["errors"][0]
        else:
            # Always show the natural language reply first (ChatGPT-style)
            chat_reply = response.get("conversational_reply", "")
            if chat_reply:
                st.write(chat_reply)
                assistant_message["text"] = chat_reply

            # Then show products if any
            if response.get("ranked_products"):
                products = response["ranked_products"]
                display_products(products)
                assistant_message["products"] = products

            # Comparison table
            if response.get("comparison"):
                with st.expander("📊 Product Comparison"):
                    display_comparison(response["comparison"])
                assistant_message["comparison"] = response["comparison"]

            # Cross-sell
            if response.get("cross_sell") and response["cross_sell"]["cross_sell_items"]:
                st.divider()
                st.subheader("🔗 Frequently Bought Together")
                display_cross_sell(response["cross_sell"]["cross_sell_items"])
                assistant_message["cross_sell"] = response["cross_sell"]["cross_sell_items"]

            # If truly nothing came back
            if not chat_reply and not response.get("ranked_products"):
                msg = "I couldn't find anything for that. Try rephrasing or ask for a specific product!"
                st.write(msg)
                assistant_message["text"] = msg

        if debug_mode:
            with st.expander("🐛 Debug Info"):
                st.json(response)

        st.session_state.messages.append(assistant_message)

if __name__ == "__main__":
    pass

