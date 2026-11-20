"""My Farm (enterprise cards, land) and My Profile (details, photo, password)."""
from datetime import date, timedelta
 
import streamlit as st
 
import config
import db
import extras
import style
 
GROUP_HELP = {
    "Cereals": "grains such as maize, sorghum and millet",
    "Legumes": "beans, peas and groundnuts",
    "Roots and tubers": "crops that grow under the ground, such as cassava",
    "Leafy vegetables": "kale, spinach and other green leaves",
    "Other vegetables": "tomato, onion and similar",
    "Fruits": "mango, banana, pawpaw and similar",
}
EMOJI = {"Cattle (dairy)": "🐄", "Cattle (beef/zebu)": "🐂", "Goats": "🐐", "Sheep": "🐑",
         "Chickens": "🐔", "Fish": "🐟"}
 
 
def _has(x):
    return x is not None and x == x
 
 
def _money_row(m):
    inc, exp = (m or {}).get("Income", 0.0), (m or {}).get("Expense", 0.0)
    a, b, c = st.columns(3)
    a.metric("Received", style.kes(inc))
    b.metric("Spent", style.kes(exp))
    c.metric("Profit", style.kes(inc - exp))
    if not m:
        st.caption("Choose this on the Money page to see its profit here.")
 
 
def _split_bar(p, unit):
    both = p["sold"] + p["home"] if p else 0
    if both <= 0:
        st.caption("Record a harvest or production with amounts sold and used at home "
                   "to see the split here.")
        return
    st.progress(p["sold"] / both, text=f"Sold {p['sold'] / both * 100:,.0f}%   ·   "
                                       f"Used at home {p['home'] / both * 100:,.0f}%")
    st.caption(f"{p['sold']:,.0f} {unit} sold  ·  {p['home']:,.0f} {unit} used at home")
 
 
# ---------- THE CARDS ----------
def _crop_card(r, prod, money, fid):
    with st.container(border=True):
        st.markdown(f"### 🌾 {r.crop}" + (f" ({r.variety})" if _has(r.variety) else ""))
        bits = [r.crop_group, f"{r.acres:,.2f} acres"] + ([r.plot] if _has(r.plot) else [])
        st.caption("  ·  ".join(b for b in bits if b))
        if _has(r.purpose):
            st.markdown(f'<span class="tag">{r.purpose}</span>', unsafe_allow_html=True)
        if _has(r.planted_on):
            days, day = extras.crop_days(r.crop), max((date.today() - r.planted_on).days, 0)
            st.progress(min(day / days, 1.0),
                        text=f"Day {day} of about {days}. Expected harvest "
                             f"{r.planted_on + timedelta(days=days):%d %b %Y}")
        _money_row(money.get(r.crop))
        _split_bar(prod.get(r.crop), "kg")
        if st.button("Remove this crop", key=f"rmc_{r.id}"):
            db.delete_farmer_crop(fid, int(r.id))
            st.rerun()
 
 
def _animal_card(r, prod, money, fid, first):
    fish = r.animal == "Fish"
    with st.container(border=True):
        unit = f"{r.system.lower()}s" if fish and _has(r.system) else "animals"
        st.markdown(f"### {EMOJI.get(r.animal, '🐾')} {r.animal}" +
                    (f" ({r.system})" if fish and _has(r.system) else ""))
        bits = [f"{int(r.head_count)} {unit}"] + ([r.breed] if _has(r.breed) else [])
        st.caption("  ·  ".join(bits))
        if _has(r.purpose):
            st.markdown(f'<span class="tag">{r.purpose}</span>', unsafe_allow_html=True)
        if fish and _has(r.capacity):
            st.write(f"**Fish stocked in each:** {r.capacity:,.0f}   ·   "
                     f"**All together:** {r.capacity * r.head_count:,.0f}")
            more = []
            if _has(r.size_m):
                more.append(f"Size of one: {r.size_m:,.0f} " + ("m²" if r.system == "Pond" else "m³"))
            if _has(r.feeds_per_day):
                more.append(f"Fed {int(r.feeds_per_day)} times a day")
            if more:
                st.caption("  ·  ".join(more))
            if _has(r.stocked_on):
                day = max((date.today() - r.stocked_on).days, 0)
                st.progress(min(day / extras.FISH_DAYS, 1.0),
                            text=f"Day {day} of about {extras.FISH_DAYS} to harvest size. "
                                 f"Expected harvest {r.stocked_on + timedelta(days=extras.FISH_DAYS):%d %b %Y}")
        if first:
            _money_row(money.get(r.animal))
            _split_bar(prod.get(r.animal), "units")
        if st.button("Remove", key=f"rma_{r.id}"):
            db.delete_farm_animal(fid, int(r.id))
            st.rerun()
 
 
