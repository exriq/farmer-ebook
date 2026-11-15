"""Messages: private one-to-one conversations between registered users."""
import streamlit as st
 
import db
 
LABEL = "💬 Messages"
 
 
def messages_page(user):
    st.header("💬 Messages")
    me = user["id"]
    conversations = db.get_conversations(me)
    names = {int(r.id): r.name + (f" ({int(r.unread)} new)" if r.unread else "")
             for r in conversations.itertuples()}
 
    # Someone pressed "Message seller" or "Send a message" on another page
    partner = st.session_state.pop("chat_with", None)
    if partner is not None:
        if partner not in names:
            found = db.get_name(partner)
            if found:
                names[partner] = found
        if partner in names:
            st.session_state["chat_partner"] = partner
 
    if not names:
        st.info("You have no conversations yet. Open the Marketplace or the Farmer "
                "directory and press the message button next to a farmer.")
        return
    if st.session_state.get("chat_partner") not in names:
        st.session_state.pop("chat_partner", None)
    other = st.selectbox("Conversation with", list(names), key="chat_partner",
                         format_func=lambda i: names[i])
 
    db.mark_read(me, other)
    thread = db.get_thread(me, other)
    if thread.empty:
        st.caption("No messages yet. Write the first one below.")
    for r in thread.itertuples():
        with st.chat_message("user" if r.sender_id == me else "assistant"):
            st.write(r.body)
            st.caption(f"{r.created_at:%d %b, %H:%M}")
    st.button("Refresh messages")
 
    text = st.chat_input("Type your message")
    if text and text.strip():
        db.send_message(me, other, text.strip())
        st.rerun()
 
 
PAGES = [
    {"order": 98, "label": LABEL, "func": messages_page,
     "roles": ("farmer", "coordinator", "admin")},
]
