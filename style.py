"""The Farm Book look: colours, motion and small building blocks used by every page."""
import html
 
import streamlit as st
 
PERSON = ('<svg viewBox="0 0 24 24" width="58%" fill="#CFE3D6" aria-hidden="true">'
          '<circle cx="12" cy="8" r="4.2"/><path d="M3.5 21c.8-4.6 4.2-7 8.5-7s7.7 2.4 8.5 7z"/></svg>')
 
CSS = """<style>
:root{--g:#1E6B47;--g9:#11352A;--gold:#C58F1E;--ink:#1B2820;--mu:#64706A;--ln:#DADFD6;--r:#B3352A}
h1,h2,h3{font-family:Georgia,"Times New Roman",serif!important;color:var(--ink)!important;border:0!important}
[data-testid="stHeader"]{background:transparent}
[data-testid="stMainBlockContainer"]{max-width:1100px;padding-top:1.6rem}
/* motion: every element rises in; a new page key replays it */
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"],.element-container{animation:rise .45s ease both}
[data-testid="stElementContainer"]:nth-child(2){animation-delay:.05s}[data-testid="stElementContainer"]:nth-child(3){animation-delay:.1s}
[data-testid="stElementContainer"]:nth-child(4){animation-delay:.15s}[data-testid="stElementContainer"]:nth-child(5){animation-delay:.2s}
[data-testid="stElementContainer"]:nth-child(n+6){animation-delay:.25s}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
/* sidebar */
[data-testid="stSidebar"]{background:var(--g9)}
[data-testid="stSidebar"] *{color:#E4EDE7}
[data-testid="stSidebar"] [role="radiogroup"]{gap:0}
[data-testid="stSidebar"] [data-baseweb="radio"]{padding:.7rem 1rem;margin:0;border-left:4px solid transparent;width:100%;transition:background .2s,padding-left .2s}
[data-testid="stSidebar"] [data-baseweb="radio"]>div:first-child{display:none}
[data-testid="stSidebar"] [data-baseweb="radio"]:hover{background:#0B2820;padding-left:1.35rem}
[data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked){background:#0B2820;border-left-color:var(--gold);font-weight:700}
[data-testid="stSidebar"] .stButton>button{background:transparent;border:1px solid #3B6B58}
.brand{display:flex;gap:12px;align-items:center;padding:.4rem .2rem 1rem}.brand small{opacity:.7}
.av{width:56px;height:56px;border-radius:50%;border:3px solid var(--gold);background:#2A5A47;display:flex;align-items:center;justify-content:center;flex:none;overflow:hidden}
.brand .av{width:44px;height:44px}
.av img{width:100%;height:100%;object-fit:cover}
/* buttons, tabs, panels */
.stButton>button,.stFormSubmitButton>button{border-radius:8px;font-weight:600;transition:transform .15s,box-shadow .15s}
.stButton>button:hover,.stFormSubmitButton>button:hover{transform:translateY(-2px);box-shadow:0 6px 14px rgba(30,107,71,.25)}
.stTabs [aria-selected="true"]{color:var(--g)!important}.stTabs [data-baseweb="tab-highlight"]{background:var(--gold)!important}
[data-testid="stVerticalBlockBorderWrapper"],[data-testid="stExpander"]{background:#fff;border-radius:10px;border-color:var(--ln)}
input,textarea,[data-baseweb="select"]>div{border-radius:8px!important}
/* page header, cards, chat bubbles */
.hd{display:flex;align-items:center;gap:14px;margin-bottom:1rem}.hd h1{margin:0;font-size:2rem}.hd .sub{color:var(--mu)}
.kpi{background:#fff;border:1px solid var(--ln);border-top:4px solid var(--g);border-radius:10px;padding:13px 15px;transition:transform .2s,box-shadow .2s}
.kpi:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(17,53,42,.14)}
.kpi b{display:block;font:700 27px Georgia,serif;margin:2px 0}.kpi small{display:block;color:var(--mu)}
.kpi.neg{border-top-color:var(--r)}.kpi.neg b{color:var(--r)}
.tag{display:inline-block;font-size:12.5px;padding:1px 9px;border-radius:99px;background:#F4E6C3;color:#6B4A07;font-weight:600}
.msg{max-width:75%;padding:9px 13px;border-radius:14px;margin:6px 0;line-height:1.4;animation:rise .25s ease both}
.msg small{display:block;opacity:.7;font-size:12px;text-align:right}
.me{margin-left:auto;background:var(--g);color:#fff;border-bottom-right-radius:4px}
.them{background:#fff;border:1px solid var(--ln);border-bottom-left-radius:4px}
</style>"""
 
 
def apply():
    st.markdown(CSS, unsafe_allow_html=True)
 
 
def avatar():
    photo = st.session_state.get("photo")
    inner = f'<img src="{photo}" alt="My photo">' if photo else PERSON
    return f'<div class="av">{inner}</div>'
 
 
def header(title, sub=""):
    st.markdown(f'<div class="hd">{avatar()}<div><h1>{html.escape(title)}</h1>'
                f'<div class="sub">{html.escape(sub)}</div></div></div>', unsafe_allow_html=True)
 
 
def kpi_row(items):
    """items: (label, value, small text, is_negative)"""
    for col, (label, value, sub, neg) in zip(st.columns(len(items)), items):
        col.markdown(f'<div class="kpi{" neg" if neg else ""}"><small>{label}</small>'
                     f'<b>{value}</b><small>{sub}</small></div>', unsafe_allow_html=True)
 
 
def kes(n):
    return f"KES {n:,.0f}"
