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
         "Pigs (swine)": "🐖", "Rabbits": "🐇", "Chickens": "🐔", "Fish": "🐟"}


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
_t = extras._t


def _tags(text):
    items = extras.split_products(text)
    if items:
        st.markdown(" ".join(f'<span class="tag">{p}</span>' for p in items),
                    unsafe_allow_html=True)


def _crop_card(r, prod, money, fid):
    with st.container(border=True):
        pic = extras.photo_bytes(r.photo)
        if pic:
            st.image(pic, width=170)
        st.markdown(f"### 🌾 {r.crop}" + (f" ({r.variety})" if _has(r.variety) and r.variety else ""))
        bits = [r.crop_group, f"{r.acres:,.2f} acres"] + ([r.plot] if _has(r.plot) and r.plot else [])
        st.caption("  ·  ".join(b for b in bits if b))
        more = [x for x in (r.planting_method, r.growing_system, r.seed_source) if _has(x) and x]
        if _has(r.intercrop) and r.intercrop:
            more.append(f"Mixed with {r.intercrop}")
        if more:
            st.caption("  ·  ".join(more))
        if _has(r.purpose):
            st.markdown(f'<span class="tag">{r.purpose}</span>', unsafe_allow_html=True)
        st.caption("Products:")
        _tags(r.products)
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


def _fish_or_group_card(r, fid):
    fish = r.animal == "Fish"
    with st.container(border=True):
        pic = extras.photo_bytes(r.photo)
        if pic:
            st.image(pic, width=170)
        st.markdown(f"### {EMOJI.get(r.animal, '🐾')} {extras.animal_label(r)}")
        if _has(r.purpose):
            st.markdown(f'<span class="tag">{r.purpose}</span>', unsafe_allow_html=True)
        st.caption("Products:")
        _tags(r.products)
        if not fish:
            bits = [x for x in (r.breed, r.system, extras.age_text(r.birth_date)) if _has(x) and x]
            if _has(r.weight_kg) and r.weight_kg:
                bits.append(f"about {r.weight_kg:,.0f} kg each")
            st.caption("  ·  ".join(bits))
        else:
            unit = _has(r.system) and r.system or "Pond"
            each = r.capacity if _has(r.capacity) else 0
            room = r.max_fish if _has(r.max_fish) else 0
            n = int(r.head_count)
            st.write(f"**{n} {unit.lower()}{'s' if n != 1 else ''}** of {_t_breed(r)}"
                     + (f"  ·  size of one: {r.size_m:,.0f} " + ("m²" if unit == "Pond" else "m³")
                        if _has(r.size_m) and r.size_m else ""))
            st.write(f"**Capacity of one {unit.lower()}:** {room:,.0f} fish   ·   "
                     f"**Stocked in each now:** {each:,.0f}")
            if room > 0:
                full = min(each / room, 1.0)
                st.progress(full, text=f"{each * n:,.0f} fish stocked out of {room * n:,.0f} "
                                       f"that all your {unit.lower()}s can hold ({full * 100:,.0f}% full)")
            if _has(r.feeds_per_day):
                st.caption(f"Fed {int(r.feeds_per_day)} times a day")
            days = config.HARVEST_FREQ.get(r.harvest_freq, extras.FISH_DAYS)
            last = extras.last_event(fid, int(r.id), "Catch / harvest")
            base = last or (r.stocked_on if _has(r.stocked_on) else None)
            if base:
                due = base + timedelta(days=days)
                gone = max((date.today() - base).days, 0)
                st.progress(min(gone / days, 1.0),
                            text=f"Harvest: {_t_freq(r)}. Next harvest due {due:%d %b %Y}"
                                 + (" (due now)" if date.today() >= due else ""))
        if st.button("Remove", key=f"rma_{r.id}"):
            db.delete_farm_animal(fid, int(r.id))
            st.rerun()


def _t_breed(r):
    return r.breed if _has(r.breed) and r.breed else "fish"


def _t_freq(r):
    return r.harvest_freq if _has(r.harvest_freq) and r.harvest_freq else "about every 6 months"


def _herd_table(sub, fid):
    """Animals registered one by one: tag, name, class, age, colour, weight, products."""
    rows = []
    for r in sub.itertuples():
        rows.append({"id": r.id, "Tag": _t(r.tag), "Name": _t(r.name), "Class": _t(r.sex),
                     "Age": extras.age_text(r.birth_date), "Colour": _t(r.colour),
                     "Weight (kg)": f"{r.weight_kg:,.0f}" if _has(r.weight_kg) else "",
                     "Breed": _t(r.breed), "Products": ", ".join(extras.split_products(r.products)),
                     "Why kept": _t(r.purpose)})
    import pandas as pd
    extras.tick_table(pd.DataFrame(rows), f"herd_{sub.iloc[0]['animal']}", {},
                      lambda i: db.delete_farm_animal(fid, i))
    st.caption("Tick a row only to remove an animal added by mistake. If an animal was SOLD or "
               "DIED, record that in Livestock records instead, so your history stays correct.")
    with st.expander("📷 See the pictures"):
        shown = [r for r in sub.itertuples() if extras.photo_bytes(r.photo)]
        if not shown:
            st.caption("No pictures yet.")
        for i in range(0, len(shown), 4):
            for col, r in zip(st.columns(4), shown[i:i + 4]):
                col.image(extras.photo_bytes(r.photo), caption=extras.animal_label(r))


