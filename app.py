import streamlit as st
from datetime import date
import db

st.set_page_config(page_title="Farmer E-Book", page_icon="🌾")
db.init_db()

if "farmer" not in st.session_state:
    st.session_state.farmer = None

SUB_COUNTIES = [
    "Homa Bay Town", "Kabondo Kasipul", "Karachuonyo", "Kasipul",
    "Ndhiwa", "Rangwe", "Suba North", "Suba South", "Other",
]
FARM_TYPES = ["Crops", "Livestock"]

# ---------- CROP OPTIONS ----------
CROPS = [
    "Maize", "Groundnuts", "Cotton", "Sorghum", "Finger millet", "Beans",
    "Green grams", "Cassava", "Sweet potato", "Rice", "Vegetables", "Other",
]
CROP_ACTIVITIES = {
    "Planting": ["acres"],
    "Fertilizer applied": ["kg", "bags"],
    "Spraying": ["litres", "acres"],
    "Weeding": ["acres"],
    "Harvest": ["kg", "bags"],
}

# ---------- LIVESTOCK OPTIONS ----------
HERD_EVENTS = ["Born", "Died", "Bought", "Sold", "Vaccinated", "Dewormed",
               "Tick control", "Treated for illness", "AI / service"]
ANIMAL_ACTIVITIES = {
    "Cattle (dairy)": HERD_EVENTS + ["Calved", "Milk produced"],
    "Cattle (beef/zebu)": HERD_EVENTS + ["Calved"],
    "Goats": HERD_EVENTS + ["Kidded", "Milk produced"],
    "Sheep": HERD_EVENTS + ["Lambed"],
    "Chickens": ["Bought", "Hatched", "Died", "Sold", "Vaccinated",
                 "Treated for illness", "Eggs collected"],
    "Fish": ["Stocked fingerlings", "Feed given", "Died", "Catch / harvest"],
    "Other": HERD_EVENTS,
}
LIVESTOCK_UNITS = {
    "Milk produced": ["litres"],
    "Eggs collected": ["eggs", "trays"],
    "Feed given": ["kg"],
    "Stocked fingerlings": ["fingerlings"],
    "Catch / harvest": ["kg", "pieces"],
}


