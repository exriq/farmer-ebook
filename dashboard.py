"""My Dashboard: produce, cash flow, inputs and labour.
When market_info.py is installed (Phase 3) it also shows market prices and
opportunities."""
import importlib.util
from datetime import date

import pandas as pd
import streamlit as st

import config
import db
from inputs_labour import stock_table


def to_kg(quantity, unit):
    return quantity * config.UNIT_TO_KG.get(unit, 1)


# ---------- PRODUCE ----------
def crop_produce(user, prof):
    st.subheader("🌽 Crops: harvested compared with what your farm could give")
    records = db.get_records("crop_records", user["id"])
    harvest = records[records["activity"] == "Harvest"].copy()
    seasons = {config.season_label(date.today())}
    got = {}
    if not harvest.empty:
        harvest["kg"] = [to_kg(q, u) for q, u in zip(harvest["quantity"], harvest["unit"])]
        harvest["season"] = [config.season_label(d) for d in harvest["entry_date"]]
        seasons |= set(harvest["season"])
    season = st.selectbox("Season", sorted(seasons, reverse=True), key="crop_season")
    if not harvest.empty:
        got = harvest[harvest["season"] == season].groupby("crop")["kg"].sum().to_dict()

    mine = db.get_farmer_crops(user["id"])
    reference = db.get_yield_reference().set_index("crop")["kg_per_acre"].to_dict()
    fertility = config.FERTILITY.get(prof["fertility"], 0.85)
    rainfall = config.RAINFALL.get(prof["rainfall"], 0.85)
    acres = dict(zip(mine["crop"], mine["acres"]))
    crops = list(dict.fromkeys(list(mine["crop"]) + list(got)))
    if not crops:
        st.info("List your crops in My Farm and record harvests in Crop records "
                "to see this summary.")
        return
    rows, missing = [], []
    for crop in crops:
        crop_acres, best = acres.get(crop), reference.get(crop)
        possible = crop_acres * best * fertility * rainfall if crop_acres and best else None
        if crop_acres and not best:
            missing.append(crop)
        current = got.get(crop, 0.0)
        rows.append({
            "Crop": crop, "Acres": crop_acres,
            "Harvested (kg)": round(current),
            "Possible (kg)": round(possible) if possible else None,
            "% of possible": round(100 * current / possible) if possible else None})
    table = pd.DataFrame(rows)
    st.dataframe(table, width="stretch", hide_index=True)
    chart = table.dropna(subset=["Possible (kg)"]).set_index("Crop")[
        ["Harvested (kg)", "Possible (kg)"]]
    if not chart.empty:
        st.bar_chart(chart, color=["#2E7D32", "#D4A017"])
    st.caption("'Possible' is an estimate for one season: acres x a reference yield x a "
               "soil fertility factor x a rainfall factor. Use it as a guide, not a "
               "promise.")
    if missing:
        st.caption("No reference yield yet for: " + ", ".join(missing))


def livestock_produce(user):
    st.subheader("🐂 Animals and animal produce")
    herd = db.get_farm_animals(user["id"])
    if herd.empty:
        st.info("List your animals in My Farm to see them here.")
    else:
        st.dataframe(herd.groupby("animal", as_index=False)["head_count"].sum().rename(
            columns={"animal": "Animal", "head_count": "Number"}),
            width="stretch", hide_index=True)
    records = db.get_records("livestock_records", user["id"])
    produce = records[records["activity"].isin(config.PRODUCTION_ACTIVITIES)].copy()
    seasons = {config.season_label(date.today())}
    if not produce.empty:
        produce["season"] = [config.season_label(d) for d in produce["entry_date"]]
        seasons |= set(produce["season"])
    season = st.selectbox("Season", sorted(seasons, reverse=True), key="live_season")
    if produce.empty:
        st.info("Record milk, eggs or fish catch in Livestock records to see totals.")
        return
    this = produce[produce["season"] == season]
    totals = this.groupby(["animal", "activity", "unit"], as_index=False)["quantity"].sum()
    st.dataframe(totals.rename(columns={
        "animal": "Animal", "activity": "Produce", "unit": "Unit",
        "quantity": "Total"}), width="stretch", hide_index=True)

    rows = []
    for (animal, activity), (unit, per_year) in config.ANIMAL_POTENTIAL_PER_YEAR.items():
        count = herd.loc[herd["animal"] == animal, "head_count"].sum() if not herd.empty else 0
        if count <= 0:
            continue
        mine = this[(this["animal"] == animal) & (this["activity"] == activity)]
        current = sum(q * (30 if u == "trays" else 1)
                      for q, u in zip(mine["quantity"], mine["unit"]))
        possible = count * per_year / 2
        rows.append({"Produce": f"{activity} ({unit})", "Animals": int(count),
                     "Produced": round(current), "Possible": round(possible),
                     "% of possible": round(100 * current / possible)})
    if rows:
        st.write("**Produced compared with what your animals could give this season**")
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.caption("Possible = animals x a typical yearly yield, halved for one season. "
                   "It is only an estimate.")


