"""Everything that talks to the Supabase database lives here."""
import hashlib
import hmac
import os
from contextlib import contextmanager

import numpy as np
import pandas as pd
import psycopg2
import streamlit as st
from psycopg2.extensions import AsIs, register_adapter

import config

# Which columns each record table accepts (keeps the app safe from bad input)
RECORD_TABLES = {
    "money": ["kind", "category", "description", "amount"],
    "crop_records": ["crop", "activity", "quantity", "unit", "note"],
    "livestock_records": ["animal", "activity", "quantity", "unit", "note"],
    "inventory_moves": ["item", "category", "movement", "quantity", "unit", "cost"],
    "labour": ["worker_type", "activity", "people_days", "cost"],
}
# Staff tables: who uploaded each row
STAFF_TABLES = {
    "market_prices": "uploaded_by",
    "input_prices": "uploaded_by",
    "opportunities": "posted_by",
}
PROFILE_FIELDS = ["name", "gender", "sub_county", "ward", "village", "farming_type",
                  "latitude", "longitude", "share_contact", "in_directory"]

_ready = False

# Numbers that come out of tables are numpy numbers. Teach the database driver
# to accept them, so a record number can never cause an error.
register_adapter(np.int64, lambda value: AsIs(int(value)))
register_adapter(np.int32, lambda value: AsIs(int(value)))


# ---------- CONNECTION HELPERS ----------
@contextmanager
def get_conn():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"], connect_timeout=15)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def rows(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def table(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        data = cur.fetchall()
    return pd.DataFrame(data, columns=cols)