def show_records(table, farmer_id):
    st.subheader("Recent records")
    df = db.get_records(table, farmer_id)
    if df.empty:
        st.info("No records yet.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


# ---------- LOGIN / REGISTER ----------
def login_page():
    st.title("🌾 Farmer E-Book")
    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        with st.form("login_form"):
            phone = st.text_input("Phone number")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                result = db.check_login(phone, password)
                if result:
                    st.session_state.farmer = {
                        "id": result[0], "name": result[1], "types": result[2]
                    }
                    st.rerun()
                else:
                    st.error("Wrong phone number or password.")

    with tab_register:
        with st.form("register_form"):
            name = st.text_input("Full name")
            phone = st.text_input("Phone number (used to log in)")
            sub_county = st.selectbox("Sub-county", SUB_COUNTIES)
            types = st.multiselect(
                "What do you farm? (choose all that apply)", FARM_TYPES,
                help="Livestock includes cattle, goats, sheep, chickens and fish.",
            )
            password = st.text_input("Choose a password", type="password")
            if st.form_submit_button("Create account"):
                if not name or not phone or not types or len(password) < 6:
                    st.error("Fill in everything, choose at least one type of farming, "
                             "and use a password of 6+ characters.")
                elif db.create_farmer(name, phone, sub_county, types, password):
                    st.success("Account created. Go to the Log in tab.")
                else:
                    st.error("That phone number is already registered.")


# ---------- MONEY ----------
def money_page(fid):
    st.header("💰 Money")
    with st.form("money_form", clear_on_submit=True):
        entry_date = st.date_input("Date", date.today())
        kind = st.radio("Type", ["Income", "Expense"], horizontal=True)
        category = st.selectbox("Category", [
            "Crop sales", "Cotton sales", "Milk sales", "Livestock sales",
            "Poultry/eggs", "Fish sales",
            "Seed & fertilizer", "Feed", "Drugs & vet", "Fingerlings",
            "Labour", "Transport", "Other",
        ])
        description = st.text_input("Note (optional)")
        amount = st.number_input("Amount (KES)", min_value=0.0, step=50.0)
        if st.form_submit_button("Save"):
            if amount > 0:
                db.add_record("money", fid, entry_date, kind=kind, category=category,
                              description=description, amount=amount)
                st.success("Saved.")
            else:
                st.error("Enter an amount above 0.")
    show_records("money", fid)


# ---------- CROPS ----------
def crops_page(fid):
    st.header("🌽 Crops")
    crop = st.selectbox("Crop", CROPS, key="crop_pick")
    activity = st.selectbox("What did you do?", list(CROP_ACTIVITIES), key="crop_act")
    with st.form("crops_form", clear_on_submit=True):
        entry_date = st.date_input("Date", date.today())
        quantity = st.number_input("How much?", min_value=0.0, step=1.0)
        unit = st.selectbox("Unit", CROP_ACTIVITIES[activity])
        note = st.text_input("Note (optional, e.g. rains came late)")
        if st.form_submit_button("Save"):
            if quantity > 0:
                db.add_record("crops", fid, entry_date, crop=crop, activity=activity,
                              quantity=quantity, unit=unit, note=note)
                st.success("Saved.")
            else:
                st.error("Enter a quantity above 0.")
    show_records("crops", fid)


# ---------- LIVESTOCK ----------
def livestock_page(fid):
    st.header("🐂 Livestock")
    animal = st.selectbox("Animal", list(ANIMAL_ACTIVITIES), key="animal_pick")
    activity = st.selectbox("What happened?", ANIMAL_ACTIVITIES[animal], key="animal_act")
    units = LIVESTOCK_UNITS.get(activity, ["animals"])
    with st.form("livestock_form", clear_on_submit=True):
        entry_date = st.date_input("Date", date.today())
        quantity = st.number_input("How many / how much?", min_value=0.0, step=1.0)
        unit = st.selectbox("Unit", units)
        note = st.text_input("Note (optional, e.g. which cow, drug used, withdrawal days)")
        if st.form_submit_button("Save"):
            if quantity > 0:
                db.add_record("livestock", fid, entry_date, animal=animal,
                              activity=activity, quantity=quantity, unit=unit, note=note)
                st.success("Saved.")
            else:
                st.error("Enter a number above 0.")
    show_records("livestock", fid)


# ---------- SUMMARY ----------
def dashboard_page(farmer):
    fid = farmer["id"]
    types = farmer["types"]
    st.header("📊 My Summary")

    money = db.get_records("money", fid)
    income = money.loc[money["kind"] == "Income", "amount"].sum()
    expense = money.loc[money["kind"] == "Expense", "amount"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Income", f"KES {income:,.0f}")
    c2.metric("Expenses", f"KES {expense:,.0f}")
    c3.metric("Profit", f"KES {income - expense:,.0f}")

    st.subheader("Spending by category")
    spend = money[money["kind"] == "Expense"]
    if spend.empty:
        st.info("Add expenses to see where your money goes.")
    else:
        st.bar_chart(spend.groupby("category")["amount"].sum())

    if "Crops" in types:
        st.subheader("🌽 Crops")
        crops = db.get_records("crops", fid)
        if crops.empty:
            st.info("Record planting and harvest to see totals here.")
        else:
            totals = crops.groupby(["crop", "activity", "unit"], as_index=False)["quantity"].sum()
            st.dataframe(totals, width="stretch", hide_index=True)

    if "Livestock" in types:
        st.subheader("🐂 Livestock")
        stock = db.get_records("livestock", fid)
        if stock.empty:
            st.info("Record births, sales, treatments and production to see totals here.")
        else:
            totals = stock.groupby(["animal", "activity", "unit"], as_index=False)["quantity"].sum()
            st.dataframe(totals, width="stretch", hide_index=True)

            milk = stock[stock["activity"] == "Milk produced"]
            if not milk.empty:
                st.subheader("🥛 Milk per day (litres)")
                st.bar_chart(milk.groupby("entry_date")["quantity"].sum())


# ---------- MAIN ----------
farmer = st.session_state.farmer

if farmer is None:
    login_page()
else:
    pages = {"My Summary": None, "Money": money_page}
    if "Crops" in farmer["types"]:
        pages["Crops"] = crops_page
    if "Livestock" in farmer["types"]:
        pages["Livestock"] = livestock_page

    st.sidebar.write(f"Hello, **{farmer['name']}**")
    choice = st.sidebar.radio("Menu", list(pages.keys()))
    if st.sidebar.button("Log out"):
        st.session_state.farmer = None
        st.rerun()

    if choice == "My Summary":
        dashboard_page(farmer)
    else:
        pages[choice](farmer["id"])