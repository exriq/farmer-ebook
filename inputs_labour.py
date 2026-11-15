"""Farm input stock (seed, fertilizer, feed, drugs) and labour pages."""
from datetime import date
 
import pandas as pd
import streamlit as st
 
import config
import db
from records import show_records
 
 
def stock_table(moves):
    """Work out what is left in store: bought minus used, for each item."""
    if moves.empty:
        return pd.DataFrame(columns=["Item", "Unit", "Bought", "Used", "In store"])
    pivot = moves.pivot_table(index=["item", "unit"], columns="movement",
                              values="quantity", aggfunc="sum", fill_value=0)
    for column in ("Bought", "Used"):
        if column not in pivot.columns:
            pivot[column] = 0.0
    pivot = pivot[["Bought", "Used"]].reset_index()
    pivot["In store"] = pivot["Bought"] - pivot["Used"]
    return pivot.rename(columns={"item": "Item", "unit": "Unit"})
 
 
def inputs_page(user):
    st.header("🧺 Farm inputs and stock")
    movement = st.radio("What happened?", ["Bought", "Used"], horizontal=True,
                        key="input_move")
    with st.form("inputs_form", clear_on_submit=True):
        entry_date = st.date_input("Date", date.today(), max_value=date.today())
        category = st.selectbox("Type of input", config.INPUT_CATEGORIES)
        item = st.text_input("Item name (e.g. DAP, hybrid maize seed, dairy meal)")
        quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
        unit = st.selectbox("Unit", config.INPUT_UNITS)
        cost = 0.0
        if movement == "Bought":
            cost = st.number_input("Total cost (KES)", min_value=0.0, step=50.0)
        if st.form_submit_button("Save"):
            if quantity > 0 and item.strip():
                db.add_record("inventory_moves", user["id"], entry_date,
                              item=item.strip().title(), category=category,
                              movement=movement, quantity=quantity, unit=unit,
                              cost=cost)
                st.success("Saved.")
            else:
                st.error("Enter the item name and a quantity above 0.")
    st.subheader("What is in my store")
    moves = db.get_records("inventory_moves", user["id"])
    stock = stock_table(moves)
    if stock.empty:
        st.info("No inputs recorded yet.")
    else:
        st.dataframe(stock, width="stretch", hide_index=True)
        if (stock["In store"] < 0).any():
            st.warning("Some items show a negative amount in store. You may have "
                       "forgotten to record a purchase.")
    show_records("inventory_moves", user["id"], "Recent input records")
 
 
def labour_page(user):
    st.header("👷 Labour")
    with st.form("labour_form", clear_on_submit=True):
        entry_date = st.date_input("Date", date.today(), max_value=date.today())
        worker_type = st.selectbox("Who did the work?", config.WORKER_TYPES)
        activity = st.selectbox("Work done", config.LABOUR_ACTIVITIES)
        people_days = st.number_input(
            "Person-days (people x days, e.g. 3 people for 2 days = 6)",
            min_value=0.0, step=0.5)
        cost = st.number_input("Amount paid (KES, leave 0 for family work)",
                               min_value=0.0, step=50.0)
        if st.form_submit_button("Save"):
            if people_days > 0:
                db.add_record("labour", user["id"], entry_date,
                              worker_type=worker_type, activity=activity,
                              people_days=people_days, cost=cost)
                st.success("Saved.")
            else:
                st.error("Enter person-days above 0.")
    show_records("labour", user["id"], "Recent labour records")
 
 
PAGES = [
    {"order": 50, "label": "🧺 Inputs and stock", "func": inputs_page,
     "roles": ("farmer",)},
    {"order": 60, "label": "👷 Labour", "func": labour_page, "roles": ("farmer",)},
]