def _age_inputs():
    """Returns the date of birth, or None if the farmer has not given the age."""
    known = st.radio("Do you know the date of birth?", ["Yes", "No, I will type the age"],
                     horizontal=True)
    if known == "Yes":
        return st.date_input("Date of birth", value=None, max_value=date.today(),
                             format="DD/MM/YYYY")
    a, b = st.columns(2)
    years = a.number_input("Age: years", min_value=0, max_value=40, step=1)
    months = b.number_input("Age: extra months", min_value=0, max_value=11, step=1)
    if years == 0 and months == 0:
        return None
    return date.today() - timedelta(days=int(years * 365.25 + months * 30.44))


# ---------- POP-UP FORMS ----------
@st.dialog("Add a crop", width="large")
def crop_dialog(user):
    st.caption("Fill the boxes from top to bottom. The picture is the last question.")
    group = st.selectbox("1. Crop group", list(config.CROP_GROUPS),
                         format_func=lambda g: f"{g} ({GROUP_HELP[g]})" if g in GROUP_HELP else g)
    crop = st.selectbox("2. Which crop?", config.CROP_GROUPS[group])
    variety = st.text_input("3. Variety or seed name (optional)", placeholder="e.g. Hybrid 614")
    plot = st.text_input("4. Name of the plot or field (optional)", placeholder="e.g. Lower shamba")
    acres = st.number_input("5. Acres under this crop", min_value=0.0, step=0.25)
    planted = st.date_input("6. Date planted", date.today(), format="DD/MM/YYYY")
    method = st.selectbox("7. How was it planted?", config.PLANTING_METHODS)
    system = st.radio("8. How is it watered?", config.GROWING_SYSTEMS, horizontal=True)
    source = st.selectbox("9. Where did the seed come from?", config.SEED_SOURCES)
    mixed = st.text_input("10. Is it mixed with another crop? Which one? (leave empty if not)",
                          placeholder="e.g. Beans")
    options = config.CROP_PRODUCTS.get(group, ["Harvested produce"])
    products = st.multiselect("11. What will you get and sell from this crop? "
                              "(these appear in your sales reports)", options,
                              default=options[:1], key=f"crop_prod_{group}")
    purpose = st.radio("12. Why do you grow it?", extras.PURPOSES)
    picture = extras.photo_input("crop")
    if st.button("Save crop", type="primary", width="stretch"):
        if acres <= 0:
            st.error("Enter the acres above 0.")
            return
        if not products:
            st.error("Choose at least one product you get from this crop.")
            return
        extras.save_crop(user["id"], crop_group=group, crop=crop, acres=acres, purpose=purpose,
                         variety=variety.strip() or None, plot=plot.strip() or None,
                         planted_on=planted, planting_method=method, growing_system=system,
                         seed_source=source, intercrop=mixed.strip() or None,
                         products="|".join(products), photo=picture)
        st.toast(f"{crop} saved ✓")
        st.rerun()


