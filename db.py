import hashlib
import hmac
import os
from contextlib import contextmanager

import pandas as pd
import psycopg2
import streamlit as st

# Which columns each table accepts (keeps the app safe from bad input)
TABLES = {
    "money": ["kind", "category", "description", "amount"],
    "crops": ["crop", "activity", "quantity", "unit", "note"],
    "livestock": ["animal", "activity", "quantity", "unit", "note"],
}

_ready = False


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


def init_db():
    global _ready
    if _ready:
        return
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS farmers (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                sub_county TEXT,
                types TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS money (
                id SERIAL PRIMARY KEY,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id),
                entry_date DATE NOT NULL,
                kind TEXT,
                category TEXT,
                description TEXT,
                amount DOUBLE PRECISION
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crops (
                id SERIAL PRIMARY KEY,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id),
                entry_date DATE NOT NULL,
                crop TEXT,
                activity TEXT,
                quantity DOUBLE PRECISION,
                unit TEXT,
                note TEXT
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS livestock (
                id SERIAL PRIMARY KEY,
                farmer_id INTEGER NOT NULL REFERENCES farmers(id),
                entry_date DATE NOT NULL,
                animal TEXT,
                activity TEXT,
                quantity DOUBLE PRECISION,
                unit TEXT,
                note TEXT
            )""")
    _ready = True


def _hash(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + "$" + digest.hex()


def _check(password, stored):
    salt_hex, _ = stored.split("$")
    return hmac.compare_digest(_hash(password, bytes.fromhex(salt_hex)), stored)


def _clean_phone(phone):
    return "".join(phone.split())


def create_farmer(name, phone, sub_county, types, password):
    phone = _clean_phone(phone)
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO farmers (name, phone, sub_county, types, password_hash) "
                "VALUES (%s, %s, %s, %s, %s)",
                (name.strip(), phone, sub_county, ",".join(types), _hash(password)),
            )
        return True
    except psycopg2.errors.UniqueViolation:
        return False


def check_login(phone, password):
    phone = _clean_phone(phone)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, types, password_hash FROM farmers WHERE phone = %s",
            (phone,),
        )
        row = cur.fetchone()
    if row and _check(password, row[3]):
        return (row[0], row[1], row[2].split(","))
    return None


def add_record(table, farmer_id, entry_date, **fields):
    allowed = TABLES[table]
    cols = [c for c in fields if c in allowed]
    names = ", ".join(["farmer_id", "entry_date"] + cols)
    marks = ", ".join(["%s"] * (2 + len(cols)))
    values = [farmer_id, entry_date] + [fields[c] for c in cols]
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", values)


def get_records(table, farmer_id):
    cols = ["entry_date"] + TABLES[table]
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(cols)} FROM {table} "
            "WHERE farmer_id = %s ORDER BY entry_date DESC, id DESC",
            (farmer_id,),
        )
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)