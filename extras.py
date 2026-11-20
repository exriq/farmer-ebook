"""Phase 6: extra database columns, the farmer photo, and pieces shared by several pages.
Nothing in db.py has to change."""
import base64
import io
from datetime import date

import streamlit as st

import config
import db

# Columns the record pages may now save (db.py reads these lists)
for _table, _cols in {
        "money": ["enterprise", "product", "quantity", "unit"],
        "crop_records": ["sold", "home_use", "crop_id", "product", "detail", "cost"],
        "livestock_records": ["sold", "home_use", "animal_id", "subject", "detail", "cost"]}.items():
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
    "ALTER TABLE money ADD COLUMN IF NOT EXISTS product TEXT",
    "ALTER TABLE money ADD COLUMN IF NOT EXISTS quantity DOUBLE PRECISION",
    "ALTER TABLE money ADD COLUMN IF NOT EXISTS unit TEXT",
    "ALTER TABLE crop_records ADD COLUMN IF NOT EXISTS crop_id INTEGER",
    "ALTER TABLE crop_records ADD COLUMN IF NOT EXISTS product TEXT",
    "ALTER TABLE crop_records ADD COLUMN IF NOT EXISTS detail TEXT",
    "ALTER TABLE crop_records ADD COLUMN IF NOT EXISTS cost DOUBLE PRECISION",
    "ALTER TABLE livestock_records ADD COLUMN IF NOT EXISTS animal_id INTEGER",
    "ALTER TABLE livestock_records ADD COLUMN IF NOT EXISTS subject TEXT",
    "ALTER TABLE livestock_records ADD COLUMN IF NOT EXISTS detail TEXT",
    "ALTER TABLE livestock_records ADD COLUMN IF NOT EXISTS cost DOUBLE PRECISION",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS planting_method TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS growing_system TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS seed_source TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS intercrop TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS products TEXT",
    "ALTER TABLE farmer_crops ADD COLUMN IF NOT EXISTS photo TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS entry_type TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS tag TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS name TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS sex TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS birth_date DATE",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS colour TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS weight_kg DOUBLE PRECISION",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS products TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS photo TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS max_fish DOUBLE PRECISION",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS harvest_freq TEXT",
    "ALTER TABLE farm_animals ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active'",
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
def _has(x):
    return x is not None and x == x


def _t(x):
    return str(x) if _has(x) else ""


def crops(fid):
    return db.table("SELECT id, crop_group, crop, acres, purpose, variety, plot, planted_on, "
                    "planting_method, growing_system, seed_source, intercrop, products, photo "
                    "FROM farmer_crops WHERE farmer_id = %s ORDER BY crop", (fid,))


def animals(fid):
    """Animals, groups and fish units still on the farm (sold or dead ones are hidden)."""
    return db.table("SELECT id, animal, entry_type, system, breed, head_count, purpose, tag, name, "
                    "sex, birth_date, colour, weight_kg, products, photo, capacity, max_fish, "
                    "size_m, feeds_per_day, stocked_on, harvest_freq FROM farm_animals "
                    "WHERE farmer_id = %s AND COALESCE(status, 'Active') = 'Active' "
                    "ORDER BY animal, id", (fid,))


CROP_COLS = ["crop_group", "crop", "acres", "purpose", "variety", "plot", "planted_on",
             "planting_method", "growing_system", "seed_source", "intercrop", "products", "photo"]
ANIMAL_COLS = ["animal", "entry_type", "system", "breed", "head_count", "purpose", "tag", "name",
               "sex", "birth_date", "colour", "weight_kg", "products", "photo", "capacity",
               "max_fish", "size_m", "feeds_per_day", "stocked_on", "harvest_freq"]


def save_crop(fid, **f):
    cols = [c for c in CROP_COLS if c in f]
    sets = ", ".join(
        f"{c} = COALESCE(EXCLUDED.{c}, farmer_crops.{c})" if c == "photo"
        else f"{c} = EXCLUDED.{c}" for c in cols if c != "crop")
    db.run(f"INSERT INTO farmer_crops (farmer_id, {', '.join(cols)}) "
           f"VALUES ({', '.join(['%s'] * (len(cols) + 1))}) "
           f"ON CONFLICT (farmer_id, crop) DO UPDATE SET {sets}",
           [fid] + [f[c] for c in cols])


def save_animal(fid, **f):
    cols = [c for c in ANIMAL_COLS if c in f]
    db.run(f"INSERT INTO farm_animals (farmer_id, {', '.join(cols)}) "
           f"VALUES ({', '.join(['%s'] * (len(cols) + 1))})",
           [fid] + [f[c] for c in cols])


def tag_taken(fid, animal, tag):
    got = db.rows("SELECT 1 FROM farm_animals WHERE farmer_id = %s AND animal = %s "
                  "AND LOWER(tag) = LOWER(%s) AND COALESCE(status, 'Active') = 'Active'",
                  (fid, animal, tag))
    return bool(got)


