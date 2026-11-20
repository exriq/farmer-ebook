"""Phase 6: extra database columns, the farmer photo, and pieces shared by several pages.
Nothing in db.py has to change."""
import base64
import io
from datetime import date
 
import streamlit as st
 
import config
import db
 
# Columns the record pages may now save (db.py reads these lists)
for _table, _cols in {"money": ["enterprise"], "crop_records": ["sold", "home_use"],
                      "livestock_records": ["sold", "home_use"]}.items():
    for _col in _cols:
        if _col not in db.RECORD_TABLES[_table]:
            db.RECORD_TABLES[_table].append(_col)
 
_STEPS = [
    "ALTER TABLE farmers ADD COLUMN IF NOT EXISTS photo TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS purpose TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS variety TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS plot TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS planted_on DATE",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS purpose TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS capacity DOUBLE PRECISION",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS size_m DOUBLE PRECISION",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS feeds_per_day INTEGER",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS stocked_on DATE",
    "ALTER TABLE money ADD COLUMN IF NOT EXISTS enterprise TEXT",
    "ALTER TABLE crop_records ADD COLUMN IF NOT EXISTS sold DOUBLE PRECISION",
    "ALTER TABLE crop_records ADD COLUMN IF NOT EXISTS home_use DOUBLE PRECISION",
    "ALTER TABLE livestock_records ADD COLUMN IF NOT EXISTS sold DOUBLE PRECISION",
    "ALTER TABLE livestock_records ADD COLUMN IF NOT EXISTS home_use DOUBLE PRECISION",
]
_done = False
 
 
def setup():
    """Adds the new columns once, when the app starts. Safe to run again."""
    global _done
    if not _done:
        for sql in _STEPS:
            db.run(sql)
        _done = True
 
 
PURPOSES = ["For sale", "For home use", "For both sale and home use"]
FISH_DAYS = 180
_DAYS = {"Maize": 120, "Sorghum": 120, "Finger millet": 120, "Bulrush millet": 90, "Rice": 130,
         "Beans": 75, "Groundnuts": 110, "Green grams": 70, "Cowpeas": 80, "Soya beans": 100,
         "Pigeon peas": 150, "Cassava": 270, "Sweet potato": 120, "Irish potato": 100,
         "Arrowroots": 270, "Kale (sukuma wiki)": 60, "Spinach": 45, "Amaranth (terere)": 40,
         "African nightshade (managu)": 45, "Spider plant (saget)": 45,
         "Cowpea leaves (kunde)": 45, "Cabbage": 90, "Tomato": 90, "Onion": 120,
         "Capsicum": 90, "Okra": 60, "Pumpkin": 100, "Eggplant": 100, "Watermelon": 90,
         "Banana": 270, "Pawpaw": 270}
BASE = {**config.UNIT_TO_KG, "trays": 30}          # everything is added up in one unit
 
 
def crop_days(crop):
    return _DAYS.get(crop, 100)
 
 
# ---------- crops and animals the farmer keeps ----------
def crops(fid):
    return db.table("SELECT id, crop_group, crop, acres, purpose, variety, plot, planted_on "
                    "FROM farmer_crops WHERE farmer_id = %s ORDER BY crop", (fid,))
 
 
def animals(fid):
    return db.table("SELECT id, animal, system, breed, head_count, purpose, capacity, size_m, "
                    "feeds_per_day, stocked_on FROM farm_animals WHERE farmer_id = %s "
                    "ORDER BY animal, id", (fid,))
 
 
def save_crop(fid, group, crop, acres, purpose, variety, plot, planted_on):
    db.run("""INSERT INTO farmer_crops (farmer_id, crop_group, crop, acres, purpose, variety,
                                        plot, planted_on)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
              ON CONFLICT (farmer_id, crop) DO UPDATE SET crop_group = EXCLUDED.crop_group,
                acres = EXCLUDED.acres, purpose = EXCLUDED.purpose, variety = EXCLUDED.variety,
                plot = EXCLUDED.plot, planted_on = EXCLUDED.planted_on""",
           (fid, group, crop, acres, purpose, variety or None, plot or None, planted_on))
 
 
