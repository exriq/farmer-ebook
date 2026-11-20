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


def _split_inputs(units, label, price_label=None):
    """Amount sold + amount used at home (+ optional price). The total is worked out."""
    unit = st.selectbox("Unit", units)
    a, b = st.columns(2)
    sold = a.number_input("Amount SOLD", min_value=0.0, step=1.0, key="split_sold")
    home = b.number_input("Amount USED AT HOME", min_value=0.0, step=1.0, key="split_home")
    st.metric(f"{label} (calculated)", f"{sold + home:,.1f} {unit}")
    price = 0.0
    if price_label:
        price = st.number_input(f"{price_label} per {unit.rstrip('s')} (KES)", min_value=0.0,
                                step=5.0, key="split_price",
                                help="Optional. If you type a price, the sale is added to your "
                                     "Money page for you, so you do not enter it twice.")
        if price and sold:
            st.caption(f"Money received: **KES {price * sold:,.0f}** (added to Money)")
    return unit, sold, home, price


def _auto_money(fid, when, kind, category, amount, enterprise, product=None, quantity=None,
                unit=None, description=""):
    db.add_record("money", fid, when, kind=kind, category=category, description=description,
                  amount=amount, enterprise=enterprise, product=product, quantity=quantity,
                  unit=unit)


# ---------- MONEY ----------
@st.dialog("Record money", width="large")
def money_dialog(user, kind):
    fid = user["id"]
    st.markdown("**💰 Money received**" if kind == "Income" else "**💸 Money spent**")
    when = st.date_input("Date", date.today(), max_value=date.today(), format="DD/MM/YYYY")
    names = extras.enterprise_names(fid)
    whole = "Whole farm (not one crop or animal)"
    which = st.selectbox("1. Which crop or animal is this about?" if kind == "Income"
                         else "1. Which crop or animal was this spent on?", [whole] + names)
    enterprise = None if which == whole else which
    note = ""
    if kind == "Income" and enterprise:
        options = extras.products_of(fid, enterprise)
        if enterprise in config.ANIMALS:
            options = options + [config.LIVE_SALE]
        product = st.selectbox("2. Which product did you sell?", options)
        category = config.income_category(enterprise, product)
        sold_ids = []
        if product == config.LIVE_SALE:
            herd = extras.animals(fid)
            herd = herd[(herd["animal"] == enterprise) & (herd["entry_type"] == "single")]
            labels = {int(r.id): extras.animal_label(r) for r in herd.itertuples()}
            if labels:
                sold_ids = st.multiselect("Which tagged animal(s) were sold? (they leave your "
                                          "farm list)", list(labels), format_func=labels.get)
        units = config.units_for(product)
        a, b = st.columns(2)
        quantity = a.number_input("3. How many did you sell?", min_value=0.0, step=1.0,
                                  value=float(len(sold_ids)) or 0.0, key=f"mq_{len(sold_ids)}")
        unit = b.selectbox("Unit", units)
        price = st.number_input(f"4. Price for one {unit.rstrip('s')} (KES)", min_value=0.0, step=10.0)
        amount = quantity * price
        st.metric("Total money received", style.kes(amount))
        buyer = st.text_input("5. Who bought it? (optional)")
        note = st.text_input("6. Note (optional)")
        st.caption(f"This will show in your reports as: **{category}  ·  {product}**")
        description = " · ".join(x for x in ([f"Buyer: {buyer}"] if buyer else []) + ([note] if note else []))
        if sold_ids:
            description = ", ".join(labels[i] for i in sold_ids) + (" · " + description if description else "")
    else:
        product = quantity = unit = None
        cats = config.INCOME_CATEGORIES if kind == "Income" else config.EXPENSE_CATEGORIES
        category = st.selectbox("2. What was it for?" if kind == "Expense" else "2. What kind of income?", cats)
        amount = st.number_input("3. Amount (KES)", min_value=0.0, step=50.0)
        description = st.text_input("4. Note (optional)")
        sold_ids = []
    if st.button("Save", type="primary", width="stretch"):
        if amount <= 0:
            st.error("Enter the amount (quantity and price) above 0.")
            return
        db.add_record("money", fid, when, kind=kind, category=category, description=description,
                      amount=amount, enterprise=enterprise, product=product,
                      quantity=quantity or None, unit=unit)
        for i in sold_ids:
            extras.apply_event(fid, int(i), "Sold", 1, when)
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
    allm = db.get_records("money", fid)
    sales = allm[allm["kind"] == "Income"].copy() if not allm.empty else allm
    if not sales.empty:
        sales["product"] = sales["product"].fillna(sales["category"])
        sales["enterprise"] = sales["enterprise"].fillna("Whole farm")
        sales["unit"] = sales["unit"].fillna("")
        sales["quantity"] = sales["quantity"].fillna(0)
        by = (sales.groupby(["enterprise", "product", "unit"], as_index=False)
              .agg(quantity=("quantity", "sum"), amount=("amount", "sum"))
              .sort_values("amount", ascending=False))
        by["Quantity sold"] = [f"{q:,.0f} {u}" if q else "" for q, u in zip(by["quantity"], by["unit"])]
        by["Average price"] = [f"KES {a / q:,.0f} per {u.rstrip('s')}" if q and u else ""
                               for a, q, u in zip(by["amount"], by["quantity"], by["unit"])]
        with st.container(border=True):
            st.subheader("💰 Money received, by product")
            st.bar_chart(by.assign(Product=by["enterprise"] + " – " + by["product"])
                         .set_index("Product")["amount"], color="#1E6B47")
            st.dataframe(by.rename(columns={"enterprise": "Crop or animal", "product": "Product",
                                            "amount": "Money received (KES)"})
                         [["Crop or animal", "Product", "Quantity sold", "Average price",
                           "Money received (KES)"]], hide_index=True, width="stretch")
    df = db.get_records("money", fid, limit=300)
    if show != "All" and not df.empty:
        df = df[df["kind"] == ("Income" if show == "Money received" else "Expense")]
    df = df.reset_index(drop=True)
    with st.container(border=True):
        if df.empty:
            st.info("Nothing recorded yet. Use the buttons above.")
        else:
            df = df[["id", "entry_date", "kind", "enterprise", "product", "category", "quantity",
                     "unit", "amount", "description"]]
            extras.tick_table(df, "money_tbl", {"entry_date": "Date", "kind": "Type",
                              "enterprise": "Crop or animal", "product": "Product",
                              "category": "What", "quantity": "Quantity", "unit": "Unit",
                              "amount": "Amount (KES)", "description": "Note"},
                              lambda i: db.delete_record("money", fid, i))