# ---------- readable names, ages and products ----------
def split_products(text):
    return [p for p in text.split("|") if p] if isinstance(text, str) else []


def crop_label(r):
    bits = [r.crop + (f" ({r.variety})" if _has(r.variety) and r.variety else "")]
    if _has(r.plot) and r.plot:
        bits.append(r.plot)
    bits.append(f"{r.acres:,.2f} acres")
    return " – ".join(bits)


def animal_label(r):
    if _t(r.entry_type) == "single":
        who = " · ".join(b for b in (_t(r.tag), _t(r.name)) if b)
        return f"{r.animal} – {who}"
    n = int(r.head_count)
    if r.animal == "Fish":
        unit = _t(r.system).lower() or "pond"
        return f"Fish – {_t(r.name) or 'my ' + unit + 's'} ({n} {unit}{'s' if n != 1 else ''})"
    return f"{r.animal} – {_t(r.name) or 'group'} ({n} animals)"


def age_text(birth):
    if not _has(birth):
        return ""
    days = max((date.today() - birth).days, 0)
    years, months = divmod(int(days / 30.44), 12)
    if years and months:
        return f"{years} yr {months} mo"
    if years:
        return f"{years} yr"
    return f"{months} mo" if months else f"{days} days"


def products_of(fid, name):
    """The products the farmer said this crop or animal gives (used for sales)."""
    out = []
    c, a = crops(fid), animals(fid)
    for text in c.loc[c["crop"] == name, "products"]:
        out += split_products(text)
    for text in a.loc[a["animal"] == name, "products"]:
        out += split_products(text)
    if not out:
        if name in config.ANIMAL_PRODUCTS:
            out = list(config.ANIMAL_PRODUCTS[name])
        else:
            groups = c.loc[c["crop"] == name, "crop_group"].tolist()
            out = list(config.CROP_PRODUCTS.get(groups[0] if groups else "", ["Harvested produce"]))
    return list(dict.fromkeys(out))


# ---------- keeping the farm list in step with the records ----------
_GAIN = ("Bought", "Calved", "Kidded", "Lambed", "Farrowed", "Kindled", "Hatched")


def apply_event(fid, animal_id, activity, count, when, weight=None):
    """Updates the farm list after a livestock record: counts, status, weight, stocking date."""
    got = db.rows("SELECT animal, entry_type FROM farm_animals WHERE id = %s AND farmer_id = %s",
                  (animal_id, fid))
    if not got:
        return
    animal, kind = got[0]
    if activity == "Weighed" and weight:
        db.run("UPDATE farm_animals SET weight_kg = %s WHERE id = %s AND farmer_id = %s",
               (weight, animal_id, fid))
    if animal == "Fish":
        if activity == "Stocked fingerlings":
            db.run("UPDATE farm_animals SET stocked_on = %s WHERE id = %s AND farmer_id = %s",
                   (when, animal_id, fid))
        return
    if kind == "single":
        if activity in ("Died", "Sold"):
            db.run("UPDATE farm_animals SET status = %s WHERE id = %s AND farmer_id = %s",
                   (activity, animal_id, fid))
        return
    delta = count if activity in _GAIN else -count if activity in ("Died", "Sold") else 0
    if delta:
        db.run("UPDATE farm_animals SET head_count = GREATEST(head_count + %s, 0) "
               "WHERE id = %s AND farmer_id = %s", (int(delta), animal_id, fid))


def last_event(fid, animal_id, activity):
    got = db.rows("SELECT MAX(entry_date) FROM livestock_records WHERE farmer_id = %s "
                  "AND animal_id = %s AND activity = %s", (fid, animal_id, activity))
    return got[0][0] if got and got[0][0] else None


# ---------- pictures of crops and animals ----------
def shrink(data, side=480):
    """A small JPEG, as text, ready to save in the database."""
    from PIL import Image
    pic = Image.open(io.BytesIO(data)).convert("RGB")
    pic.thumbnail((side, side))
    buf = io.BytesIO()
    pic.save(buf, "JPEG", quality=75)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def photo_bytes(text):
    if not isinstance(text, str) or "," not in text:
        return None
    try:
        return base64.b64decode(text.split(",", 1)[1])
    except Exception:
        return None


def photo_input(what):
    """The last question on a registration form. Returns a small picture as text, or None."""
    st.markdown("**📷 Picture (optional)**")
    how = st.radio("Picture", ["No picture", "Take a picture now", "Choose one from my phone"],
                   horizontal=True, label_visibility="collapsed", key=f"pic_how_{what}")
    image = None
    if how == "Take a picture now":
        image = st.camera_input(f"Take a picture of the {what}", key=f"pic_cam_{what}")
    elif how == "Choose one from my phone":
        image = st.file_uploader("Choose a picture", type=["jpg", "jpeg", "png"],
                                 key=f"pic_up_{what}")
    return shrink(image.getvalue()) if image is not None else None


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
