"""UkulimaKonect - main file (Farm Book design, three levels of access).
 
Replace your old app.py with this one. Page files are still found by themselves."""
 
import html
import importlib
import importlib.util
 
import streamlit as st
 
import chat
import config
import db
import extras
import style
 
st.set_page_config(page_title=config.APP_NAME, page_icon="🌾", layout="wide")
style.apply()
 
# The role 'agrovet' is added here, so config.py does not have to change.
if "agrovet" not in config.ROLES:
    config.ROLES.insert(max(len(config.ROLES) - 1, 0), "agrovet")
 
try:
    db.init_db()
    db.run("ALTER TABLE farmers ADD COLUMN IF NOT EXISTS requested_role TEXT")
    extras.setup()
except Exception as error:
    print("DATABASE ERROR:", repr(error))
    st.error("The database cannot be reached right now. Please try again in a minute.")
    st.stop()
 
st.session_state.setdefault("user", None)
 
MODULES = ["home", "records", "farm_profile", "inputs_labour", "dashboard",
           "market_info", "staff", "marketplace", "agrovet", "chat"]
AGROVET_PAGES = ("Overview", "Market prices", "Input prices", "Marketplace",
                 "Farmer directory", "Messages", "My Shop", "Demand near me", "My Profile")
ROLE_LABEL = {"farmer": "Farmer", "coordinator": "Sub-county coordinator",
              "agrovet": "Agrovet", "admin": "Administrator"}
ROLE_INFO = {
    "farmer": ("Farmer", "Keep your farm records, see prices and trade with other farmers."),
    "agrovet": ("Agrovet", "Sell farm inputs, share prices and answer farmers. "
                "The administrator approves agrovet accounts."),
    "coordinator": ("Sub-county coordinator", "Support the farmers in your sub-county. "
                    "The administrator approves coordinator accounts."),
}
 
 
def load_pages():
    importlib.invalidate_caches()
    pages = []
    for name in MODULES:
        if importlib.util.find_spec(name) is not None:
            pages.extend(getattr(importlib.import_module(name), "PAGES", []))
    return sorted(pages, key=lambda p: p["order"])
 
 
def allowed(page, user):
    label = page["label"]
    if user.get("pending"):                      # waiting for approval
        return any(k in label for k in ("Overview", "Messages"))
    if user["role"] == "agrovet":
        return any(k in label for k in AGROVET_PAGES)
    if user["role"] not in page["roles"]:
        return False
    types = page.get("types")
    if types and user["role"] == "farmer" and user["farming_type"] not in types:
        return False
    return True
 
 
# ---------- LOG IN / REGISTER ----------
def login_page():
    style.header(config.APP_NAME, "Farm records, prices and trade for Homa Bay County")
    tab_login, tab_register = st.tabs(["Log in", "Register"])
    with tab_login:
        with st.form("login_form"):
            phone = st.text_input("Phone number", placeholder="07XXXXXXXX")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary"):
                user = db.check_login(config.normalize_phone(phone) or phone, password)
                if not user:
                    st.error("Wrong phone number or password.")
                elif not user["active"]:
                    st.error("This account has been switched off. Please contact your "
                             "sub-county coordinator.")
                else:
                    st.session_state.user = user
                    st.rerun()
    with tab_register:
        register_form()
 
 
