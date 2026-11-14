"""My Farm (land, crops grown, animals kept) and My Profile pages."""
import streamlit as st
 
import config
import db
 
 
# ---------- LAND ----------
def land_tab(user):
    fid = user["id"]
    land = db.get_land(fid)
    prof = db.get_farm_profile(fid)
    with st.form("land_form"):
        st.write("How much land do you have, by type of ownership? (acres)")
        values = {}
        for tenure in config.TENURES:
            values[tenure] = st.number_input(
                tenure, min_value=0.0, step=0.25, value=float(land.get(tenure, 0.0)),
                key=f"land_{tenure}")
        active = st.number_input(
            "Land you are actively using for farming now (acres)", min_value=0.0,
            step=0.25, value=float(prof["active_acres"]))
        fertility = st.selectbox(
            "Soil fertility (your best judgement)", list(config.FERTILITY),
            index=list(config.FERTILITY).index(prof["fertility"])
            if prof["fertility"] in config.FERTILITY else 1)
        rainfall = st.selectbox(
            "Rainfall in your area", list(config.RAINFALL),
            index=list(config.RAINFALL).index(prof["rainfall"])
            if prof["rainfall"] in config.RAINFALL else 1)
        if st.form_submit_button("Save land details"):
            total = sum(values.values())
            if active > total:
                st.error("Land in active use cannot be more than your total land.")
            else:
                db.save_land_and_profile(fid, values, active, fertility, rainfall)
                st.success("Saved.")
    # Read again so the numbers below are always up to date
    land = db.get_land(fid)
    prof = db.get_farm_profile(fid)
    st.subheader("Your farm at a glance")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total land", f"{sum(land.values()):,.2f} acres")
    c2.metric("Land in active use", f"{prof['active_acres']:,.2f} acres")
    c3.metric("Farm scale", config.scale_for(prof["active_acres"]))
    st.caption("Scale is worked out from land in active use: under 5 acres is small, "
               "5 to under 10 is semi-large, and 10 or more is large.")
 
 
# ---------- CROPS GROWN ----------
def crops_tab(user):
    fid = user["id"]
    st.write("List the crops you grow and the acres under each.")
    group = st.selectbox("Crop group", list(config.CROP_GROUPS), key="farm_crop_group")
    with st.form("farm_crop_form", clear_on_submit=True):
        crop = st.selectbox("Crop", config.CROP_GROUPS[group])
        acres = st.number_input("Acres under this crop", min_value=0.0, step=0.25)
        if st.form_submit_button("Add crop"):
            if acres > 0:
                db.add_farmer_crop(fid, group, crop, acres)
                st.success(f"{crop} saved.")
            else:
                st.error("Enter the acres above 0.")
    df = db.get_farmer_crops(fid)
    if df.empty:
        st.info("No crops listed yet.")
        return
    st.dataframe(df[["crop_group", "crop", "acres"]].rename(
        columns={"crop_group": "Group", "crop": "Crop", "acres": "Acres"}),
        width="stretch", hide_index=True)
    active = db.get_farm_profile(fid)["active_acres"]
    if df["acres"].sum() > active > 0:
        st.warning(f"Your crops add up to {df['acres'].sum():,.2f} acres, which is more "
                   f"than your land in active use ({active:,.2f}). Check both.")
    remove = st.selectbox("Remove a crop from my list", ["-"] + df["crop"].tolist(),
                          key="rm_crop")
    if st.button("Remove crop", key="rm_crop_btn") and remove != "-":
        row_id = int(df.loc[df["crop"] == remove, "id"].iloc[0])
        db.delete_farmer_crop(fid, row_id)
        st.rerun()
 
 
