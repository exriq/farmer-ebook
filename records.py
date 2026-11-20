"""Money, Crop records and Livestock records: cards, pop-up forms and tick-box delete."""
from datetime import date
 
import pandas as pd
import streamlit as st
 
import config
import db
import extras
import style
 
 
def show_records(tbl, farmer_id, title="Recent records"):
    """Latest records with tick boxes to delete mistakes. Also used by Inputs and Labour."""
    st.subheader(title)
    df = db.get_records(tbl, farmer_id, limit=100)
    if df.empty:
        st.info("No records yet.")
        return
    nice = {c: c.replace("_", " ").capitalize() for c in df.columns if c != "id"}
    extras.tick_table(df, f"rec_{tbl}", nice, lambda i: db.delete_record(tbl, farmer_id, i))
 
 
def _sum_since(fid, start):
    got = dict(db.rows("SELECT kind, SUM(amount) FROM money WHERE farmer_id = %s "
                       "AND entry_date >= %s GROUP BY kind", (fid, start)))
    return float(got.get("Income") or 0), float(got.get("Expense") or 0)
 
 
def _chart(split, unit):
    """Bar chart of sold and used at home, from {name: {sold, home}}."""
    data = {n: v for n, v in split.items() if v["sold"] + v["home"] > 0}
    if data:
        frame = pd.DataFrame({"Sold": [v["sold"] for v in data.values()],
                              "Used at home": [v["home"] for v in data.values()]},
                             index=list(data))
        with st.container(border=True):
            st.subheader(f"Sold and used at home ({unit})")
            st.bar_chart(frame, color=["#1E6B47", "#C58F1E"])
 
 
def _share_cards(split, unit):
    total = sum(v["total"] for v in split.values())
    sold = sum(v["sold"] for v in split.values())
    home = sum(v["home"] for v in split.values())
    both = sold + home
    style.kpi_row([("Total produced", f"{total:,.0f} {unit}", "all records", False),
                   ("Sold", f"{sold / both * 100:,.0f}%" if both else "-", f"{sold:,.0f} {unit}", False),
                   ("Used at home", f"{home / both * 100:,.0f}%" if both else "-", f"{home:,.0f} {unit}", False)])
 
 
def _split_inputs(units, label):
    """Amount sold + amount used at home. The total is worked out for the farmer."""
    unit = st.selectbox("Unit", units)
    a, b = st.columns(2)
    sold = a.number_input("Amount sold", min_value=0.0, step=1.0, key="split_sold")
    home = b.number_input("Amount used at home", min_value=0.0, step=1.0, key="split_home")
    st.metric(f"{label} (calculated)", f"{sold + home:,.1f} {unit}")
    return unit, sold, home
 
 
# ---------- MONEY ----------
@st.dialog("Record money")
def money_dialog(user, kind):
    st.markdown("**💰 Money received**" if kind == "Income" else "**💸 Money spent**")
    when = st.date_input("Date", date.today(), max_value=date.today())
    cats = config.INCOME_CATEGORIES if kind == "Income" else config.EXPENSE_CATEGORIES
    category = st.selectbox("What was it for?" if kind == "Expense" else "What did you sell?", cats)
    which = st.selectbox("Which crop or animal?", ["Whole farm"] + extras.enterprise_names(user["id"]))
    amount = st.number_input("Amount (KES)", min_value=0.0, step=50.0)
    note = st.text_input("Note (optional)")
    if st.button("Save", type="primary", width="stretch"):
        if amount <= 0:
            st.error("Enter an amount above 0.")
            return
        db.add_record("money", user["id"], when, kind=kind, category=category,
                      description=note, amount=amount,
                      enterprise=None if which == "Whole farm" else which)
        st.toast("Saved ✓")
        st.rerun()
 
 
def money_page(user):
    fid = user["id"]
    style.header("Money", "Money received and money spent")
    today = date.today()
    mi, mo = _sum_since(fid, date(today.year, today.month, 1))
    yi, yo = _sum_since(fid, date(today.year, 1, 1))
    style.kpi_row([("Profit this month", style.kes(mi - mo), today.strftime("%B"), mi - mo < 0),
                   ("Money received", style.kes(mi), today.strftime("%B"), False),
                   ("Money spent", style.kes(mo), today.strftime("%B"), False),
                   ("Profit this year", style.kes(yi - yo), str(today.year), yi - yo < 0)])
    st.write("")
    a, b, _ = st.columns([1, 1, 2])
    if a.button("💰 Money received", type="primary", width="stretch"):
        money_dialog(user, "Income")
    if b.button("💸 Money spent", width="stretch"):
        money_dialog(user, "Expense")
    kind = st.session_state.pop("money_kind", None)      # set by the Overview buttons
    if kind:
        money_dialog(user, kind)
    show = st.radio("Show", ["All", "Money received", "Money spent"], horizontal=True,
                    label_visibility="collapsed")
    df = db.get_records("money", fid, limit=300)
    if show != "All" and not df.empty:
        df = df[df["kind"] == ("Income" if show == "Money received" else "Expense")]
    df = df.reset_index(drop=True)
    with st.container(border=True):
        if df.empty:
            st.info("Nothing recorded yet. Use the buttons above.")
        else:
            extras.tick_table(df, "money_tbl", {"entry_date": "Date", "kind": "Type",
                              "category": "What", "description": "Note", "amount": "Amount (KES)",
                              "enterprise": "Crop or animal"},
                              lambda i: db.delete_record("money", fid, i))
 
 
