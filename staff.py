"""Pages for sub-county coordinators and the administrator."""
from datetime import date
 
import pandas as pd
import streamlit as st
 
import config
import db
 
STAFF = ("coordinator", "admin")
 
 
def staff_sub_county(user, key):
    """Coordinators work only on their own sub-county. Admins choose."""
    if user["role"] == "coordinator":
        st.info(f"You are working on: {user['sub_county']}")
        return user["sub_county"]
    return st.selectbox("Sub-county", config.SUB_COUNTIES, key=key)
 
 
def delete_box(tbl, user, key):
    with st.expander("Delete a mistaken upload"):
        number = st.number_input("Number to delete (the No. column)", min_value=1,
                                 step=1, key=f"{key}_no")
        if st.button("Delete", key=f"{key}_btn"):
            if db.delete_staff_row(tbl, int(number), user):
                st.success("Deleted.")
                st.rerun()
            else:
                st.error("Nothing was deleted. Check the number. You can only delete "
                         "your own uploads.")
 
 
def blank_grid(columns):
    return pd.DataFrame([columns] * 8)
 
 
def text_or(value, fallback):
    """A cleared table cell comes back empty. Use the fallback instead."""
    return value if isinstance(value, str) and value else fallback
 
 
def usable_rows(grid, price_column="price"):
    """Keep only the rows the person actually filled in."""
    grid = grid.dropna(subset=[price_column])
    return grid[grid[price_column] > 0]
 
 
# ---------- MARKET PRICES ----------
def upload_market_page(user):
    st.header("📤 Upload market prices")
    st.caption("Enter the prices you collected at one ward market. Each product gets "
               "one row. Use the + under the table to add more rows.")
    sub = staff_sub_county(user, "um_sub")
    with st.form("market_form", clear_on_submit=True):
        entry_date = st.date_input("Date the prices were collected", date.today(),
                                   max_value=date.today())
        ward = st.text_input("Ward")
        market = st.text_input("Market name")
        grid = st.data_editor(
            blank_grid({"product": None, "unit": "kg",
                        "price": float("nan"), "demand": "Medium"}),
            num_rows="dynamic", width="stretch", hide_index=True, key="market_grid",
            column_config={
                "product": st.column_config.SelectboxColumn(
                    "Product", options=config.PRODUCTS),
                "unit": st.column_config.SelectboxColumn(
                    "Unit", options=config.PRICE_UNITS),
                "price": st.column_config.NumberColumn(
                    "Price (KES)", min_value=0.0, step=1.0),
                "demand": st.column_config.SelectboxColumn(
                    "Demand", options=config.DEMAND_LEVELS)})
        if st.form_submit_button("Save prices"):
            rows = usable_rows(grid).dropna(subset=["product"])
            if not ward.strip() or not market.strip():
                st.error("Please fill in the ward and the market name.")
            elif rows.empty:
                st.error("Add at least one product with a price.")
            else:
                entries = [{
                    "entry_date": entry_date, "sub_county": sub,
                    "ward": ward.strip(), "market": market.strip(),
                    "product": r["product"], "unit": text_or(r["unit"], "kg"),
                    "price": float(r["price"]),
                    "demand": text_or(r["demand"], "Medium")}
                    for _, r in rows.iterrows()]
                db.add_market_prices(entries, user["id"])
                st.success(f"Saved {len(entries)} prices.")
    st.subheader("Recent uploads")
    mine = db.get_market_prices(
        sub_county=None if user["role"] == "admin" else sub,
        uploader_id=None if user["role"] == "admin" else user["id"], limit=40)
    if mine.empty:
        st.info("Nothing uploaded yet.")
    else:
        st.dataframe(mine.rename(columns={"id": "No."}), width="stretch",
                     hide_index=True)
        delete_box("market_prices", user, "del_mp")
 
 