# ---------- CROPS ----------
@st.dialog("Record a crop activity", width="large")
def crop_dialog(user):
    fid = user["id"]
    mine = extras.crops(fid)
    if mine.empty:
        st.info("You have not added a crop yet. Go to **My Farm → Add a crop** first.")
        return
    labels = {int(r.id): extras.crop_label(r) for r in mine.itertuples()}
    cid = st.selectbox("1. Which crop is this about?", list(labels), format_func=labels.get)
    row = mine[mine["id"] == cid].iloc[0]
    when = st.date_input("2. Date", date.today(), max_value=date.today(), format="DD/MM/YYYY")
    activity = st.selectbox("3. What did you do?", list(config.CROP_ACTIVITIES),
                            format_func=lambda a: config.CROP_ACTIVITY_INFO[a][0])
    st.info(config.CROP_ACTIVITY_INFO[activity][1])
    detail, cost, sold, home, price, product = [], 0.0, None, None, 0.0, None
    if activity == "Harvest":
        product = st.selectbox("Which product did you harvest?", extras.products_of(fid, row["crop"]))
        unit, sold, home, price = _split_inputs(config.CROP_ACTIVITIES[activity], "Total harvested",
                                                "Price")
        quantity = sold + home
    else:
        if activity == "Land preparation":
            quantity = st.number_input("Acres prepared", min_value=0.0, step=0.25)
            unit = "acres"
            detail.append("Method: " + st.selectbox("How was it done?", config.LAND_PREP_METHODS))
        elif activity == "Planting":
            quantity = st.number_input("Acres planted", min_value=0.0, step=0.25)
            unit = "acres"
            seed = st.number_input("Seed used (kg, optional)", min_value=0.0, step=1.0)
            if seed:
                detail.append(f"Seed: {seed:g} kg")
        elif activity == "Fertilizer applied":
            detail.append("Type: " + st.selectbox("Which fertilizer?", config.FERTILIZER_TYPES))
            quantity = st.number_input("How much?", min_value=0.0, step=1.0)
            unit = st.selectbox("Unit", config.CROP_ACTIVITIES[activity])
        elif activity == "Spraying":
            what = st.text_input("What did you spray? (product name, optional)")
            if what:
                detail.append(f"Product: {what}")
            detail.append("Against: " + st.selectbox("What was it for?", config.SPRAY_TARGETS))
            quantity = st.number_input("How much did you spray?", min_value=0.0, step=1.0)
            unit = st.selectbox("Unit", config.CROP_ACTIVITIES[activity])
        else:                                           # Weeding
            quantity = st.number_input("Acres weeded", min_value=0.0, step=0.25)
            unit = "acres"
            detail.append("Method: " + st.selectbox("How was it done?", config.WEEDING_METHODS))
        cost = st.number_input("What did it cost you? (KES, optional)", min_value=0.0, step=50.0,
                               help="If you type a cost, it is added to your Money page for you.")
    note = st.text_input("Note (optional, e.g. rains came late)")
    if st.button("Save", type="primary", width="stretch"):
        if quantity <= 0:
            st.error("Enter an amount above 0.")
            return
        db.add_record("crop_records", fid, when, crop=row["crop"], crop_id=int(cid),
                      activity=activity, quantity=quantity, unit=unit, note=note, sold=sold,
                      home_use=home, product=product, detail=" · ".join(detail) or None,
                      cost=cost or None)
        if cost:
            _auto_money(fid, when, "Expense", config.CROP_COST_CATEGORY[activity], cost,
                        row["crop"], description=f"{activity}: {labels[cid]}")
        if activity == "Harvest" and sold and price:
            _auto_money(fid, when, "Income", config.income_category(row["crop"], product),
                        price * sold, row["crop"], product, sold, unit, labels[cid])
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
            df = df[["id", "entry_date", "crop", "activity", "product", "quantity", "unit",
                     "sold", "home_use", "detail", "cost", "note"]]
            extras.tick_table(df, "crop_tbl", {"entry_date": "Date", "crop": "Crop",
                              "activity": "Activity", "product": "Product", "quantity": "Amount",
                              "unit": "Unit", "sold": "Sold", "home_use": "Used at home",
                              "detail": "Details", "cost": "Cost (KES)", "note": "Note"},
                              lambda i: db.delete_record("crop_records", fid, i))


