"""UkulimaKonect - main file. You paste this ONCE (Phase 1) and never change it.
Each phase adds new files, and this file finds them by itself."""
import importlib
import importlib.util
 
import streamlit as st
 
import config
import db
 
st.set_page_config(page_title=config.APP_NAME, page_icon="🌾", layout="wide")
 
st.markdown("""
<style>
[data-testid="stSidebar"] {background-color: #E6F0D8;}
h1, h2, h3 {color: #5A3E2B;}
h1 {border-bottom: 3px solid #D4A017; padding-bottom: 0.2rem;}
[data-testid="stMetric"] {background: #F6F9EF; border-left: 5px solid #D4A017;
    padding: 0.6rem 0.8rem; border-radius: 6px;}
</style>
""", unsafe_allow_html=True)
 
try:
    db.init_db()
except Exception as error:
    print("DATABASE ERROR:", repr(error))
    st.error("The database cannot be reached right now. Please try again in a minute.")
    st.stop()
 
st.session_state.setdefault("user", None)
 
# Page files, in the order they are looked for. Missing files are skipped.
MODULES = ["records", "farm_profile", "inputs_labour", "dashboard",
           "market_info", "staff", "marketplace", "chat"]
 
 
def load_pages():
    importlib.invalidate_caches()
    pages = []
    for name in MODULES:
        if importlib.util.find_spec(name) is not None:
            module = importlib.import_module(name)
            pages.extend(getattr(module, "PAGES", []))
    return sorted(pages, key=lambda p: p["order"])
 
 
def allowed(page, user):
    if user["role"] not in page["roles"]:
        return False
    types = page.get("types")
    if types and user["role"] == "farmer" and user["farming_type"] not in types:
        return False
    return True
 
 
# ---------- LOG IN / REGISTER ----------
def login_page():
    st.title("🌾 " + config.APP_NAME)
    st.caption("Farm records, market prices and farmer-to-farmer trade for Homa Bay County")
    tab_login, tab_register = st.tabs(["Log in", "Register"])
 
    with tab_login:
        with st.form("login_form"):
            phone = st.text_input("Phone number", placeholder="07XXXXXXXX")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
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
    with st.form("register_form"):
        st.subheader("About you")
        name = st.text_input("Full name")
        gender = st.selectbox("Gender", config.GENDERS)
        phone = st.text_input("Phone number (used to log in)", placeholder="07XXXXXXXX")
        sub_county = st.selectbox("Sub-county", config.SUB_COUNTIES)
        ward = st.text_input("Ward")
        village = st.text_input("Village")
        st.subheader("Your farming")
        farming_type = st.selectbox(
            "What kind of farming do you do?", config.FARMING_TYPES,
            format_func=lambda t: f"{t} - {config.FARMING_TYPE_HELP[t]}")
        with st.expander("Farm location (optional)"):
            st.caption("Stand at your farm, open Google Maps, touch the blue dot, and "
                       "copy the two numbers shown. You can also add this later.")
            lat_text = st.text_input("Latitude", placeholder="-0.5273")
            lon_text = st.text_input("Longitude", placeholder="34.4571")
        st.subheader("Privacy")
        in_directory = st.checkbox(
            "Let other registered farmers find me in the farmer directory and message me",
            value=True)
        share_contact = st.checkbox(
            "Show my phone number on my marketplace posts", value=False)
        st.subheader("Password")
        password = st.text_input("Choose a password (8 or more characters)",
                                 type="password")
        password2 = st.text_input("Type the password again", type="password")
        consent = st.checkbox(
            "I agree that UkulimaKonect may store my details and farm records to "
            "support farmers in Homa Bay County. I understand that the platform "
            "administrators can see my records, and that my sub-county coordinator "
            "can see my profile details.")
 
        if st.form_submit_button("Create account"):
            clean_phone = config.normalize_phone(phone)
            lat, lat_error = config.parse_coordinate(
                lat_text, *config.LAT_RANGE, "Latitude")
            lon, lon_error = config.parse_coordinate(
                lon_text, *config.LON_RANGE, "Longitude")
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
                    "sub_county": sub_county, "ward": ward.strip(),
                    "village": village.strip(), "farming_type": farming_type,
                    "latitude": lat, "longitude": lon,
                    "share_contact": share_contact, "in_directory": in_directory}
            if db.create_farmer(info, password):
                st.session_state.user = db.check_login(clean_phone, password)
                st.rerun()
            else:
                st.error("That phone number is already registered. Use the Log in tab.")
 
 
# ---------- MAIN ----------
user = st.session_state.user
if user is None:
    login_page()
    st.stop()
 
pages = [p for p in load_pages() if allowed(p, user)]
labels = [p["label"] for p in pages]
if st.session_state.get("menu_choice") not in labels:
    st.session_state.pop("menu_choice", None)
 
st.sidebar.markdown(f"### 🌾 {config.APP_NAME}")
st.sidebar.write(f"Hello, **{user['name']}**")
if user["role"] != "farmer":
    st.sidebar.caption(f"{user['role'].title()} - {user['sub_county']}")
choice = st.sidebar.radio("Menu", labels, key="menu_choice")
if st.sidebar.button("Log out"):
    st.session_state.clear()
    st.rerun()
 
page = pages[labels.index(choice)]
try:
    page["func"](user)
except Exception as error:
    print("PAGE ERROR:", page["label"], repr(error))
    st.error("Something went wrong on this page. Please try again.")
    if user["role"] == "admin":
        st.exception(error)
