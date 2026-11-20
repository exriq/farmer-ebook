"""Messages: private conversations that update by themselves (no refresh button needed)."""
import html
 
import streamlit as st
 
import db
 
LABEL = "💬 Messages"
ROLE_TAG = {"farmer": "Farmer", "coordinator": "Coordinator", "agrovet": "Agrovet", "admin": "Admin"}
 
 
def unread_count(me):
    return int(db.rows("SELECT COUNT(*) FROM messages WHERE recipient_id = %s AND NOT is_read",
                       (me,))[0][0])
 
 
def _open(pid, name):
    st.session_state.setdefault("chat_extra", {})[pid] = name
    st.session_state["chat_partner"] = pid
 
 
@st.fragment(run_every=4)
def _thread(me, other):
    """Re-reads the conversation every 4 seconds, so new replies appear on their own."""
    db.mark_read(me, other)
    t = db.table("""SELECT sender_id, body, created_at, is_read FROM messages
                    WHERE (sender_id = %(me)s AND recipient_id = %(o)s)
                       OR (sender_id = %(o)s AND recipient_id = %(me)s)
                    ORDER BY created_at DESC, id DESC LIMIT 60""", {"me": me, "o": other})
    if t.empty:
        st.caption("No messages yet. Write the first one below.")
    for r in t.iloc[::-1].itertuples():
        mine = int(r.sender_id) == me
        seen = " ✓✓" if mine and r.is_read else (" ✓" if mine else "")
        body = html.escape(r.body).replace("\n", "<br>")
        st.markdown(f'<div class="msg {"me" if mine else "them"}">{body}'
                    f'<small>{r.created_at:%d %b, %H:%M}{seen}</small></div>',
                    unsafe_allow_html=True)
 
 
def messages_page(user):
    st.header("💬 Messages")
    me = int(user["id"])
    conv = db.get_conversations(me)
    names = {int(r.id): r.name + (f"  ·  {int(r.unread)} new" if r.unread else "")
             for r in conv.itertuples()}
    names.update(st.session_state.get("chat_extra", {}))
    partner = st.session_state.pop("chat_with", None)      # set by Marketplace / Directory
    if partner is not None:
        _open(int(partner), db.get_name(int(partner)) or "User")
        names.update(st.session_state["chat_extra"])
 
    with st.expander("➕ Start a new conversation", expanded=not names):
        q = st.text_input("Search by name", key="chat_search")
        if q.strip():
            found = db.table("""SELECT id, name, role, sub_county FROM farmers
                WHERE id <> %(me)s AND active AND name ILIKE %(q)s
                  AND (in_directory OR role IN ('coordinator', 'agrovet', 'admin'))
                ORDER BY name LIMIT 12""", {"me": me, "q": f"%{q.strip()}%"})
            if found.empty:
                st.caption("Nobody found with that name.")
            for r in found.itertuples():
                a, b = st.columns([4, 1])
                a.write(f"**{r.name}**  ·  {ROLE_TAG.get(r.role, r.role)}  ·  {r.sub_county or ''}")
                b.button("Message", key=f"new_{r.id}", on_click=_open, args=(int(r.id), r.name))
    if not names:
        return
    if st.session_state.get("chat_partner") not in names:
        st.session_state["chat_partner"] = next(iter(names))
    other = st.selectbox("Conversation with", list(names), key="chat_partner",
                         format_func=lambda i: names[i])
    _thread(me, int(other))
    text = st.chat_input("Type your message")
    if text and text.strip():
        db.send_message(me, int(other), text.strip())
        st.rerun()
 
 
PAGES = [{"order": 98, "label": LABEL, "func": messages_page,
          "roles": ("farmer", "coordinator", "agrovet", "admin")}]