# ---------- CREATE THE TABLES (runs once when the app starts) ----------
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS farmers (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        gender TEXT, sub_county TEXT, ward TEXT, village TEXT,
        farming_type TEXT NOT NULL DEFAULT 'Crops',
        latitude DOUBLE PRECISION, longitude DOUBLE PRECISION,
        role TEXT NOT NULL DEFAULT 'farmer',
        active BOOLEAN NOT NULL DEFAULT TRUE,
        share_contact BOOLEAN NOT NULL DEFAULT FALSE,
        in_directory BOOLEAN NOT NULL DEFAULT TRUE,
        password_hash TEXT NOT NULL,
        consented_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS land_holdings (
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        tenure TEXT NOT NULL,
        acres DOUBLE PRECISION NOT NULL DEFAULT 0,
        PRIMARY KEY (farmer_id, tenure))""",
    """CREATE TABLE IF NOT EXISTS farm_profile (
        farmer_id INTEGER PRIMARY KEY REFERENCES farmers(id) ON DELETE CASCADE,
        active_acres DOUBLE PRECISION NOT NULL DEFAULT 0,
        fertility TEXT NOT NULL DEFAULT 'Medium',
        rainfall TEXT NOT NULL DEFAULT 'Fair')""",
    """CREATE TABLE IF NOT EXISTS farmer_crops (
        id SERIAL PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        crop_group TEXT, crop TEXT NOT NULL,
        acres DOUBLE PRECISION NOT NULL DEFAULT 0,
        UNIQUE (farmer_id, crop))""",
    """CREATE TABLE IF NOT EXISTS farm_animals (
        id SERIAL PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        animal TEXT NOT NULL, system TEXT, breed TEXT,
        head_count INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS crop_records (
        id SERIAL PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        entry_date DATE NOT NULL,
        crop TEXT, activity TEXT, quantity DOUBLE PRECISION, unit TEXT, note TEXT)""",
    """CREATE TABLE IF NOT EXISTS livestock_records (
        id SERIAL PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        entry_date DATE NOT NULL,
        animal TEXT, activity TEXT, quantity DOUBLE PRECISION, unit TEXT, note TEXT)""",
    """CREATE TABLE IF NOT EXISTS money (
        id SERIAL PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        entry_date DATE NOT NULL,
        kind TEXT, category TEXT, description TEXT, amount DOUBLE PRECISION)""",
    """CREATE TABLE IF NOT EXISTS inventory_moves (
        id SERIAL PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        entry_date DATE NOT NULL,
        item TEXT, category TEXT, movement TEXT,
        quantity DOUBLE PRECISION, unit TEXT, cost DOUBLE PRECISION DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS labour (
        id SERIAL PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        entry_date DATE NOT NULL,
        worker_type TEXT, activity TEXT,
        people_days DOUBLE PRECISION, cost DOUBLE PRECISION DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS market_prices (
        id SERIAL PRIMARY KEY,
        entry_date DATE NOT NULL,
        sub_county TEXT, ward TEXT, market TEXT,
        product TEXT, unit TEXT, price DOUBLE PRECISION, demand TEXT,
        uploaded_by INTEGER REFERENCES farmers(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS input_prices (
        id SERIAL PRIMARY KEY,
        entry_date DATE NOT NULL,
        sub_county TEXT, agrovet TEXT,
        item TEXT, unit TEXT, price DOUBLE PRECISION,
        uploaded_by INTEGER REFERENCES farmers(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS opportunities (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL, provider TEXT, kind TEXT, details TEXT,
        deadline DATE, sub_county TEXT, contact TEXT,
        closed BOOLEAN NOT NULL DEFAULT FALSE,
        posted_by INTEGER REFERENCES farmers(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS listings (
        id SERIAL PRIMARY KEY,
        farmer_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        product TEXT NOT NULL, quantity DOUBLE PRECISION, unit TEXT,
        price DOUBLE PRECISION, details TEXT,
        status TEXT NOT NULL DEFAULT 'Open',
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        sender_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        recipient_id INTEGER NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
        body TEXT NOT NULL,
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS yield_reference (
        crop TEXT PRIMARY KEY,
        kg_per_acre DOUBLE PRECISION NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_crop_rec ON crop_records (farmer_id, entry_date)",
    "CREATE INDEX IF NOT EXISTS idx_live_rec ON livestock_records (farmer_id, entry_date)",
    "CREATE INDEX IF NOT EXISTS idx_money ON money (farmer_id, entry_date)",
    "CREATE INDEX IF NOT EXISTS idx_msg ON messages (sender_id, recipient_id)",
    "CREATE INDEX IF NOT EXISTS idx_mp ON market_prices (sub_county, entry_date)",
]


def init_db():
    global _ready
    if _ready:
        return
    with get_conn() as conn, conn.cursor() as cur:
        for statement in SCHEMA:
            cur.execute(statement)
        for crop, kg in config.CROP_REFERENCE_YIELD.items():
            cur.execute(
                "INSERT INTO yield_reference (crop, kg_per_acre) VALUES (%s, %s) "
                "ON CONFLICT (crop) DO NOTHING", (crop, kg))
    _ready = True


# ---------- PASSWORDS ----------
def _hash(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + "$" + digest.hex()


def _check(password, stored):
    salt_hex, _ = stored.split("$")
    return hmac.compare_digest(_hash(password, bytes.fromhex(salt_hex)), stored)


# ---------- FARMERS ----------
def create_farmer(info, password):
    """info is a dict. Returns True, or False if the phone is already used."""
    try:
        run("""INSERT INTO farmers
               (name, phone, gender, sub_county, ward, village, farming_type,
                latitude, longitude, share_contact, in_directory,
                password_hash, consented_at)
               VALUES (%(name)s, %(phone)s, %(gender)s, %(sub_county)s, %(ward)s,
                       %(village)s, %(farming_type)s, %(latitude)s, %(longitude)s,
                       %(share_contact)s, %(in_directory)s, %(pw)s, now())""",
            {**info, "pw": _hash(password)})
        return True
    except psycopg2.errors.UniqueViolation:
        return False


def get_farmer(farmer_id):
    """The person's details as a dict (never includes the password)."""
    df = table("""SELECT id, name, phone, gender, sub_county, ward, village,
                  farming_type, latitude, longitude, role, active,
                  share_contact, in_directory
                  FROM farmers WHERE id = %s""", (farmer_id,))
    return None if df.empty else df.iloc[0].to_dict()


def check_login(phone, password):
    found = rows("SELECT id, password_hash FROM farmers WHERE phone = %s", (phone,))
    if found and _check(password, found[0][1]):
        return get_farmer(found[0][0])
    return None


def update_profile(farmer_id, fields):
    keys = [k for k in fields if k in PROFILE_FIELDS]
    if not keys:
        return
    sets = ", ".join(f"{k} = %({k})s" for k in keys)
    params = {k: fields[k] for k in keys}
    params["fid"] = farmer_id
    run(f"UPDATE farmers SET {sets} WHERE id = %(fid)s", params)


def change_password(farmer_id, old, new):
    found = rows("SELECT password_hash FROM farmers WHERE id = %s", (farmer_id,))
    if not found or not _check(old, found[0][0]):
        return False
    run("UPDATE farmers SET password_hash = %s WHERE id = %s", (_hash(new), farmer_id))
    return True


# ---------- FARM PROFILE: LAND, CROPS, ANIMALS ----------
def get_land(farmer_id):
    found = rows("SELECT tenure, acres FROM land_holdings WHERE farmer_id = %s",
                 (farmer_id,))
    return {t: a for t, a in found}


def get_farm_profile(farmer_id):
    found = rows("""SELECT active_acres, fertility, rainfall FROM farm_profile
                    WHERE farmer_id = %s""", (farmer_id,))
    if not found:
        return {"active_acres": 0.0, "fertility": "Medium", "rainfall": "Fair"}
    return {"active_acres": found[0][0], "fertility": found[0][1],
            "rainfall": found[0][2]}


def save_land_and_profile(farmer_id, land, active_acres, fertility, rainfall):
    with get_conn() as conn, conn.cursor() as cur:
        for tenure, acres in land.items():
            cur.execute("""INSERT INTO land_holdings (farmer_id, tenure, acres)
                           VALUES (%s, %s, %s)
                           ON CONFLICT (farmer_id, tenure)
                           DO UPDATE SET acres = EXCLUDED.acres""",
                        (farmer_id, tenure, acres))
        cur.execute("""INSERT INTO farm_profile
                       (farmer_id, active_acres, fertility, rainfall)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (farmer_id) DO UPDATE SET
                       active_acres = EXCLUDED.active_acres,
                       fertility = EXCLUDED.fertility,
                       rainfall = EXCLUDED.rainfall""",
                    (farmer_id, active_acres, fertility, rainfall))


def add_farmer_crop(farmer_id, group, crop, acres):
    run("""INSERT INTO farmer_crops (farmer_id, crop_group, crop, acres)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (farmer_id, crop) DO UPDATE SET
           acres = EXCLUDED.acres, crop_group = EXCLUDED.crop_group""",
        (farmer_id, group, crop, acres))


def get_farmer_crops(farmer_id):
    return table("""SELECT id, crop_group, crop, acres FROM farmer_crops
                    WHERE farmer_id = %s ORDER BY crop_group, crop""", (farmer_id,))


def delete_farmer_crop(farmer_id, row_id):
    run("DELETE FROM farmer_crops WHERE id = %s AND farmer_id = %s",
        (row_id, farmer_id))


def add_farm_animal(farmer_id, animal, system, breed, head_count):
    run("""INSERT INTO farm_animals (farmer_id, animal, system, breed, head_count)
           VALUES (%s, %s, %s, %s, %s)""",
        (farmer_id, animal, system, breed, head_count))


def get_farm_animals(farmer_id):
    return table("""SELECT id, animal, system, breed, head_count FROM farm_animals
                    WHERE farmer_id = %s AND COALESCE(status, 'Active') = 'Active'
                    ORDER BY animal, id""", (farmer_id,))


def delete_farm_animal(farmer_id, row_id):
    run("DELETE FROM farm_animals WHERE id = %s AND farmer_id = %s",
        (row_id, farmer_id))


# ---------- DAILY RECORDS (money, crops, livestock, inputs, labour) ----------
def add_record(tbl, farmer_id, entry_date, **fields):
    allowed = RECORD_TABLES[tbl]
    cols = [c for c in fields if c in allowed]
    names = ", ".join(["farmer_id", "entry_date"] + cols)
    marks = ", ".join(["%s"] * (2 + len(cols)))
    values = [farmer_id, entry_date] + [fields[c] for c in cols]
    run(f"INSERT INTO {tbl} ({names}) VALUES ({marks})", values)


def get_records(tbl, farmer_id, limit=None):
    cols = ["id", "entry_date"] + RECORD_TABLES[tbl]
    sql = (f"SELECT {', '.join(cols)} FROM {tbl} WHERE farmer_id = %s "
           "ORDER BY entry_date DESC, id DESC")
    if limit:
        sql += f" LIMIT {int(limit)}"
    return table(sql, (farmer_id,))


def delete_record(tbl, farmer_id, record_id):
    if tbl not in RECORD_TABLES:
        return 0
    return run(f"DELETE FROM {tbl} WHERE id = %s AND farmer_id = %s",
               (record_id, farmer_id))


# ---------- MARKET AND INPUT PRICES, OPPORTUNITIES (coordinators) ----------
def add_market_prices(entries, uploader_id):
    with get_conn() as conn, conn.cursor() as cur:
        for e in entries:
            cur.execute("""INSERT INTO market_prices
                (entry_date, sub_county, ward, market, product, unit, price,
                 demand, uploaded_by)
                VALUES (%(entry_date)s, %(sub_county)s, %(ward)s, %(market)s,
                        %(product)s, %(unit)s, %(price)s, %(demand)s, %(by)s)""",
                        {**e, "by": uploader_id})


def get_market_prices(sub_county=None, uploader_id=None, limit=None):
    sql = """SELECT id, entry_date, sub_county, ward, market, product, unit,
             price, demand FROM market_prices WHERE TRUE"""
    params = []
    if sub_county:
        sql += " AND sub_county = %s"
        params.append(sub_county)
    if uploader_id:
        sql += " AND uploaded_by = %s"
        params.append(uploader_id)
    sql += " ORDER BY entry_date DESC, id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return table(sql, params)


def add_input_prices(entries, uploader_id):
    with get_conn() as conn, conn.cursor() as cur:
        for e in entries:
            cur.execute("""INSERT INTO input_prices
                (entry_date, sub_county, agrovet, item, unit, price, uploaded_by)
                VALUES (%(entry_date)s, %(sub_county)s, %(agrovet)s, %(item)s,
                        %(unit)s, %(price)s, %(by)s)""", {**e, "by": uploader_id})


def get_input_prices(sub_county=None, uploader_id=None, limit=None):
    sql = """SELECT id, entry_date, sub_county, agrovet, item, unit, price
             FROM input_prices WHERE TRUE"""
    params = []
    if sub_county:
        sql += " AND sub_county = %s"
        params.append(sub_county)
    if uploader_id:
        sql += " AND uploaded_by = %s"
        params.append(uploader_id)
    sql += " ORDER BY entry_date DESC, id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return table(sql, params)


def add_opportunity(info, poster_id):
    run("""INSERT INTO opportunities
           (title, provider, kind, details, deadline, sub_county, contact, posted_by)
           VALUES (%(title)s, %(provider)s, %(kind)s, %(details)s, %(deadline)s,
                   %(sub_county)s, %(contact)s, %(by)s)""", {**info, "by": poster_id})


def get_opportunities(sub_county=None, only_open=True, poster_id=None):
    sql = """SELECT id, title, provider, kind, details, deadline, sub_county, contact
             FROM opportunities WHERE TRUE"""
    params = []
    if only_open:
        sql += " AND NOT closed AND (deadline IS NULL OR deadline >= CURRENT_DATE)"
    if sub_county:
        sql += " AND (sub_county = %s OR sub_county = %s)"
        params += [sub_county, config.ALL_SUB_COUNTIES]
    if poster_id:
        sql += " AND posted_by = %s"
        params.append(poster_id)
    sql += " ORDER BY deadline NULLS LAST, id DESC"
    return table(sql, params)


def delete_staff_row(tbl, row_id, user):
    """Coordinators can delete their own uploads. Admins can delete any."""
    column = STAFF_TABLES.get(tbl)
    if not column:
        return 0
    if user["role"] == "admin":
        return run(f"DELETE FROM {tbl} WHERE id = %s", (row_id,))
    return run(f"DELETE FROM {tbl} WHERE id = %s AND {column} = %s",
               (row_id, user["id"]))


# ---------- MARKETPLACE AND DIRECTORY ----------
def add_listing(farmer_id, product, quantity, unit, price, details):
    run("""INSERT INTO listings (farmer_id, product, quantity, unit, price, details)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (farmer_id, product, quantity, unit, price, details))


def get_listings(sub_county=None, search=None, farmer_id=None):
    """Phone numbers only come back when the seller chose to share them."""
    sql = """SELECT l.id, l.farmer_id, l.product, l.quantity, l.unit, l.price,
             l.details, l.status, l.created_at, f.name, f.sub_county, f.ward,
             f.village,
             CASE WHEN f.share_contact THEN f.phone ELSE NULL END AS phone
             FROM listings l JOIN farmers f ON f.id = l.farmer_id
             WHERE f.active"""
    params = []
    if farmer_id:
        sql += " AND l.farmer_id = %s"
        params.append(farmer_id)
    else:
        sql += " AND l.status = 'Open'"
    if sub_county:
        sql += " AND f.sub_county = %s"
        params.append(sub_county)
    if search:
        sql += " AND l.product ILIKE %s"
        params.append(f"%{search}%")
    sql += " ORDER BY l.created_at DESC LIMIT 100"
    return table(sql, params)


def mark_listing_sold(listing_id, farmer_id):
    run("UPDATE listings SET status = 'Sold' WHERE id = %s AND farmer_id = %s",
        (listing_id, farmer_id))


def delete_listing(listing_id, user):
    if user["role"] == "admin":
        return run("DELETE FROM listings WHERE id = %s", (listing_id,))
    return run("DELETE FROM listings WHERE id = %s AND farmer_id = %s",
               (listing_id, user["id"]))


def get_directory(me, sub_county=None, farming_type=None):
    sql = """SELECT f.id, f.name, f.role, f.sub_county, f.ward, f.village,
             f.farming_type,
             CASE WHEN f.share_contact THEN f.phone ELSE NULL END AS phone,
             (SELECT string_agg(c.crop, ', ' ORDER BY c.crop)
                FROM farmer_crops c WHERE c.farmer_id = f.id) AS crops,
             (SELECT string_agg(DISTINCT a.animal, ', ')
                FROM farm_animals a WHERE a.farmer_id = f.id) AS animals
             FROM farmers f WHERE f.in_directory AND f.active AND f.id <> %s"""
    params = [me]
    if sub_county:
        sql += " AND f.sub_county = %s"
        params.append(sub_county)
    if farming_type:
        sql += " AND f.farming_type = %s"
        params.append(farming_type)
    sql += " ORDER BY f.name LIMIT 200"
    return table(sql, params)


# ---------- MESSAGES ----------
def send_message(sender_id, recipient_id, body):
    run("INSERT INTO messages (sender_id, recipient_id, body) VALUES (%s, %s, %s)",
        (sender_id, recipient_id, body[:1000]))


def get_thread(me, other):
    return table("""SELECT id, sender_id, body, created_at FROM messages
                    WHERE (sender_id = %(me)s AND recipient_id = %(o)s)
                       OR (sender_id = %(o)s AND recipient_id = %(me)s)
                    ORDER BY created_at, id LIMIT 300""", {"me": me, "o": other})


def mark_read(me, other):
    run("""UPDATE messages SET is_read = TRUE
           WHERE recipient_id = %s AND sender_id = %s AND NOT is_read""", (me, other))


def get_conversations(me):
    return table("""SELECT p.id, p.name, MAX(m.created_at) AS last_time,
        SUM(CASE WHEN m.recipient_id = %(me)s AND NOT m.is_read THEN 1 ELSE 0 END)
            AS unread
        FROM messages m
        JOIN farmers p ON p.id = CASE WHEN m.sender_id = %(me)s
                                      THEN m.recipient_id ELSE m.sender_id END
        WHERE m.sender_id = %(me)s OR m.recipient_id = %(me)s
        GROUP BY p.id, p.name ORDER BY last_time DESC""", {"me": me})


def get_name(farmer_id):
    found = rows("SELECT name FROM farmers WHERE id = %s", (farmer_id,))
    return found[0][0] if found else None


# ---------- ADMIN ----------
def list_users():
    return table("""SELECT f.id, f.name, f.phone, f.gender, f.sub_county, f.ward,
                    f.village, f.farming_type, f.role, f.active,
                    COALESCE(p.active_acres, 0) AS active_acres, f.created_at
                    FROM farmers f LEFT JOIN farm_profile p ON p.farmer_id = f.id
                    ORDER BY f.id""")


def set_role(phone, role, sub_county=None):
    if role not in config.ROLES:
        return 0
    if sub_county:
        return run("UPDATE farmers SET role = %s, sub_county = %s WHERE phone = %s",
                   (role, sub_county, phone))
    return run("UPDATE farmers SET role = %s WHERE phone = %s", (role, phone))


def set_active(phone, active):
    return run("UPDATE farmers SET active = %s WHERE phone = %s", (active, phone))


def reset_password(phone, new_password):
    return run("UPDATE farmers SET password_hash = %s WHERE phone = %s",
               (_hash(new_password), phone))


def get_yield_reference():
    return table("SELECT crop, kg_per_acre FROM yield_reference ORDER BY crop")


def save_yield_reference(df):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM yield_reference")
        for _, r in df.iterrows():
            cur.execute("INSERT INTO yield_reference (crop, kg_per_acre) "
                        "VALUES (%s, %s) ON CONFLICT (crop) DO UPDATE "
                        "SET kg_per_acre = EXCLUDED.kg_per_acre",
                        (r["crop"], float(r["kg_per_acre"])))