def save_animal(fid, animal, system, breed, count, purpose, capacity, size_m, feeds, stocked):
    db.run("""INSERT INTO farm_animals (farmer_id, animal, system, breed, head_count, purpose,
                                        capacity, size_m, feeds_per_day, stocked_on)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
           (fid, animal, system, breed or None, count, purpose, capacity, size_m, feeds, stocked))
 
 
def enterprise_names(fid):
    names = crops(fid)["crop"].tolist() + animals(fid)["animal"].tolist()
    return list(dict.fromkeys(names))
 
 
# ---------- production: how much was sold and how much was used at home ----------
def _split(data):
    out = {}
    for name, unit, total, sold, home in data:
        k = BASE.get(unit, 1)
        o = out.setdefault(name, [0.0, 0.0, 0.0])
        o[0] += (total or 0) * k
        o[1] += (sold or 0) * k
        o[2] += (home or 0) * k
    return {n: {"total": v[0], "sold": v[1], "home": v[2]} for n, v in out.items()}
 
 
def crop_production(fid):
    return _split(db.rows("SELECT crop, unit, SUM(quantity), SUM(sold), SUM(home_use) "
                          "FROM crop_records WHERE farmer_id = %s AND activity = 'Harvest' "
                          "GROUP BY crop, unit", (fid,)))
 
 
def animal_production(fid):
    return _split(db.rows("SELECT animal, unit, SUM(quantity), SUM(sold), SUM(home_use) "
                          "FROM livestock_records WHERE farmer_id = %s AND activity = ANY(%s) "
                          "GROUP BY animal, unit", (fid, config.PRODUCTION_ACTIVITIES)))
 
 
def money_by_enterprise(fid):
    out = {}
    for name, kind, amount in db.rows("SELECT enterprise, kind, SUM(amount) FROM money WHERE "
                                      "farmer_id = %s AND enterprise IS NOT NULL "
                                      "GROUP BY enterprise, kind", (fid,)):
        out.setdefault(name, {"Income": 0.0, "Expense": 0.0})[kind] = float(amount or 0)
    return out
 
 
# ---------- a table with tick boxes ----------
def tick_table(df, key, rename, delete):
    """Shows rows with tick boxes. delete(row_id) is called for every ticked row."""
    n = st.session_state.get(key + "_n", 0)
    event = st.dataframe(df.drop(columns=["id"]).rename(columns=rename), hide_index=True,
                         width="stretch", on_select="rerun", selection_mode="multi-row",
                         key=f"{key}_{n}")
    picked = event.selection.rows
    if picked:
        st.caption("Tick the boxes on the left to choose rows.")
        if st.button(f"🗑 Delete {len(picked)} selected", key=key + "_del"):
            for i in picked:
                delete(int(df.iloc[i]["id"]))
            st.session_state[key + "_n"] = n + 1     # a fresh table, so no old ticks remain
            st.rerun()
    else:
        st.caption("Tick the boxes on the left to delete rows you entered by mistake.")
 
 
# ---------- the farmer's photo ----------
def save_photo(uid, data):
    from PIL import Image
    pic = Image.open(io.BytesIO(data)).convert("RGB")
    side = min(pic.size)
    left, top = (pic.width - side) // 2, (pic.height - side) // 2
    pic = pic.crop((left, top, left + side, top + side)).resize((240, 240))
    buf = io.BytesIO()
    pic.save(buf, "JPEG", quality=80)
    text = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    db.run("UPDATE farmers SET photo = %s WHERE id = %s", (text, uid))
 
 
@st.dialog("My photo")
def photo_dialog(uid):
    st.caption("Only you see this photo, on your own pages. It is never shown to other users.")
    how = st.radio("How?", ["Upload a photo", "Take a photo"], horizontal=True,
                   label_visibility="collapsed")
    image = (st.file_uploader("Choose a picture", type=["jpg", "jpeg", "png"])
             if how == "Upload a photo" else st.camera_input("Take a photo"))
    if image is not None and st.button("Save photo", type="primary", width="stretch"):
        save_photo(uid, image.getvalue())
        st.rerun()
    if st.session_state.get("photo") and st.button("Remove my photo", width="stretch"):
        db.run("UPDATE farmers SET photo = NULL WHERE id = %s", (uid,))
        st.rerun()