# ---------- CROPS ----------
@st.dialog("Record a crop activity")
def crop_dialog(user):
    when = st.date_input("Date", date.today(), max_value=date.today())
    group = st.selectbox("Crop group", list(config.CROP_GROUPS))
    crop = st.selectbox("Crop", config.CROP_GROUPS[group])
    activity = st.selectbox("What did you do?", list(config.CROP_ACTIVITIES))
    if activity == "Harvest":
        unit, sold, home = _split_inputs(config.CROP_ACTIVITIES[activity], "Total harvested")
        quantity = sold + home
    else:
        quantity = st.number_input("How much?", min_value=0.0, step=1.0)
        unit = st.selectbox("Unit", config.CROP_ACTIVITIES[activity])
        sold = home = None
    note = st.text_input("Note (optional, e.g. rains came late)")
    if st.button("Save", type="primary", width="stretch"):
        if quantity <= 0:
            st.error("Enter an amount above 0.")
            return
        db.add_record("crop_records", user["id"], when, crop=crop, activity=activity,
                      quantity=quantity, unit=unit, note=note, sold=sold, home_use=home)
        st.toast("Saved ✓")
        st.rerun()
 
 
def crops_page(user):
    fid = user["id"]
    style.header("Crop records", "What you did on your crops, and what you harvested")
    split = extras.crop_production(fid)
    _share_cards(split, "kg")
    st.write("")
    if st.button("＋ Record a crop activity", type="primary"):
        crop_dialog(user)
    _chart(split, "kg")
    df = db.get_records("crop_records", fid, limit=300)
    with st.container(border=True):
        if df.empty:
            st.info("Nothing recorded yet. Use the button above.")
        else:
            extras.tick_table(df, "crop_tbl", {"entry_date": "Date", "crop": "Crop",
                              "activity": "Activity", "quantity": "Amount", "unit": "Unit",
                              "note": "Note", "sold": "Sold", "home_use": "Used at home"},
                              lambda i: db.delete_record("crop_records", fid, i))
 
 
# ---------- LIVESTOCK ----------
@st.dialog("Record livestock")
def livestock_dialog(user):
    when = st.date_input("Date", date.today(), max_value=date.today())
    mine = extras.animals(user["id"])["animal"].tolist()
    animal = st.selectbox("Animal", list(dict.fromkeys(mine)) or config.ANIMALS)
    activity = st.selectbox("What happened?", config.ANIMAL_ACTIVITIES[animal])
    units = config.LIVESTOCK_UNITS.get(activity, ["animals"])
    if activity in config.PRODUCTION_ACTIVITIES:
        unit, sold, home = _split_inputs(units, "Total produced")
        quantity = sold + home
    else:
        quantity = st.number_input("How many / how much?", min_value=0.0, step=1.0)
        unit = st.selectbox("Unit", units)
        sold = home = None
    note = st.text_input("Note (optional, e.g. which cow, drug used)")
    if st.button("Save", type="primary", width="stretch"):
        if quantity <= 0:
            st.error("Enter an amount above 0.")
            return
        db.add_record("livestock_records", user["id"], when, animal=animal, activity=activity,
                      quantity=quantity, unit=unit, note=note, sold=sold, home_use=home)
        st.toast("Saved ✓")
        st.rerun()
 
 
def livestock_page(user):
    fid = user["id"]
    style.header("Livestock records", "Milk, eggs, fish, health and herd changes")
    split = extras.animal_production(fid)
    _share_cards(split, "units")
    st.write("")
    if st.button("＋ Record livestock", type="primary"):
        livestock_dialog(user)
    st.caption("If you sold something, also record the money in the Money page.")
    _chart(split, "litres, eggs or kg")
    df = db.get_records("livestock_records", fid, limit=300)
    with st.container(border=True):
        if df.empty:
            st.info("Nothing recorded yet. Use the button above.")
        else:
            extras.tick_table(df, "live_tbl", {"entry_date": "Date", "animal": "Animal",
                              "activity": "What happened", "quantity": "Amount", "unit": "Unit",
                              "note": "Note", "sold": "Sold", "home_use": "Used at home"},
                              lambda i: db.delete_record("livestock_records", fid, i))
 
 
PAGES = [
    {"order": 20, "label": "🌽 Crop records", "func": crops_page,
     "roles": ("farmer",), "types": ("Crops", "Mixed")},
    {"order": 30, "label": "🐂 Livestock records", "func": livestock_page,
     "roles": ("farmer",), "types": ("Livestock", "Mixed")},
    {"order": 40, "label": "💰 Money", "func": money_page, "roles": ("farmer",)},
]
