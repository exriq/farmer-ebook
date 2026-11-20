"""Pages made for agrovets: My Shop (prices that farmers see) and Demand near me."""
from datetime import date

import streamlit as st

import chat
import config
import db
import extras
import style


@st.dialog("Add or update a price")
def price_dialog(user):
    name = st.text_input("Product", placeholder="e.g. DAP fertiliser, hybrid maize seed")
    unit = st.selectbox("Sold per", config.INPUT_UNITS)
    price = st.number_input("Price (KES)", min_value=0.0, step=10.0)
    if st.button("Save price", type="primary", width="stretch"):
        if not name.strip() or price <= 0:
            st.error("Enter the product and a price above 0.")
            return
        db.run("DELETE FROM input_prices WHERE uploaded_by = %s AND lower(item) = lower(%s) "
               "AND unit = %s", (user["id"], name.strip(), unit))       # an update replaces the old price
        db.run("""INSERT INTO input_prices (entry_date, sub_county, agrovet, item, unit, price,
                                            uploaded_by)
                  VALUES (%s, %s, %s, %s, %s, %s, %s)""",
               (date.today(), user["sub_county"], user["name"], name.strip(), unit, price,
                user["id"]))
        st.toast("Price saved ✓")
        st.rerun()


def shop_page(user):
    style.header("My Shop", "The prices farmers in your sub-county can see")
    mine = db.table("SELECT id, entry_date, item, unit, price FROM input_prices "
                    "WHERE uploaded_by = %s ORDER BY entry_date DESC, item", (user["id"],))
    reach = int(db.rows("SELECT COUNT(*) FROM farmers WHERE role = 'farmer' AND active "
                        "AND in_directory AND sub_county = %s", (user["sub_county"],))[0][0])
    style.kpi_row([("Products listed", len(mine), "with a price", False),
                   ("Last updated", f"{mine.entry_date.max():%d %b}" if len(mine) else "-",
                    "keep prices fresh", False),
                   ("New messages", chat.unread_count(user["id"]), "from farmers", False),
                   ("Farmers you can reach", reach, user["sub_county"], False)])
    st.write("")
    if st.button("＋ Add or update a price", type="primary"):
        price_dialog(user)
    with st.container(border=True):
        st.subheader("My prices")
        if mine.empty:
            st.info("You have not listed any prices yet. Farmers compare prices on the "
                    "**Input prices** page, so listed products get more enquiries.")
        else:
            extras.tick_table(mine, "shop_tbl", {"entry_date": "Date", "item": "Product",
                              "unit": "Per", "price": "Price (KES)"},
                              lambda i: db.run("DELETE FROM input_prices WHERE id = %s "
                                               "AND uploaded_by = %s", (i, user["id"])))


def demand_page(user):
    sub = user["sub_county"]
    if user["role"] == "admin":
        sub = st.selectbox("Sub-county", config.SUB_COUNTIES)
    style.header("Demand near me", f"What farmers in {sub} grow and keep")
    crops = db.table("""SELECT c.crop AS "Crop", SUM(c.acres) AS "Acres",
                               COUNT(DISTINCT c.farmer_id) AS "Farmers"
                        FROM farmer_crops c JOIN farmers f ON f.id = c.farmer_id
                        WHERE f.sub_county = %s AND f.active AND f.role = 'farmer'
                        GROUP BY c.crop ORDER BY SUM(c.acres) DESC LIMIT 10""", (sub,))
    animals = db.table("""SELECT a.animal AS "Animal", SUM(a.head_count) AS "Number",
                                 COUNT(DISTINCT a.farmer_id) AS "Farmers"
                          FROM farm_animals a JOIN farmers f ON f.id = a.farmer_id
                          WHERE f.sub_county = %s AND f.active AND f.role = 'farmer'
                            AND COALESCE(a.status, 'Active') = 'Active'
                          GROUP BY a.animal ORDER BY SUM(a.head_count) DESC""", (sub,))
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.subheader("Crops by acres")
        if crops.empty:
            st.info("No crops listed by farmers here yet.")
        else:
            st.bar_chart(crops.set_index("Crop")["Acres"], color="#1E6B47")
            st.caption(f"Most grown: **{crops.iloc[0]['Crop']}**, on "
                       f"{crops.iloc[0]['Acres']:,.0f} acres by {int(crops.iloc[0]['Farmers'])} farmers. "
                       "Stock the seed, fertiliser and chemicals this crop needs.")
    with right, st.container(border=True):
        st.subheader("Animals, birds and fish")
        if animals.empty:
            st.info("No animals listed by farmers here yet.")
        else:
            st.bar_chart(animals.set_index("Animal")["Number"], color="#C58F1E")
            st.caption(f"Most kept: **{animals.iloc[0]['Animal']}**. Think about feed, "
                       "vaccines and dewormers for it.")
    st.caption("These are totals only. No farmer's name or phone number is shown here.")


PAGES = [
    {"order": 15, "label": "🏪 My Shop", "func": shop_page, "roles": ("agrovet",)},
    {"order": 16, "label": "🌾 Demand near me", "func": demand_page,
     "roles": ("agrovet", "coordinator", "admin")},
]