# ---------- POP-UP FORMS ----------
@st.dialog("Add a crop")
def crop_dialog(user):
    group = st.selectbox("Crop group", list(config.CROP_GROUPS),
                         format_func=lambda g: f"{g} ({GROUP_HELP[g]})" if g in GROUP_HELP else g)
    crop = st.selectbox("Which crop?", config.CROP_GROUPS[group])
    variety = st.text_input("Variety or seed name (optional)", placeholder="e.g. Hybrid 614")
    plot = st.text_input("Plot or field name (optional)", placeholder="e.g. Lower shamba")
    acres = st.number_input("Acres under this crop", min_value=0.0, step=0.25)
    planted = st.date_input("Date planted", date.today())
    purpose = st.radio("Why do you grow it?", extras.PURPOSES)
    if st.button("Save crop", type="primary", width="stretch"):
        if acres <= 0:
            st.error("Enter the acres above 0.")
            return
        extras.save_crop(user["id"], group, crop, acres, purpose, variety.strip(),
                         plot.strip(), planted)
        st.toast(f"{crop} saved ✓")
        st.rerun()
 
 
@st.dialog("Add animals or fish")
def animal_dialog(user):
    animal = st.selectbox("What do you keep?", config.ANIMALS)
    cap = size = feeds = started = None
    if animal == "Fish":
        system = st.radio("Fish farming system", config.FISH_SYSTEMS, horizontal=True)
        unit = system.lower()
        breed = st.selectbox("Main fish breed", config.FISH_BREEDS)
        count = st.number_input(f"How many {unit}s?", min_value=0, step=1)
        cap = st.number_input(f"Fish stocked in each {unit}", min_value=0, step=100)
        size = st.number_input("Size of one pond (square metres)" if system == "Pond"
                               else "Size of one cage (cubic metres)", min_value=0.0, step=1.0)
        feeds = st.number_input("Times you feed each day", min_value=0, max_value=6, value=2)
        started = st.date_input("Date the fish were stocked", date.today())
    else:
        system = None
        breed = st.text_input("Breed (optional)", placeholder="e.g. Friesian, Galla, Kienyeji")
        count = st.number_input("How many do you have now?", min_value=0, step=1)
    purpose = st.radio("Why do you keep them?", extras.PURPOSES)
    if st.button("Save", type="primary", width="stretch"):
        if count <= 0:
            st.error("Enter a number above 0.")
            return
        extras.save_animal(user["id"], animal, system, breed.strip() if breed else None,
                           int(count), purpose, cap or None, size or None, feeds, started)
        st.toast("Saved ✓")
        st.rerun()
 
 
# ---------- LAND ----------
def land_tab(user):
    fid = user["id"]
    land, prof = db.get_land(fid), db.get_farm_profile(fid)
    with st.container(border=True):
        with st.form("land_form"):
            st.write("How much land do you have, by type of ownership? (acres)")
            values = {t: st.number_input(t, min_value=0.0, step=0.25,
                                         value=float(land.get(t, 0.0)), key=f"land_{t}")
                      for t in config.TENURES}
            active = st.number_input("Land you are actively using for farming now (acres)",
                                     min_value=0.0, step=0.25, value=float(prof["active_acres"]))
            fertility = st.selectbox(
                "Soil fertility (your best judgement)", list(config.FERTILITY),
                index=list(config.FERTILITY).index(prof["fertility"])
                if prof["fertility"] in config.FERTILITY else 1)
            rainfall = st.selectbox(
                "Rainfall in your area", list(config.RAINFALL),
                index=list(config.RAINFALL).index(prof["rainfall"])
                if prof["rainfall"] in config.RAINFALL else 1)
            if st.form_submit_button("Save land details", type="primary"):
                if active > sum(values.values()):
                    st.error("Land in active use cannot be more than your total land.")
                else:
                    db.save_land_and_profile(fid, values, active, fertility, rainfall)
                    st.success("Saved.")
                    st.rerun()
    st.caption("Scale is worked out from land in active use: under 5 acres is small, "
               "5 to under 10 is semi-large, and 10 or more is large.")
 
 
