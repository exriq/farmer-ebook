"""Overview: the first screen. Each level of access sees its own version."""
from datetime import date
 
import pandas as pd
import streamlit as st
 
import chat
import db
import style
 
 
def go(label, **state):
    st.session_state.menu_choice = label
    st.session_state.update(state)
 
 
def farmer_view(user):
    today = date.today()
    df = db.table("SELECT entry_date, kind, amount FROM money WHERE farmer_id = %s "
                  "AND entry_date >= %s", (user["id"], date(today.year - 1, today.month, 1)))
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["month"] = df["entry_date"].dt.to_period("M")
    inc, exp = df[df.kind == "Income"], df[df.kind == "Expense"]
 
    def total(d, start):
        return float(d[d.entry_date >= pd.Timestamp(start)].amount.sum())
 
    ms, ys = date(today.year, today.month, 1), date(today.year, 1, 1)
    mi, mo, yi, yo = total(inc, ms), total(exp, ms), total(inc, ys), total(exp, ys)
    style.kpi_row([("Profit this month", style.kes(mi - mo), today.strftime("%B"), mi - mo < 0),
                   ("Money received", style.kes(mi), today.strftime("%B"), False),
                   ("Money spent", style.kes(mo), today.strftime("%B"), False),
                   ("Profit this year", style.kes(yi - yo), str(today.year), yi - yo < 0)])
    st.write("")
    a, b, c = st.columns(3)
    a.button("💸 I spent money", use_container_width=True, on_click=go, args=("💰 Money",),
             kwargs={"money_kind": "Expense"})
    b.button("💰 I received money", use_container_width=True, on_click=go, args=("💰 Money",),
             kwargs={"money_kind": "Income"})
    c.button("🏡 My farm", use_container_width=True, on_click=go, args=("🏡 My Farm",))
    months = pd.period_range(end=pd.Period(today, "M"), periods=12, freq="M")
    chart = pd.DataFrame({
        "Received": inc.groupby("month").amount.sum().reindex(months, fill_value=0).values,
        "Spent": exp.groupby("month").amount.sum().reindex(months, fill_value=0).values},
        index=[m.strftime("%b") for m in months])
    with st.container(border=True):
        st.subheader("Money received and spent, last 12 months")
        st.bar_chart(chart, color=["#1E6B47", "#B3352A"])
    with st.container(border=True):
        st.subheader("Latest money records")
        recent = db.get_records("money", user["id"], limit=6)
        st.dataframe(recent.drop(columns=["id"]), hide_index=True) if len(recent) else \
            st.info("Nothing recorded yet. Use the buttons above.")
 
 
def coordinator_view(user):
    f = db.table("SELECT name, ward, village, farming_type, created_at FROM farmers "
                 "WHERE role = 'farmer' AND sub_county = %s ORDER BY created_at DESC",
                 (user["sub_county"],))
    new = int((pd.to_datetime(f.created_at, utc=True) >=
               pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=30)).sum()) if len(f) else 0
    style.kpi_row([("Farmers in my sub-county", len(f), user["sub_county"], False),
                   ("Joined in the last 30 days", new, "new farmers", False),
                   ("Crop farmers", int((f.farming_type == "Crops").sum()), "", False),
                   ("Livestock and mixed", int((f.farming_type != "Crops").sum()), "", False)])
    st.write("")
    if len(f):
        with st.container(border=True):
            st.subheader("Farmers by ward")
            st.bar_chart(f.groupby("ward").size(), color="#1E6B47")
        with st.container(border=True):
            st.subheader("Newest farmers")
            st.dataframe(f.drop(columns=["created_at"]).head(8), hide_index=True)
    else:
        st.info("No farmers have registered in your sub-county yet.")
 
 
def agrovet_view(user):
    reach = int(db.rows("SELECT COUNT(*) FROM farmers WHERE role = 'farmer' AND active "
                        "AND in_directory")[0][0])
    style.kpi_row([("New messages", chat.unread_count(user["id"]), "waiting for you", False),
                   ("Farmers you can reach", reach, "listed in the directory", False)])
    st.write("")
    with st.container(border=True):
        st.subheader("Your shop window")
        st.write("Post your products in the **Marketplace**, check **Input prices**, and "
                 "answer farmers in **Messages**.")
 
 
def admin_view(user):
    counts = dict(db.rows("SELECT role, COUNT(*) FROM farmers GROUP BY role"))
    style.kpi_row([("Farmers", counts.get("farmer", 0), "", False),
                   ("Coordinators", counts.get("coordinator", 0), "", False),
                   ("Agrovets", counts.get("agrovet", 0), "", False),
                   ("Administrators", counts.get("admin", 0), "", False)])
    st.write("")
    req = db.table("SELECT name, phone, sub_county, requested_role FROM farmers WHERE "
                   "role = 'farmer' AND requested_role IN ('coordinator', 'agrovet') ORDER BY id")
    with st.container(border=True):
        st.subheader("Access requests waiting for you")
        if req.empty:
            st.caption("No requests waiting.")
        for r in req.itertuples():
            a, b, c = st.columns([4, 1, 1])
            a.write(f"**{r.name}** wants **{r.requested_role}** access  ·  {r.sub_county}")
            if b.button("Approve", key=f"ok_{r.phone}"):
                db.set_role(r.phone, r.requested_role,
                            r.sub_county if r.requested_role == "coordinator" else None)
                st.rerun()
            if c.button("Decline", key=f"no_{r.phone}"):
                db.run("UPDATE farmers SET requested_role = NULL WHERE phone = %s", (r.phone,))
                st.rerun()
 
 
def overview(user):
    role = user["role"]
    style.header(f"Welcome, {user['name'].split()[0]}",
                 {"farmer": "Your farm at a glance", "coordinator": "Your sub-county at a glance",
                  "agrovet": "Your business at a glance", "admin": "The whole platform"}[role])
    if user.get("pending"):
        st.warning(f"Your request for **{user['pending']}** access is waiting for the "
                   "administrator. Until it is approved you can use Overview and Messages.")
        return
    {"farmer": farmer_view, "coordinator": coordinator_view, "agrovet": agrovet_view,
     "admin": admin_view}[role](user)
 
 
PAGES = [{"order": 5, "label": "🏠 Overview", "func": overview,
          "roles": ("farmer", "coordinator", "agrovet", "admin")}]
