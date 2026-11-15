"""Market prices, farm input prices and opportunities.
Farmers read these pages. Coordinators fill them in (see staff.py)."""
from datetime import date
 
import pandas as pd
import streamlit as st
 
import config
import db
 
ALL_ROLES = ("farmer", "coordinator", "admin")
 
 
def pick_sub_county(user, key):
    options = [config.ALL_SUB_COUNTIES] + config.SUB_COUNTIES
    default = options.index(user["sub_county"]) if user["sub_county"] in options else 0
    choice = st.selectbox("Sub-county", options, index=default, key=key)
    return None if choice == config.ALL_SUB_COUNTIES else choice
 
 
def _outlook(change):
    if pd.isna(change):
        return "No earlier data"
    if change > 5:
        return "Rising"
    if change < -5:
        return "Falling"
    return "Steady"
 
 
def _demand_word(score):
    return "High" if score >= 2.5 else "Medium" if score >= 1.5 else "Low"
 
 
def best_products(prices):
    """Rank products by demand first, then by how the price is moving."""
    if prices.empty:
        return pd.DataFrame()
    df = prices.copy()
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["score"] = df["demand"].map(config.DEMAND_SCORE)
    today = pd.Timestamp(date.today())
    recent = df[df["entry_date"] >= today - pd.Timedelta(days=30)]
    earlier = df[(df["entry_date"] < today - pd.Timedelta(days=30))
                 & (df["entry_date"] >= today - pd.Timedelta(days=60))]
    if recent.empty:
        return pd.DataFrame()
    now = recent.groupby(["product", "unit"]).agg(
        avg_price=("price", "mean"), demand_score=("score", "mean"),
        reports=("price", "count")).reset_index()
    before = earlier.groupby(["product", "unit"])["price"].mean().rename(
        "earlier_price").reset_index()
    out = now.merge(before, on=["product", "unit"], how="left")
    out["change"] = (out["avg_price"] / out["earlier_price"] - 1) * 100
    out = out.sort_values(["demand_score", "change"], ascending=[False, False],
                          na_position="last")
    out["Demand"] = out["demand_score"].apply(_demand_word)
    out["Price outlook"] = out["change"].apply(_outlook)
    out["Avg price (KES)"] = out["avg_price"].round(0)
    return out.rename(columns={"product": "Product", "unit": "Unit",
                               "reports": "Reports"})[
        ["Product", "Unit", "Avg price (KES)", "Demand", "Price outlook", "Reports"]]
 
 
BEST_NOTE = ("Ranked by demand first, then by whether the price is rising. Based on "
             "reports from the last 30 days compared with the 30 days before.")
 
 
def market_prices_page(user):
    st.header("📈 Market prices")
    sub = pick_sub_county(user, "mp_sub")
    prices = db.get_market_prices(sub)
    if prices.empty:
        st.info("No market prices have been uploaded yet. Your sub-county "
                "coordinator will add them.")
        return
    prices["market"] = prices["market"].fillna("Unnamed market")
    prices["item"] = prices["product"] + " (" + prices["unit"] + ")"
 
    st.subheader("Best performing products")
    best = best_products(prices)
    if best.empty:
        st.info("There are no price reports from the last 30 days yet.")
    else:
        st.dataframe(best, width="stretch", hide_index=True)
        st.caption(BEST_NOTE)
 
    st.subheader("Price over time")
    item = st.selectbox("Product", sorted(prices["item"].unique()), key="mp_item")
    one = prices[prices["item"] == item].copy()
    one["entry_date"] = pd.to_datetime(one["entry_date"])
    series = one.pivot_table(index="entry_date", columns="market", values="price",
                             aggfunc="mean").sort_index()
    st.line_chart(series)
 
    st.subheader("Latest prices")
    latest = prices.sort_values("entry_date").groupby(["market", "item"]).tail(1)
    st.dataframe(latest[["entry_date", "sub_county", "ward", "market", "item",
                         "price", "demand"]].rename(columns={
        "entry_date": "Date", "sub_county": "Sub-county", "ward": "Ward",
        "market": "Market", "item": "Product", "price": "Price (KES)",
        "demand": "Demand"}).sort_values("Product"), width="stretch", hide_index=True)
 
 
def input_prices_page(user):
    st.header("🛒 Farm input prices")
    sub = pick_sub_county(user, "ip_sub")
    prices = db.get_input_prices(sub)
    if prices.empty:
        st.info("No input prices have been uploaded yet. Your sub-county "
                "coordinator will add them.")
        return
    prices["item_unit"] = prices["item"] + " (" + prices["unit"] + ")"
    st.subheader("Latest prices at agrovets")
    latest = prices.sort_values("entry_date").groupby(["agrovet", "item_unit"]).tail(1)
    st.dataframe(latest[["entry_date", "sub_county", "agrovet", "item_unit", "price"]]
                 .rename(columns={"entry_date": "Date", "sub_county": "Sub-county",
                                  "agrovet": "Agrovet", "item_unit": "Item",
                                  "price": "Price (KES)"}).sort_values("Item"),
                 width="stretch", hide_index=True)
    st.subheader("Price over time")
    item = st.selectbox("Item", sorted(prices["item_unit"].unique()), key="ip_item")
    one = prices[prices["item_unit"] == item].copy()
    one["entry_date"] = pd.to_datetime(one["entry_date"])
    series = one.pivot_table(index="entry_date", columns="agrovet", values="price",
                             aggfunc="mean").sort_index()
    st.line_chart(series)
 
 
def show_opportunities(df):
    for r in df.itertuples():
        with st.container(border=True):
            st.markdown(f"**{r.title}**")
            who = " - ".join(x for x in [r.kind, r.provider] if x)
            st.caption(who)
            if r.deadline is not None and not pd.isna(r.deadline):
                st.write(f"Deadline: {r.deadline}")
            if r.details:
                st.write(r.details)
            if r.contact:
                st.write(f"How to apply or contact: {r.contact}")
            st.caption(f"For: {r.sub_county}")
 
 
def opportunities_page(user):
    st.header("🎯 Opportunities")
    st.caption("Government and non-government programmes you may benefit from.")
    sub = pick_sub_county(user, "op_sub")
    df = db.get_opportunities(sub)
    if df.empty:
        st.info("No opportunities are open right now. Check again soon.")
    else:
        show_opportunities(df)
 
 
def dashboard_section(user):
    """Shown inside the farmer dashboard."""
    st.subheader(f"Top products in {user['sub_county']}")
    best = best_products(db.get_market_prices(user["sub_county"]))
    if best.empty:
        st.info("No recent market reports for your sub-county yet.")
    else:
        st.dataframe(best.head(5), width="stretch", hide_index=True)
        st.caption(BEST_NOTE + " See Market prices for the full list.")
    st.subheader("Opportunities for you")
    ops = db.get_opportunities(user["sub_county"]).head(3)
    if ops.empty:
        st.info("No opportunities are open right now.")
    else:
        show_opportunities(ops)
 
 
PAGES = [
    {"order": 70, "label": "📈 Market prices", "func": market_prices_page,
     "roles": ALL_ROLES},
    {"order": 75, "label": "🛒 Input prices", "func": input_prices_page,
     "roles": ALL_ROLES},
    {"order": 80, "label": "🎯 Opportunities", "func": opportunities_page,
     "roles": ALL_ROLES},
]