# ---------- MY FARM ----------
def farm_page(user):
    fid, ftype = user["id"], user["farming_type"]
    style.header("My Farm", "Your land, crops and animals, with their profit and production")
    land, prof = db.get_land(fid), db.get_farm_profile(fid)
    crops, animals = extras.crops(fid), extras.animals(fid)
    style.kpi_row([("Total land", f"{sum(land.values()):,.2f} acres", "all ownership types", False),
                   ("Land in active use", f"{prof['active_acres']:,.2f} acres", "this season", False),
                   ("Farm scale", config.scale_for(prof["active_acres"]), "worked out for you", False),
                   ("Enterprises", len(crops) + len(animals), "crops, animals and fish", False)])
    st.write("")
    tab_enterprises, tab_land = st.tabs(["My crops and animals", "Land and scale"])
    with tab_enterprises:
        a, b, _ = st.columns([1, 1, 2])
        if ftype in ("Crops", "Mixed") and a.button("＋ Add a crop", type="primary", width="stretch"):
            crop_dialog(user)
        if ftype in ("Livestock", "Mixed") and b.button("＋ Add animals or fish", type="primary",
                                                        width="stretch"):
            animal_dialog(user)
        money = extras.money_by_enterprise(fid)
        if ftype in ("Crops", "Mixed"):
            if crops.empty:
                st.info("No crops yet. Click **Add a crop**.")
            prod = extras.crop_production(fid)
            items = list(crops.itertuples())
            for i in range(0, len(items), 2):
                for col, r in zip(st.columns(2), items[i:i + 2]):
                    with col:
                        _crop_card(r, prod, money, fid)
            over = crops["acres"].sum() if len(crops) else 0
            if over > prof["active_acres"] > 0:
                st.warning(f"Your crops add up to {over:,.2f} acres, which is more than your land "
                           f"in active use ({prof['active_acres']:,.2f}). Check both.")
        if ftype in ("Livestock", "Mixed"):
            if animals.empty:
                st.info("No animals yet. Click **Add animals or fish**.")
            prod, seen, items = extras.animal_production(fid), set(), list(animals.itertuples())
            for i in range(0, len(items), 2):
                cols = st.columns(2)
                for col, r in zip(cols, items[i:i + 2]):
                    with col:
                        _animal_card(r, prod, money, fid, r.animal not in seen)
                        seen.add(r.animal)
    with tab_land:
        land_tab(user)
 
 
# ---------- MY PROFILE ----------
def _as_text(value):
    return "" if value is None or value != value else str(value)
 
 
def profile_page(user):
    style.header("My Profile", "Your details, photo and password")
    me = db.get_farmer(user["id"])
    a, b = st.columns([1, 4])
    a.markdown(style.avatar(), unsafe_allow_html=True)
    if b.button("📷 Add or change my photo"):
        extras.photo_dialog(user["id"])
    tab_details, tab_password = st.tabs(["My details", "Change password"])
    with tab_details:
        with st.form("profile_form"):
            name = st.text_input("Full name", value=me["name"])
            gender = st.selectbox("Gender", config.GENDERS,
                                  index=config.GENDERS.index(me["gender"])
                                  if me["gender"] in config.GENDERS else 0)
            ward = st.text_input("Ward", value=me["ward"] or "")
            village = st.text_input("Village", value=me["village"] or "")
            farming_type = me["farming_type"]
            if user["role"] == "farmer":
                farming_type = st.selectbox(
                    "Type of farming", config.FARMING_TYPES,
                    index=config.FARMING_TYPES.index(me["farming_type"])
                    if me["farming_type"] in config.FARMING_TYPES else 0,
                    format_func=lambda t: f"{t} - {config.FARMING_TYPE_HELP[t]}")
            lat_text = st.text_input("Latitude (optional)", value=_as_text(me["latitude"]))
            lon_text = st.text_input("Longitude (optional)", value=_as_text(me["longitude"]))
            in_directory = st.checkbox("Let other registered users find me in the directory "
                                       "and message me", value=bool(me["in_directory"]))
            share_contact = st.checkbox("Show my phone number on my marketplace posts",
                                        value=bool(me["share_contact"]))
            if st.form_submit_button("Save my details", type="primary"):
                lat, lat_error = config.parse_coordinate(lat_text, *config.LAT_RANGE, "Latitude")
                lon, lon_error = config.parse_coordinate(lon_text, *config.LON_RANGE, "Longitude")
                if not name.strip():
                    st.error("Your name cannot be empty.")
                elif lat_error or lon_error:
                    st.error(lat_error or lon_error)
                elif (lat is None) != (lon is None):
                    st.error("Fill in both latitude and longitude, or leave both empty.")
                else:
                    db.update_profile(user["id"], {
                        "name": name.strip(), "gender": gender, "ward": ward.strip(),
                        "village": village.strip(), "farming_type": farming_type,
                        "latitude": lat, "longitude": lon,
                        "in_directory": in_directory, "share_contact": share_contact})
                    st.session_state.user = db.get_farmer(user["id"])
                    st.success("Saved.")
    with tab_password:
        with st.form("password_form", clear_on_submit=True):
            old = st.text_input("Current password", type="password")
            new = st.text_input("New password (8 or more characters)", type="password")
            again = st.text_input("Type the new password again", type="password")
            if st.form_submit_button("Change password", type="primary"):
                if len(new) < 8:
                    st.error("The new password must have 8 or more characters.")
                elif new != again:
                    st.error("The two new passwords do not match.")
                elif db.change_password(user["id"], old, new):
                    st.success("Password changed.")
                else:
                    st.error("Your current password is wrong.")
 
 
PAGES = [
    {"order": 10, "label": "🏡 My Farm", "func": farm_page, "roles": ("farmer",)},
    {"order": 990, "label": "👤 My Profile", "func": profile_page,
     "roles": ("farmer", "coordinator", "agrovet", "admin")},
]