# ---------- ANIMALS KEPT ----------
def animals_tab(user):
    fid = user["id"]
    st.write("List the animals, birds or fish you keep.")
    animal = st.selectbox("Animal", config.ANIMALS, key="farm_animal_pick")
    with st.form("farm_animal_form", clear_on_submit=True):
        if animal == "Fish":
            system = st.selectbox("Fish farming system", config.FISH_SYSTEMS)
            breed = st.selectbox("Main fish breed", config.FISH_BREEDS)
            count = st.number_input("Number of ponds or cages", min_value=0, step=1)
        else:
            system = None
            breed = st.text_input("Breed (optional, e.g. Friesian, Galla, Kienyeji)")
            count = st.number_input("How many do you have now?", min_value=0, step=1)
        if st.form_submit_button("Add animals"):
            if count > 0:
                db.add_farm_animal(fid, animal, system, breed or None, int(count))
                st.success("Saved.")
            else:
                st.error("Enter a number above 0.")
    df = db.get_farm_animals(fid)
    if df.empty:
        st.info("No animals listed yet.")
        return
    st.dataframe(df.drop(columns=["id"]).rename(columns={
        "animal": "Animal", "system": "System", "breed": "Breed",
        "head_count": "Number"}), width="stretch", hide_index=True)
    labels = {int(r.id): f"{r.animal} - {r.breed or 'no breed'} ({r.head_count})"
              for r in df.itertuples()}
    remove = st.selectbox("Remove an entry", [0] + list(labels), key="rm_animal",
                          format_func=lambda i: "-" if i == 0 else labels[i])
    if st.button("Remove entry", key="rm_animal_btn") and remove != 0:
        db.delete_farm_animal(fid, remove)
        st.rerun()
 
 
def farm_page(user):
    st.header("🏡 My Farm")
    names = ["Land and scale"]
    if user["farming_type"] in ("Crops", "Mixed"):
        names.append("Crops I grow")
    if user["farming_type"] in ("Livestock", "Mixed"):
        names.append("Animals I keep")
    tabs = st.tabs(names)
    with tabs[0]:
        land_tab(user)
    for tab, name in zip(tabs[1:], names[1:]):
        with tab:
            if name == "Crops I grow":
                crops_tab(user)
            else:
                animals_tab(user)
 
 
# ---------- MY PROFILE ----------
def _as_text(value):
    """Empty box for a missing number, otherwise the number as text."""
    return "" if value is None or value != value else str(value)
 
 
def profile_page(user):
    st.header("👤 My Profile")
    me = db.get_farmer(user["id"])
    tab_details, tab_password = st.tabs(["My details", "Change password"])
    with tab_details:
        with st.form("profile_form"):
            name = st.text_input("Full name", value=me["name"])
            gender = st.selectbox(
                "Gender", config.GENDERS,
                index=config.GENDERS.index(me["gender"])
                if me["gender"] in config.GENDERS else 0)
            ward = st.text_input("Ward", value=me["ward"] or "")
            village = st.text_input("Village", value=me["village"] or "")
            farming_type = st.selectbox(
                "Type of farming", config.FARMING_TYPES,
                index=config.FARMING_TYPES.index(me["farming_type"])
                if me["farming_type"] in config.FARMING_TYPES else 0,
                format_func=lambda t: f"{t} - {config.FARMING_TYPE_HELP[t]}")
            lat_text = st.text_input("Farm latitude (optional)",
                                     value=_as_text(me["latitude"]))
            lon_text = st.text_input("Farm longitude (optional)",
                                     value=_as_text(me["longitude"]))
            in_directory = st.checkbox(
                "Let other farmers find me in the directory and message me",
                value=bool(me["in_directory"]))
            share_contact = st.checkbox("Show my phone number on my marketplace posts",
                                        value=bool(me["share_contact"]))
            if st.form_submit_button("Save my details"):
                lat, lat_error = config.parse_coordinate(
                    lat_text, *config.LAT_RANGE, "Latitude")
                lon, lon_error = config.parse_coordinate(
                    lon_text, *config.LON_RANGE, "Longitude")
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
            if st.form_submit_button("Change password"):
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
     "roles": ("farmer", "coordinator", "admin")},
]
