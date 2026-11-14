"""Daily record pages: Money, Crops and Livestock."""
from datetime import date
 
import streamlit as st
 
import config
import db
 
 
def show_records(tbl, farmer_id, title="Recent records"):
    """Show the latest records, with a way to delete a mistaken one."""
    st.subheader(title)
    df = db.get_records(tbl, farmer_id, limit=100)
    if df.empty:
        st.info("No records yet.")
        return
    st.dataframe(df.rename(columns={"id": "No."}), width="stretch", hide_index=True)
    with st.expander("Delete a mistaken record"):
        number = st.number_input("Record number (the No. column)", min_value=1,
                                 step=1, key=f"del_no_{tbl}")
        if st.button("Delete this record", key=f"del_btn_{tbl}"):
            if db.delete_record(tbl, farmer_id, int(number)):
                st.success("Deleted.")
                st.rerun()
            else:
                st.error("No record with that number was found in your records.")
 
 
def money_page(user):
    st.header("💰 Money")
    kind = st.radio("Type", ["Income", "Expense"], horizontal=True, key="money_kind")
    categories = (config.INCOME_CATEGORIES if kind == "Income"
                  else config.EXPENSE_CATEGORIES)
    with st.form("money_form", clear_on_submit=True):
        entry_date = st.date_input("Date", date.today(), max_value=date.today())
        category = st.selectbox("Category", categories)
        description = st.text_input("Note (optional)")
        amount = st.number_input("Amount (KES)", min_value=0.0, step=50.0)
        if st.form_submit_button("Save"):
            if amount > 0:
                db.add_record("money", user["id"], entry_date, kind=kind,
                              category=category, description=description,
                              amount=amount)
                st.success("Saved.")
            else:
                st.error("Enter an amount above 0.")
    show_records("money", user["id"])
 
 
def crops_page(user):
    st.header("🌽 Crop records")
    group = st.selectbox("Crop group", list(config.CROP_GROUPS), key="crop_group_pick")
    crop = st.selectbox("Crop", config.CROP_GROUPS[group], key="crop_pick")
    activity = st.selectbox("What did you do?", list(config.CROP_ACTIVITIES),
                            key="crop_act")
    with st.form("crops_form", clear_on_submit=True):
        entry_date = st.date_input("Date", date.today(), max_value=date.today())
        quantity = st.number_input("How much?", min_value=0.0, step=1.0)
        unit = st.selectbox("Unit", config.CROP_ACTIVITIES[activity])
        note = st.text_input("Note (optional, e.g. rains came late)")
        if st.form_submit_button("Save"):
            if quantity > 0:
                db.add_record("crop_records", user["id"], entry_date, crop=crop,
                              activity=activity, quantity=quantity, unit=unit,
                              note=note)
                st.success("Saved.")
            else:
                st.error("Enter a quantity above 0.")
    show_records("crop_records", user["id"])
 
 
def livestock_page(user):
    st.header("🐂 Livestock records")
    animal = st.selectbox("Animal", config.ANIMALS, key="animal_pick")
    activity = st.selectbox("What happened?", config.ANIMAL_ACTIVITIES[animal],
                            key="animal_act")
    units = config.LIVESTOCK_UNITS.get(activity, ["animals"])
    with st.form("livestock_form", clear_on_submit=True):
        entry_date = st.date_input("Date", date.today(), max_value=date.today())
        quantity = st.number_input("How many / how much?", min_value=0.0, step=1.0)
        unit = st.selectbox("Unit", units)
        note = st.text_input("Note (optional, e.g. which cow, drug used)")
        if st.form_submit_button("Save"):
            if quantity > 0:
                db.add_record("livestock_records", user["id"], entry_date,
                              animal=animal, activity=activity, quantity=quantity,
                              unit=unit, note=note)
                st.success("Saved.")
            else:
                st.error("Enter a number above 0.")
    st.caption("If you sold something, also record the money in the Money page.")
    show_records("livestock_records", user["id"])
 
 
PAGES = [
    {"order": 20, "label": "🌽 Crop records", "func": crops_page,
     "roles": ("farmer",), "types": ("Crops", "Mixed")},
    {"order": 30, "label": "🐂 Livestock records", "func": livestock_page,
     "roles": ("farmer",), "types": ("Livestock", "Mixed")},
    {"order": 40, "label": "💰 Money", "func": money_page, "roles": ("farmer",)},
]