# ---------- INPUT PRICES ----------
def upload_input_page(user):
    st.header("📤 Upload farm input prices")
    st.caption("Enter the prices you found at one agrovet. Each item gets one row.")
    sub = staff_sub_county(user, "ui_sub")
    with st.form("input_form", clear_on_submit=True):
        entry_date = st.date_input("Date the prices were collected", date.today(),
                                   max_value=date.today())
        agrovet = st.text_input("Agrovet name and town")
        grid = st.data_editor(
            blank_grid({"item": None, "unit": "kg", "price": float("nan")}),
            num_rows="dynamic", width="stretch", hide_index=True, key="input_grid",
            column_config={
                "item": st.column_config.SelectboxColumn(
                    "Item", options=config.INPUT_ITEMS),
                "unit": st.column_config.SelectboxColumn(
                    "Unit", options=config.PRICE_UNITS + ["packet", "litre bottle"]),
                "price": st.column_config.NumberColumn(
                    "Price (KES)", min_value=0.0, step=1.0)})
        if st.form_submit_button("Save prices"):
            rows = usable_rows(grid).dropna(subset=["item"])
            if not agrovet.strip():
                st.error("Please fill in the agrovet name.")
            elif rows.empty:
                st.error("Add at least one item with a price.")
            else:
                entries = [{
                    "entry_date": entry_date, "sub_county": sub,
                    "agrovet": agrovet.strip(), "item": r["item"],
                    "unit": text_or(r["unit"], "kg"), "price": float(r["price"])}
                    for _, r in rows.iterrows()]
                db.add_input_prices(entries, user["id"])
                st.success(f"Saved {len(entries)} prices.")
    st.subheader("Recent uploads")
    mine = db.get_input_prices(
        sub_county=None if user["role"] == "admin" else sub,
        uploader_id=None if user["role"] == "admin" else user["id"], limit=40)
    if mine.empty:
        st.info("Nothing uploaded yet.")
    else:
        st.dataframe(mine.rename(columns={"id": "No."}), width="stretch",
                     hide_index=True)
        delete_box("input_prices", user, "del_ip")
 
 
# ---------- OPPORTUNITIES ----------
def post_opportunity_page(user):
    st.header("📣 Post an opportunity")
    st.caption("Government or non-government programmes, grants, trainings, inputs "
               "subsidies and markets that farmers can benefit from.")
    if user["role"] == "coordinator":
        targets = [user["sub_county"], config.ALL_SUB_COUNTIES]
    else:
        targets = [config.ALL_SUB_COUNTIES] + config.SUB_COUNTIES
    with st.form("opp_form", clear_on_submit=True):
        title = st.text_input("Title")
        provider = st.text_input("Who is offering it?")
        kind = st.selectbox("Type", config.OPPORTUNITY_TYPES)
        details = st.text_area("Details (what is offered, who qualifies)")
        contact = st.text_input("How to apply or who to contact")
        target = st.selectbox("Who is it for?", targets)
        has_deadline = st.checkbox("This opportunity has a closing date")
        deadline = st.date_input("Closing date (used only if the box above is ticked)",
                                 date.today())
        if st.form_submit_button("Post"):
            if not title.strip() or not details.strip():
                st.error("Please fill in the title and the details.")
            elif has_deadline and deadline < date.today():
                st.error("The closing date cannot be in the past.")
            else:
                db.add_opportunity({
                    "title": title.strip(), "provider": provider.strip(),
                    "kind": kind, "details": details.strip(),
                    "deadline": deadline if has_deadline else None,
                    "sub_county": target, "contact": contact.strip()}, user["id"])
                st.success("Posted. Farmers can now see it.")
    st.subheader("Opportunities I posted")
    mine = db.get_opportunities(only_open=False,
                                poster_id=None if user["role"] == "admin" else user["id"])
    if mine.empty:
        st.info("Nothing posted yet.")
    else:
        st.dataframe(mine[["id", "title", "kind", "deadline", "sub_county"]].rename(
            columns={"id": "No."}), width="stretch", hide_index=True)
        delete_box("opportunities", user, "del_op")
 
 
# ---------- OVERVIEW OF FARMERS ----------
def overview_page(user):
    st.header("🗺️ Farmers overview")
    users = db.list_users()
    farmers = users[users["role"] == "farmer"].copy()
    if user["role"] == "coordinator":
        farmers = farmers[farmers["sub_county"] == user["sub_county"]]
        st.caption(f"Farmers registered in {user['sub_county']}")
    if farmers.empty:
        st.info("No farmers have registered yet.")
        return
    farmers["scale"] = farmers["active_acres"].apply(config.scale_for)
    c1, c2, c3 = st.columns(3)
    c1.metric("Farmers", len(farmers))
    c2.metric("Land in active use", f"{farmers['active_acres'].sum():,.0f} acres")
    c3.metric("Women farmers", int((farmers["gender"] == "Female").sum()))
    left, right = st.columns(2)
    with left:
        st.write("**Farmers by sub-county**")
        st.bar_chart(farmers["sub_county"].value_counts(), color="#2E7D32")
        st.write("**Farmers by type of farming**")
        st.bar_chart(farmers["farming_type"].value_counts(), color="#D4A017")
    with right:
        st.write("**Farmers by gender**")
        st.bar_chart(farmers["gender"].value_counts(), color="#B5651D")
        st.write("**Farmers by scale**")
        st.bar_chart(farmers["scale"].value_counts(), color="#2E7D32")
    st.subheader("Registered farmers")
    st.dataframe(farmers[["name", "gender", "sub_county", "ward", "village",
                          "farming_type", "scale", "created_at"]].rename(columns={
        "name": "Name", "gender": "Gender", "sub_county": "Sub-county", "ward": "Ward",
        "village": "Village", "farming_type": "Farming", "scale": "Scale",
        "created_at": "Joined"}), width="stretch", hide_index=True)
 
 