# ---------- LIVESTOCK ----------
@st.dialog("Record livestock", width="large")
def livestock_dialog(user):
    fid = user["id"]
    herd = extras.animals(fid)
    if herd.empty:
        st.info("You have not added animals yet. Go to **My Farm → Add animals or fish** first.")
        return
    labels = {int(r.id): extras.animal_label(r) for r in herd.itertuples()}
    aid = st.selectbox("1. Which animal or group is this about?", list(labels), format_func=labels.get)
    r = herd[herd["id"] == aid].iloc[0]
    species, single, fish = r["animal"], r["entry_type"] == "single", r["animal"] == "Fish"
    group_size = int(r["head_count"])
    when = st.date_input("2. Date", date.today(), max_value=date.today(), format="DD/MM/YYYY")
    activity = st.selectbox("3. What happened?", config.ANIMAL_ACTIVITIES[species],
                            format_func=lambda a: config.ACTIVITY_INFO[a][0])
    st.info(config.ACTIVITY_INFO[activity][1])
    fields = config.ACTIVITY_FIELDS[activity]
    quantity, unit, sold, home, price, cost, weight = None, "animals", None, None, 0.0, 0.0, None
    detail = []
    if "split" in fields:
        unit, sold, home, price = _split_inputs(config.LIVESTOCK_UNITS[activity], "Total produced",
                                                "Price")
        quantity = sold + home
        if "fish_count" in fields:
            n = st.number_input("How many fish? (optional)", min_value=0, step=1)
            if n:
                detail.append(f"Fish: {n}")
    if "weight" in fields:
        weight = st.number_input("Weight (kg)", min_value=0.0, step=1.0)
        quantity, unit = weight, "kg"
    if "born" in fields:
        quantity = st.number_input("Number born ALIVE", min_value=0, step=1, value=1)
        dead = st.number_input("Number born DEAD (if any)", min_value=0, step=1)
        if dead:
            detail.append(f"Born dead: {dead}")
        if single:
            st.caption("To keep a baby, add it as its own animal in My Farm.")
    if "count" in fields:
        if single:
            st.caption("Number of animals: 1 (this animal)")
            quantity = 1
        else:
            limit = group_size if activity in ("Died", "Sold") and not fish else None
            quantity = st.number_input("How many?" if not fish else "How many fingerlings or fish?",
                                       min_value=1, max_value=limit, step=1, value=1)
        if fish:
            unit = "fingerlings" if activity == "Stocked fingerlings" else "fish"
    if "feed" in fields:
        quantity, unit = st.number_input("Feed given (kg)", min_value=0.0, step=1.0), "kg"
    if "service" in fields:
        st.caption("This records one service.")
        quantity = 1
        used = st.text_input("Bull, buck or semen used (name or breed)")
        if used:
            detail.append(f"Used: {used}")
    if "illness" in fields:
        ill = st.text_input("What was wrong? (signs or disease)")
        if ill:
            detail.append(f"Illness: {ill}")
    if "medicine" in fields:
        med = st.text_input("Drug, vaccine or product used")
        if med:
            detail.append(f"Product: {med}")
    if "cause" in fields:
        detail.append("Cause: " + st.selectbox("Cause of death", config.DEATH_CAUSES))
    if "price" in fields:
        price_total = st.number_input("Total money you received (KES)", min_value=0.0, step=100.0,
                                      help="If you type it, the sale is added to your Money page for you.")
    else:
        price_total = 0.0
    if "cost" in fields:
        cost = st.number_input("What did it cost you? (KES, optional)", min_value=0.0, step=50.0,
                               help="If you type a cost, it is added to your Money page for you.")
    note = st.text_input("Note (optional)")
    if st.button("Save", type="primary", width="stretch"):
        if not quantity or quantity <= 0:
            st.error("Enter an amount above 0.")
            return
        db.add_record("livestock_records", fid, when, animal=species, animal_id=int(aid),
                      subject=labels[aid], activity=activity, quantity=quantity, unit=unit,
                      note=note, sold=sold, home_use=home, detail=" · ".join(detail) or None,
                      cost=cost or None)
        extras.apply_event(fid, int(aid), activity, int(quantity) if unit != "kg" else 0, when,
                           weight)
        if cost:
            _auto_money(fid, when, "Expense", config.LIVESTOCK_COST_CATEGORY[activity], cost,
                        species, description=f"{activity}: {labels[aid]}")
        if activity == "Sold" and price_total:
            _auto_money(fid, when, "Income", "Livestock sales", price_total, species,
                        config.LIVE_SALE, quantity, "animals", labels[aid])
        if activity in config.PRODUCTION_ACTIVITIES and sold and price:
            product = config.PRODUCT_OF_ACTIVITY[activity]
            _auto_money(fid, when, "Income", config.income_category(species, product), price * sold,
                        species, product, sold, unit, labels[aid])
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
    st.caption("Type a price when you record a sale here and it is added to Money for you.")
    _chart(split, "litres, eggs or kg")
    df = db.get_records("livestock_records", fid, limit=300)
    with st.container(border=True):
        if df.empty:
            st.info("Nothing recorded yet. Use the button above.")
        else:
            df = df[["id", "entry_date", "subject", "activity", "quantity", "unit", "sold",
                     "home_use", "detail", "cost", "note"]]
            extras.tick_table(df, "live_tbl", {"entry_date": "Date", "subject": "Animal or group",
                              "activity": "What happened", "quantity": "Amount", "unit": "Unit",
                              "sold": "Sold", "home_use": "Used at home", "detail": "Details",
                              "cost": "Cost (KES)", "note": "Note"},
                              lambda i: db.delete_record("livestock_records", fid, i))


PAGES = [
    {"order": 20, "label": "🌽 Crop records", "func": crops_page,
     "roles": ("farmer",), "types": ("Crops", "Mixed")},
    {"order": 30, "label": "🐂 Livestock records", "func": livestock_page,
     "roles": ("farmer",), "types": ("Livestock", "Mixed")},
    {"order": 40, "label": "💰 Money", "func": money_page, "roles": ("farmer",)},
]