def register_form():
    role = st.radio("I am registering as", list(ROLE_INFO), horizontal=True,
                    format_func=lambda r: ROLE_INFO[r][0], key="reg_role")
    st.info(ROLE_INFO[role][1])
    st.subheader("About you")
    name = st.text_input("Business name" if role == "agrovet" else "Full name", key="reg_name")
    gender = st.selectbox("Gender", config.GENDERS, key="reg_gender")
    phone = st.text_input("Phone number (used to log in)", placeholder="07XXXXXXXX",
                          key="reg_phone")
    sub_county = st.selectbox("Sub-county", config.SUB_COUNTIES, key="reg_sc")
    ward = st.text_input("Ward", key="reg_ward")
    village = st.text_input("Village or town", key="reg_village")
    farming_type = "Crops"
    if role == "farmer":
        st.subheader("Your farming")
        farming_type = st.selectbox(
            "What kind of farming do you do?", config.FARMING_TYPES, key="reg_ft",
            format_func=lambda t: f"{t} - {config.FARMING_TYPE_HELP[t]}")
    with st.expander("Location (optional)"):
        st.caption("Stand at the place, open Google Maps, touch the blue dot, and copy the "
                   "two numbers shown. You can also add this later.")
        lat_text = st.text_input("Latitude", placeholder="-0.5273", key="reg_lat")
        lon_text = st.text_input("Longitude", placeholder="34.4571", key="reg_lon")
    st.subheader("Privacy")
    in_directory = st.checkbox("Let other registered users find me in the directory and "
                               "message me", value=True, key="reg_dir")
    share_contact = st.checkbox("Show my phone number on my marketplace posts",
                                value=False, key="reg_share")
    st.subheader("Password")
    password = st.text_input("Choose a password (8 or more characters)", type="password",
                             key="reg_pw")
    password2 = st.text_input("Type the password again", type="password", key="reg_pw2")
    consent = st.checkbox("I agree that UkulimaKonect may store my details and records to "
                          "support farmers in Homa Bay County. I understand that the platform "
                          "administrators can see my records, and that my sub-county "
                          "coordinator can see my profile details.", key="reg_consent")
    if not st.button("Create account", type="primary", key="reg_go"):
        return
    clean_phone = config.normalize_phone(phone)
    lat, lat_error = config.parse_coordinate(lat_text, *config.LAT_RANGE, "Latitude")
    lon, lon_error = config.parse_coordinate(lon_text, *config.LON_RANGE, "Longitude")
    problem = None
    if not name.strip() or not ward.strip() or not village.strip():
        problem = "Please fill in your name, ward and village."
    elif not clean_phone:
        problem = "Enter a Kenyan mobile number such as 0712345678."
    elif lat_error or lon_error:
        problem = lat_error or lon_error
    elif (lat is None) != (lon is None):
        problem = "Fill in both latitude and longitude, or leave both empty."
    elif len(password) < 8:
        problem = "The password must have 8 or more characters."
    elif password != password2:
        problem = "The two passwords do not match."
    elif not consent:
        problem = "Please tick the box to agree before creating your account."
    if problem:
        st.error(problem)
        return
    info = {"name": name.strip(), "phone": clean_phone, "gender": gender,
            "sub_county": sub_county, "ward": ward.strip(), "village": village.strip(),
            "farming_type": farming_type, "latitude": lat, "longitude": lon,
            "share_contact": share_contact, "in_directory": in_directory}
    if not db.create_farmer(info, password):
        st.error("That phone number is already registered. Use the Log in tab.")
        return
    if role != "farmer":    # access above farmer is only given by the administrator
        db.run("UPDATE farmers SET requested_role = %s WHERE phone = %s", (role, clean_phone))
    st.session_state.user = db.check_login(clean_phone, password)
    st.rerun()
 
 
@st.fragment(run_every=10)
def unread_notice(uid):
    n = chat.unread_count(uid)
    if n:
        st.markdown(f'<span class="tag">💬 {n} new message{"s" if n > 1 else ""}</span>',
                    unsafe_allow_html=True)
 
 
# ---------- MAIN ----------
user = st.session_state.user
if user is None:
    login_page()
    st.stop()
 
fresh = db.rows("SELECT role, requested_role, sub_county, active, photo FROM farmers WHERE id = %s",
                (user["id"],))
if not fresh or not fresh[0][3]:                 # removed or switched off
    st.session_state.clear()
    st.rerun()
user = {**user, "role": fresh[0][0], "sub_county": fresh[0][2]}   # approvals show at once
st.session_state["photo"] = fresh[0][4]
if user["role"] == "farmer" and fresh[0][1] in ("coordinator", "agrovet"):
    user["pending"] = fresh[0][1]
 
pages = [p for p in load_pages() if allowed(p, user)]
labels = [p["label"] for p in pages]
if st.session_state.get("menu_choice") not in labels:
    st.session_state.pop("menu_choice", None)
 
with st.sidebar:
    where = f" · {user['sub_county']}" if user["role"] in ("coordinator", "agrovet") else ""
    st.markdown(f'<div class="brand">{style.avatar()}<div><b>{html.escape(user["name"])}</b>'
                f'<br><small>{ROLE_LABEL.get(user["role"], user["role"])}{where}</small>'
                f'</div></div>', unsafe_allow_html=True)
    choice = st.radio("Menu", labels, key="menu_choice", label_visibility="collapsed")
    unread_notice(user["id"])
    if st.button("📷 Change photo"):
        extras.photo_dialog(user["id"])
    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()
 
page = pages[labels.index(choice)]
with st.container(key=f"page_{labels.index(choice)}"):    # a new key replays the page animation
    try:
        page["func"](user)
    except Exception as error:
        print("PAGE ERROR:", page["label"], repr(error))
        st.error("Something went wrong on this page. Please try again.")
        if user["role"] == "admin":
            st.exception(error)