@st.dialog("Add animals or fish", width="large")
def animal_dialog(user):
    fid = user["id"]
    st.caption("Fill the boxes from top to bottom. The picture is the last question.")
    animal = st.selectbox("1. What do you keep?", config.ANIMALS)
    data = {"animal": animal}
    if animal == "Fish":
        system = st.radio("2. Do you keep the fish in ponds or in cages?", config.FISH_SYSTEMS,
                          horizontal=True)
        u = system.lower()
        data.update(entry_type="group", system=system)
        data["name"] = st.text_input(f"3. Name of this group of {u}s (optional)",
                                     placeholder=f"e.g. Lower {u}s").strip() or None
        data["breed"] = st.selectbox("4. Main fish breed", config.FISH_BREEDS)
        data["head_count"] = int(st.number_input(f"5. How many {u}s are in this group?",
                                                 min_value=0, step=1))
        data["size_m"] = st.number_input("6. Size of ONE pond (square metres)" if system == "Pond"
                                         else "6. Size of ONE cage (cubic metres)",
                                         min_value=0.0, step=1.0) or None
        data["max_fish"] = st.number_input(f"7. Capacity: the most fish ONE {u} can hold",
                                           min_value=0, step=100) or None
        data["capacity"] = st.number_input(f"8. Fish stocked in EACH {u} now",
                                           min_value=0, step=100) or None
        data["stocked_on"] = st.date_input("9. Date the fish were stocked", date.today(),
                                           format="DD/MM/YYYY")
        data["feeds_per_day"] = int(st.number_input("10. Times you feed each day",
                                                    min_value=0, max_value=6, value=2))
        data["harvest_freq"] = st.selectbox("11. How often do you harvest?",
                                            list(config.HARVEST_FREQ))
        step = 12
    else:
        single = False
        if animal in config.TAGGED_ANIMALS:
            how = st.radio("2. How do you want to register them?",
                           ["One animal at a time (with a tag number or name)",
                            "A group together (no tags)"])
            single = how.startswith("One")
        data["entry_type"] = "single" if single else "group"
        data["system"] = st.selectbox("3. How are they kept?", config.KEEPING_SYSTEMS[animal])
        data["breed"] = st.text_input("4. Breed (optional)",
                                      placeholder=config.BREED_EXAMPLES.get(animal, "")).strip() or None
        if single:
            a, b = st.columns(2)
            data["tag"] = a.text_input("5. Tag number", placeholder="e.g. T045").strip() or None
            data["name"] = b.text_input("   or name", placeholder="e.g. Daisy").strip() or None
            data["sex"] = st.selectbox("6. What is it? (class of animal)", config.ANIMAL_CLASSES[animal])
            data["birth_date"] = _age_inputs()
            data["colour"] = st.selectbox("7. Colour of the skin or coat", config.COAT_COLOURS)
            data["weight_kg"] = st.number_input(
                "8. Weight now (kg)", min_value=0.0, step=1.0,
                help="A weighing scale or weigh band is best. If you have none, give your best guess.")
            data["head_count"] = 1
            step = 9
        else:
            data["name"] = st.text_input("5. Name of this group (optional)",
                                         placeholder="e.g. Layers house 1").strip() or None
            data["head_count"] = int(st.number_input("6. How many do you have now?",
                                                     min_value=0, step=1))
            data["birth_date"] = _age_inputs() if animal != "Chickens" else None
            if animal == "Chickens":
                data["weight_kg"] = None
            else:
                data["weight_kg"] = st.number_input("7. Average weight of one (kg, optional)",
                                                    min_value=0.0, step=1.0) or None
            step = 8
    options = config.ANIMAL_PRODUCTS[animal]
    data["products"] = st.multiselect(
        f"{step}. What do you get and sell from them? (these appear in your sales reports)",
        options, default=options[:1], key=f"animal_prod_{animal}")
    data["purpose"] = st.radio(f"{step + 1}. Why do you keep them?", extras.PURPOSES)
    picture = extras.photo_input("animal")
    if st.button("Save", type="primary", width="stretch"):
        if data["head_count"] <= 0:
            st.error("Enter a number above 0.")
        elif not data["products"]:
            st.error("Choose at least one product you get from them.")
        elif data["entry_type"] == "single" and not (data.get("tag") or data.get("name")):
            st.error("Type a tag number or a name, so you can tell this animal apart.")
        elif data["entry_type"] == "single" and data.get("tag") and extras.tag_taken(fid, animal, data["tag"]):
            st.error(f"You already have {animal} with tag {data['tag']}.")
        elif data["entry_type"] == "single" and not data["weight_kg"]:
            st.error("Enter the weight in kg (your best guess is fine).")
        elif data["entry_type"] == "single" and not data["birth_date"]:
            st.error("Enter the date of birth or the age.")
        elif animal == "Fish" and data.get("max_fish") and (data.get("capacity") or 0) > data["max_fish"]:
            st.error("Fish stocked in each cannot be more than the capacity.")
        else:
            data["products"] = "|".join(data["products"])
            data["photo"] = picture
            extras.save_animal(fid, **data)
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
    head = int(animals.loc[animals["animal"] != "Fish", "head_count"].sum()) if len(animals) else 0
    style.kpi_row([("Total land", f"{sum(land.values()):,.2f} acres", "all ownership types", False),
                   ("Land in active use", f"{prof['active_acres']:,.2f} acres", "this season", False),
                   ("Farm scale", config.scale_for(prof["active_acres"]), "worked out for you", False),
                   ("Crops and animals", f"{len(crops)} crops · {head} animals", "on your farm now", False)])
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
            prod = extras.animal_production(fid)
            for animal, sub in animals.groupby("animal", sort=False):
                total = int(sub["head_count"].sum())
                st.markdown(f"## {EMOJI.get(animal, '🐾')} {animal}"
                            + ("" if animal == "Fish" else f"  ·  {total} on the farm"))
                with st.container(border=True):
                    _money_row(money.get(animal))
                    _split_bar(prod.get(animal), "units")
                singles = sub[sub["entry_type"] == "single"]
                if len(singles):
                    _herd_table(singles, fid)
                others = list(sub[sub["entry_type"] != "single"].itertuples())
                for i in range(0, len(others), 2):
                    for col, r in zip(st.columns(2), others[i:i + 2]):
                        with col:
                            _fish_or_group_card(r, fid)
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