def produce_section(user):
    prof = db.get_farm_profile(user["id"])
    if user["farming_type"] in ("Crops", "Mixed"):
        crop_produce(user, prof)
    if user["farming_type"] in ("Livestock", "Mixed"):
        livestock_produce(user)


# ---------- MONEY ----------
def cash_section(user):
    st.subheader("💰 Cash coming in and going out")
    money = db.get_records("money", user["id"])
    if money.empty:
        st.info("Record income and expenses in the Money page to see this summary.")
        return
    period = st.selectbox("Show my money by", config.PERIODS, index=1, key="cash_period")
    money["Period"] = [config.period_label(d, period) for d in money["entry_date"]]
    pivot = money.pivot_table(index="Period", columns="kind", values="amount",
                              aggfunc="sum", fill_value=0)
    for column in ("Income", "Expense"):
        if column not in pivot.columns:
            pivot[column] = 0.0
    pivot = pivot[["Income", "Expense"]].sort_index()
    pivot["Profit / loss"] = pivot["Income"] - pivot["Expense"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total income", f"KES {pivot['Income'].sum():,.0f}")
    c2.metric("Total expenses", f"KES {pivot['Expense'].sum():,.0f}")
    c3.metric("Profit / loss", f"KES {pivot['Profit / loss'].sum():,.0f}")
    st.bar_chart(pivot[["Income", "Expense"]], color=["#2E7D32", "#B5651D"])
    st.dataframe(pivot.round(0).reset_index(), width="stretch", hide_index=True)
    spend = money[money["kind"] == "Expense"]
    if not spend.empty:
        st.write("**Where the money goes**")
        st.bar_chart(spend.groupby("category")["amount"].sum(), color="#B5651D")
    sales = money[money["kind"] == "Income"].copy()
    if not sales.empty:
        sales["product"] = sales["product"].fillna(sales["category"])
        sales["enterprise"] = sales["enterprise"].fillna("Whole farm")
        st.write("**Where my income comes from (by product)**")
        by = sales.groupby(["enterprise", "product"], as_index=False)["amount"].sum()
        by["Product"] = by["enterprise"] + " – " + by["product"]
        st.bar_chart(by.set_index("Product")["amount"], color="#2E7D32")


# ---------- INPUTS AND LABOUR ----------
def inputs_section(user):
    st.subheader("🧺 Inputs in store")
    moves = db.get_records("inventory_moves", user["id"])
    if moves.empty:
        st.info("Record inputs in the Inputs and stock page to see your store here.")
    else:
        st.dataframe(stock_table(moves), width="stretch", hide_index=True)
        bought = moves[moves["movement"] == "Bought"]
        if not bought.empty:
            st.metric("Total spent on inputs", f"KES {bought['cost'].sum():,.0f}")
            st.bar_chart(bought.groupby("category")["cost"].sum(), color="#B5651D")
    st.subheader("👷 Labour")
    labour = db.get_records("labour", user["id"])
    if labour.empty:
        st.info("Record work in the Labour page to see this summary.")
        return
    by_type = labour.groupby("worker_type", as_index=False)[["people_days", "cost"]].sum()
    st.dataframe(by_type.rename(columns={
        "worker_type": "Who", "people_days": "Person-days", "cost": "Paid (KES)"}),
        width="stretch", hide_index=True)
    by_work = labour.groupby("activity")["people_days"].sum()
    st.write("**Person-days by type of work**")
    st.bar_chart(by_work, color="#2E7D32")


# ---------- THE PAGE ----------
def dashboard_page(user):
    st.header("📊 My Dashboard")
    prof = db.get_farm_profile(user["id"])
    land = db.get_land(user["id"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total land", f"{sum(land.values()):,.1f} acres")
    c2.metric("In active use", f"{prof['active_acres']:,.1f} acres")
    c3.metric("Farm scale", config.scale_for(prof["active_acres"]))
    c4.metric("Farming type", user["farming_type"])
    if sum(land.values()) == 0:
        st.info("Open My Farm and fill in your land details to get the most from "
                "this dashboard.")

    sections = ["Produce", "Cash flow", "Inputs and labour"]
    has_market = importlib.util.find_spec("market_info") is not None
    if has_market:
        sections.append("Market and opportunities")
    section = st.radio("Show", sections, horizontal=True, key="dash_section")
    if section == "Produce":
        produce_section(user)
    elif section == "Cash flow":
        cash_section(user)
    elif section == "Inputs and labour":
        inputs_section(user)
    else:
        import market_info
        market_info.dashboard_section(user)


PAGES = [
    {"order": 5, "label": "📊 My Dashboard", "func": dashboard_page,
     "roles": ("farmer",)},
]