# ---------- ADMIN: USERS ----------
def admin_users_page(user):
    st.header("🔧 Admin: users")
    users = db.list_users()
    st.dataframe(users, width="stretch", hide_index=True)
    st.download_button("Download this list (CSV)", users.to_csv(index=False),
                       file_name="ukulimakonect_users.csv", mime="text/csv")
    st.caption("This list contains personal details. Keep the file safe and do not "
               "share it.")
 
    st.subheader("Make someone a coordinator or administrator")
    with st.form("role_form", clear_on_submit=True):
        phone = st.text_input("Their phone number")
        role = st.selectbox("New role", config.ROLES, index=1)
        sub_county = st.selectbox("Sub-county (for coordinators)", config.SUB_COUNTIES)
        if st.form_submit_button("Change role"):
            clean = config.normalize_phone(phone)
            if not clean:
                st.error("Enter a valid phone number.")
            elif clean == user["phone"]:
                st.error("You cannot change your own role.")
            elif db.set_role(clean, role, sub_county if role == "coordinator" else None):
                st.success("Done. The change shows the next time they log in.")
            else:
                st.error("No account has that phone number.")
 
    st.subheader("Switch an account off or on")
    with st.form("active_form", clear_on_submit=True):
        phone = st.text_input("Phone number of the account")
        state = st.radio("Set the account to", ["Off", "On"], horizontal=True)
        if st.form_submit_button("Apply"):
            clean = config.normalize_phone(phone)
            if not clean:
                st.error("Enter a valid phone number.")
            elif clean == user["phone"]:
                st.error("You cannot switch off your own account.")
            elif db.set_active(clean, state == "On"):
                st.success("Done.")
            else:
                st.error("No account has that phone number.")
 
    st.subheader("Reset a forgotten password")
    with st.form("reset_form", clear_on_submit=True):
        phone = st.text_input("Phone number of the farmer")
        temp = st.text_input("Temporary password (8 or more characters)")
        if st.form_submit_button("Reset password"):
            clean = config.normalize_phone(phone)
            if not clean:
                st.error("Enter a valid phone number.")
            elif len(temp) < 8:
                st.error("The temporary password must have 8 or more characters.")
            elif db.reset_password(clean, temp):
                st.success("Done. Give the farmer the temporary password privately "
                           "and ask them to change it in My Profile.")
            else:
                st.error("No account has that phone number.")
 
 
# ---------- ADMIN: YIELD REFERENCE ----------
def yield_reference_page(user):
    st.header("🔧 Admin: reference yields")
    st.write("These figures decide the 'possible harvest' shown on farmer dashboards. "
             "They are only starting estimates. Replace them with figures from the "
             "county agriculture office. Give the most a good farm could harvest from "
             "one acre in one season, in kg.")
    edited = st.data_editor(
        db.get_yield_reference(), num_rows="dynamic", width="stretch", hide_index=True,
        key="yield_editor",
        column_config={
            "crop": st.column_config.SelectboxColumn(
                "Crop", options=config.ALL_CROPS, required=True),
            "kg_per_acre": st.column_config.NumberColumn(
                "Best kg per acre per season", min_value=1.0, required=True)})
    if st.button("Save reference yields"):
        clean = edited.dropna().drop_duplicates("crop", keep="last")
        db.save_yield_reference(clean)
        st.success("Saved.")
 
 
PAGES = [
    {"order": 210, "label": "📤 Upload market prices", "func": upload_market_page,
     "roles": STAFF},
    {"order": 220, "label": "📤 Upload input prices", "func": upload_input_page,
     "roles": STAFF},
    {"order": 230, "label": "📣 Post an opportunity", "func": post_opportunity_page,
     "roles": STAFF},
    {"order": 240, "label": "🗺️ Farmers overview", "func": overview_page,
     "roles": STAFF},
    {"order": 910, "label": "🔧 Admin: users", "func": admin_users_page,
     "roles": ("admin",)},
    {"order": 920, "label": "🔧 Admin: reference yields", "func": yield_reference_page,
     "roles": ("admin",)},
]
