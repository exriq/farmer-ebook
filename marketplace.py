"""Marketplace (buy and sell) and the farmer directory."""
import streamlit as st
 
import config
import db
 
ALL_ROLES = ("farmer", "coordinator", "admin")
 
 
def go_to_messages(partner_id):
    """Button action: open the Messages page with this person selected."""
    st.session_state["chat_with"] = int(partner_id)
    st.session_state["menu_choice"] = "💬 Messages"
 
 
def _text(value):
    return "" if value is None or (isinstance(value, float) and value != value) else value
 
 
# ---------- MARKETPLACE ----------
def browse_tab(user):
    left, right = st.columns(2)
    with left:
        sub = st.selectbox("Sub-county", [config.ALL_SUB_COUNTIES] + config.SUB_COUNTIES,
                           key="mk_sub")
    with right:
        search = st.text_input("Search for a product (e.g. maize, milk)", key="mk_search")
    df = db.get_listings(None if sub == config.ALL_SUB_COUNTIES else sub,
                         search.strip() or None)
    if df.empty:
        st.info("No listings match. Be the first to post one.")
        return
    for r in df.itertuples():
        with st.container(border=True):
            st.markdown(f"**{r.product}**")
            quantity = f"{r.quantity:g} {r.unit}" if r.quantity == r.quantity else ""
            price = f"KES {r.price:,.0f} per {r.unit}" if r.price == r.price else ""
            st.write(" | ".join(x for x in [quantity, price] if x))
            if _text(r.details):
                st.write(r.details)
            place = ", ".join(x for x in [_text(r.village), _text(r.ward),
                                          _text(r.sub_county)] if x)
            st.caption(f"Seller: {r.name} ({place}) - posted {r.created_at:%d %b %Y}")
            if _text(r.phone):
                st.write(f"Phone: {r.phone}")
            buttons = st.columns(2)
            if r.farmer_id != user["id"]:
                buttons[0].button("Message seller", key=f"msg_{r.id}",
                                  on_click=go_to_messages, args=(r.farmer_id,))
            if user["role"] == "admin":
                if buttons[1].button("Remove listing (admin)", key=f"adm_del_{r.id}"):
                    db.delete_listing(int(r.id), user)
                    st.rerun()
 
 
def post_tab(user):
    with st.form("listing_form", clear_on_submit=True):
        product = st.selectbox("Product", config.PRODUCTS + ["Other"])
        other = st.text_input("If you chose Other, type the product name")
        quantity = st.number_input("Quantity available", min_value=0.0, step=1.0)
        unit = st.selectbox("Unit", config.PRICE_UNITS)
        price = st.number_input("Asking price per unit (KES)", min_value=0.0, step=10.0)
        details = st.text_area("Details (quality, when it will be ready, where to "
                               "collect)")
        if st.form_submit_button("Post listing"):
            name = other.strip() if product == "Other" else product
            if not name or quantity <= 0 or price <= 0:
                st.error("Fill in the product, a quantity above 0 and a price above 0.")
            else:
                db.add_listing(user["id"], name, quantity, unit, price,
                               details.strip()[:500])
                st.success("Posted. Other farmers can now see your listing.")
    st.caption("Your phone number is shown only if you ticked that option in "
               "My Profile. Never share bank or M-Pesa PIN numbers with anyone.")
 
 
def mine_tab(user):
    df = db.get_listings(farmer_id=user["id"])
    if df.empty:
        st.info("You have not posted anything yet.")
        return
    for r in df.itertuples():
        with st.container(border=True):
            st.markdown(f"**{r.product}** - {r.quantity:g} {r.unit} at "
                        f"KES {r.price:,.0f} - {r.status}")
            buttons = st.columns(2)
            if r.status == "Open" and buttons[0].button("Mark as sold",
                                                         key=f"sold_{r.id}"):
                db.mark_listing_sold(int(r.id), user["id"])
                st.rerun()
            if buttons[1].button("Delete", key=f"del_{r.id}"):
                db.delete_listing(int(r.id), user)
                st.rerun()
 
 
def marketplace_page(user):
    st.header("🛍️ Marketplace")
    tabs = st.tabs(["Browse", "Post a listing", "My listings"])
    with tabs[0]:
        browse_tab(user)
    with tabs[1]:
        post_tab(user)
    with tabs[2]:
        mine_tab(user)
 
 
# ---------- DIRECTORY ----------
def directory_page(user):
    st.header("👥 Farmer directory")
    st.caption("Farmers who chose to be listed. Contact them through Messages.")
    c1, c2, c3 = st.columns(3)
    with c1:
        sub = st.selectbox("Sub-county", [config.ALL_SUB_COUNTIES] + config.SUB_COUNTIES,
                           key="dir_sub")
    with c2:
        ftype = st.selectbox("Type of farming", ["Any"] + config.FARMING_TYPES,
                             key="dir_type")
    with c3:
        search = st.text_input("Crop or animal (e.g. maize, goats)", key="dir_search")
    df = db.get_directory(user["id"],
                          None if sub == config.ALL_SUB_COUNTIES else sub,
                          None if ftype == "Any" else ftype)
    if search.strip():
        key = search.strip().lower()
        has = (df["crops"].fillna("").str.lower().str.contains(key, regex=False)
               | df["animals"].fillna("").str.lower().str.contains(key, regex=False))
        df = df[has]
    if df.empty:
        st.info("No farmers match.")
        return
    st.write(f"{len(df)} found")
    for r in df.head(50).itertuples():
        with st.container(border=True):
            badge = "" if r.role == "farmer" else f" ({r.role.title()})"
            st.markdown(f"**{r.name}**{badge}")
            place = ", ".join(x for x in [_text(r.village), _text(r.ward),
                                          _text(r.sub_county)] if x)
            st.caption(f"{place} - {r.farming_type} farming")
            grows = ", ".join(x for x in [_text(r.crops), _text(r.animals)] if x)
            if grows:
                st.write(grows)
            if _text(r.phone):
                st.write(f"Phone: {r.phone}")
            st.button("Send a message", key=f"dir_{r.id}", on_click=go_to_messages,
                      args=(r.id,))
 
 
PAGES = [
    {"order": 90, "label": "🛍️ Marketplace", "func": marketplace_page,
     "roles": ALL_ROLES},
    {"order": 95, "label": "👥 Farmer directory", "func": directory_page,
     "roles": ALL_ROLES},
]
