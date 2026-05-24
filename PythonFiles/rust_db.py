# rust_db.py - Python SQLite fallback (MSVC linker yokken kullanılır)
# -*- coding: utf-8 -*-
"""
Rust tabanlı rust_db modülünün Python karşılığı.
Aynı API'yi sqlite3 modülü ile gerçekler; veriler diske kalıcı olarak kaydedilir.
"""

import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone


def _to_iso_date(date_str):
    """dd.mm.yyyy  →  yyyy-mm-dd"""
    if not date_str:
        return date_str
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date_str


def _to_display_date(date_str):
    """yyyy-mm-dd  →  dd.mm.yyyy"""
    if not date_str:
        return date_str
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return date_str


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


_INVOICE_COLS = (
    "id", "fatura_no", "irsaliye_no", "tarih", "firma", "malzeme",
    "miktar", "matrah", "toplam_tutar_tl", "toplam_tutar_usd",
    "toplam_tutar_eur", "birim", "kdv_yuzdesi", "kdv_tutari",
    "kdv_dahil", "usd_rate", "eur_rate", "updated_at", "created_at",
)

_MONTH_COLS = (
    "ocak", "subat", "mart", "nisan", "mayis", "haziran",
    "temmuz", "agustos", "eylul", "ekim", "kasim", "aralik",
)


def _row_to_invoice(row):
    if row is None:
        return None
    d = dict(zip(_INVOICE_COLS, row))
    d["tarih"] = _to_display_date(d.get("tarih"))
    return d


def _row_to_expense(row):
    if row is None:
        return None
    cols = ("id", "yil") + _MONTH_COLS
    return dict(zip(cols, row))


class Database:
    def __init__(self):
        self._lock = threading.Lock()
        self._invoices_con = None
        self._settings_con = None
        self._history_con = None

    # ------------------------------------------------------------------
    # BAĞLANTI & TABLO
    # ------------------------------------------------------------------

    def init_connections(self):
        db_dir = os.path.join(os.getcwd(), "Database")
        os.makedirs(db_dir, exist_ok=True)

        self._invoices_con = sqlite3.connect(
            os.path.join(db_dir, "invoices.db"), check_same_thread=False
        )
        self._invoices_con.execute("PRAGMA journal_mode=WAL")

        self._settings_con = sqlite3.connect(
            os.path.join(db_dir, "settings.db"), check_same_thread=False
        )
        self._settings_con.execute("PRAGMA journal_mode=WAL")

        self._history_con = sqlite3.connect(
            os.path.join(db_dir, "history.db"), check_same_thread=False
        )
        self._history_con.execute("PRAGMA journal_mode=WAL")

    def create_tables(self):
        with self._lock:
            c = self._invoices_con
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS income_invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fatura_no TEXT NOT NULL,
                    irsaliye_no TEXT,
                    tarih TEXT,
                    firma TEXT,
                    malzeme TEXT,
                    miktar TEXT,
                    matrah REAL DEFAULT 0.0,
                    toplam_tutar_tl REAL,
                    toplam_tutar_usd REAL,
                    toplam_tutar_eur REAL,
                    birim TEXT,
                    kdv_yuzdesi REAL,
                    kdv_tutari REAL,
                    kdv_dahil INTEGER DEFAULT 0,
                    usd_rate REAL,
                    eur_rate REAL,
                    updated_at TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS expense_invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fatura_no TEXT NOT NULL,
                    irsaliye_no TEXT,
                    tarih TEXT,
                    firma TEXT,
                    malzeme TEXT,
                    miktar TEXT,
                    matrah REAL DEFAULT 0.0,
                    toplam_tutar_tl REAL,
                    toplam_tutar_usd REAL,
                    toplam_tutar_eur REAL,
                    birim TEXT,
                    kdv_yuzdesi REAL,
                    kdv_tutari REAL,
                    kdv_dahil INTEGER DEFAULT 0,
                    usd_rate REAL,
                    eur_rate REAL,
                    updated_at TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS general_expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    yil INTEGER,
                    ocak REAL DEFAULT 0, subat REAL DEFAULT 0,
                    mart REAL DEFAULT 0, nisan REAL DEFAULT 0,
                    mayis REAL DEFAULT 0, haziran REAL DEFAULT 0,
                    temmuz REAL DEFAULT 0, agustos REAL DEFAULT 0,
                    eylul REAL DEFAULT 0, ekim REAL DEFAULT 0,
                    kasim REAL DEFAULT 0, aralik REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS corporate_tax (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    yil INTEGER,
                    ocak REAL DEFAULT 0, subat REAL DEFAULT 0,
                    mart REAL DEFAULT 0, nisan REAL DEFAULT 0,
                    mayis REAL DEFAULT 0, haziran REAL DEFAULT 0,
                    temmuz REAL DEFAULT 0, agustos REAL DEFAULT 0,
                    eylul REAL DEFAULT 0, ekim REAL DEFAULT 0,
                    kasim REAL DEFAULT 0, aralik REAL DEFAULT 0
                );
                """
            )
            c.commit()

            # Migration: matrah sütunu yoksa ekle
            for tbl in ("income_invoices", "expense_invoices"):
                try:
                    c.execute(f"ALTER TABLE {tbl} ADD COLUMN matrah REAL DEFAULT 0.0")
                    c.commit()
                except sqlite3.OperationalError:
                    pass

            s = self._settings_con
            s.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    date TEXT PRIMARY KEY, usd_rate REAL, eur_rate REAL
                );
                """
            )
            s.commit()

            h = self._history_con
            h.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT
                )
                """
            )
            h.commit()

    # ------------------------------------------------------------------
    # AYARLAR
    # ------------------------------------------------------------------

    def get_all_settings(self):
        with self._lock:
            rows = self._settings_con.execute(
                "SELECT key, value FROM settings"
            ).fetchall()
        return dict(rows)

    def get_setting(self, key):
        with self._lock:
            row = self._settings_con.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        return row[0] if row else None

    def save_setting(self, key, value):
        with self._lock:
            self._settings_con.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            self._settings_con.commit()

    # ------------------------------------------------------------------
    # DÖVİZ KURLARI
    # ------------------------------------------------------------------

    def save_exchange_rates(self, usd_rate, eur_rate):
        with self._lock:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self._settings_con.execute(
                "INSERT INTO exchange_rates(date,usd_rate,eur_rate) VALUES(?,?,?) "
                "ON CONFLICT(date) DO UPDATE SET usd_rate=excluded.usd_rate, eur_rate=excluded.eur_rate",
                (date, usd_rate, eur_rate),
            )
            self._settings_con.commit()

    def load_exchange_rates(self):
        with self._lock:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            row = self._settings_con.execute(
                "SELECT usd_rate, eur_rate FROM exchange_rates WHERE date=?", (date,)
            ).fetchone()
        return (row[0], row[1]) if row else (0.0, 0.0)

    # ------------------------------------------------------------------
    # GELİR FATURALARI
    # ------------------------------------------------------------------

    def _invoice_params(self, data):
        return (
            data.get("fatura_no"),
            _to_iso_date(data.get("tarih")),
            data.get("firma"),
            data.get("malzeme"),
            data.get("miktar"),
            data.get("matrah"),
            data.get("toplam_tutar_tl"),
            data.get("toplam_tutar_usd"),
            data.get("toplam_tutar_eur"),
            data.get("birim"),
            data.get("kdv_yuzdesi", 0.0),
            data.get("kdv_tutari", 0.0),
            data.get("kdv_dahil", 0),
            data.get("usd_rate"),
            data.get("eur_rate"),
        )

    def add_gelir_invoice(self, data):
        with self._lock:
            cur = self._invoices_con.execute(
                """INSERT INTO income_invoices
                   (fatura_no, tarih, firma, malzeme, miktar, matrah,
                    toplam_tutar_tl, toplam_tutar_usd, toplam_tutar_eur,
                    birim, kdv_yuzdesi, kdv_tutari, kdv_dahil,
                    usd_rate, eur_rate, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                self._invoice_params(data) + (_now_iso(),),
            )
            self._invoices_con.commit()
            return cur.lastrowid

    def update_gelir_invoice(self, invoice_id, data):
        with self._lock:
            cur = self._invoices_con.execute(
                """UPDATE income_invoices SET
                   fatura_no=?, tarih=?, firma=?, malzeme=?, miktar=?, matrah=?,
                   toplam_tutar_tl=?, toplam_tutar_usd=?, toplam_tutar_eur=?,
                   birim=?, kdv_yuzdesi=?, kdv_tutari=?, kdv_dahil=?,
                   usd_rate=?, eur_rate=?, updated_at=?
                   WHERE id=?""",
                self._invoice_params(data) + (_now_iso(), invoice_id),
            )
            self._invoices_con.commit()
            return cur.rowcount > 0

    def delete_gelir_invoice(self, invoice_id):
        with self._lock:
            cur = self._invoices_con.execute(
                "DELETE FROM income_invoices WHERE id=?", (invoice_id,)
            )
            self._invoices_con.commit()
            return cur.rowcount

    def delete_multiple_gelir_invoices(self, invoice_ids):
        if not invoice_ids:
            return 0
        with self._lock:
            placeholders = ",".join("?" * len(invoice_ids))
            cur = self._invoices_con.execute(
                f"DELETE FROM income_invoices WHERE id IN ({placeholders})",
                list(invoice_ids),
            )
            self._invoices_con.commit()
            return cur.rowcount

    def get_all_gelir_invoices(self, limit=None, offset=None, order_by=None):
        order = order_by or "tarih DESC"
        query = f"SELECT * FROM income_invoices ORDER BY {order}"
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            query += " OFFSET ?"
            params.append(offset or 0)
        with self._lock:
            rows = self._invoices_con.execute(query, params).fetchall()
        return [_row_to_invoice(r) for r in rows]

    def get_gelir_invoice_count(self):
        with self._lock:
            return self._invoices_con.execute(
                "SELECT COUNT(*) FROM income_invoices"
            ).fetchone()[0]

    def get_gelir_invoice_by_id(self, invoice_id):
        with self._lock:
            row = self._invoices_con.execute(
                "SELECT * FROM income_invoices WHERE id=?", (invoice_id,)
            ).fetchone()
        return _row_to_invoice(row)

    # ------------------------------------------------------------------
    # GİDER FATURALARI
    # ------------------------------------------------------------------

    def add_gider_invoice(self, data):
        with self._lock:
            cur = self._invoices_con.execute(
                """INSERT INTO expense_invoices
                   (fatura_no, tarih, firma, malzeme, miktar, matrah,
                    toplam_tutar_tl, toplam_tutar_usd, toplam_tutar_eur,
                    birim, kdv_yuzdesi, kdv_tutari, kdv_dahil,
                    usd_rate, eur_rate, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                self._invoice_params(data) + (_now_iso(),),
            )
            self._invoices_con.commit()
            return cur.lastrowid

    def update_gider_invoice(self, invoice_id, data):
        with self._lock:
            cur = self._invoices_con.execute(
                """UPDATE expense_invoices SET
                   fatura_no=?, tarih=?, firma=?, malzeme=?, miktar=?, matrah=?,
                   toplam_tutar_tl=?, toplam_tutar_usd=?, toplam_tutar_eur=?,
                   birim=?, kdv_yuzdesi=?, kdv_tutari=?, kdv_dahil=?,
                   usd_rate=?, eur_rate=?, updated_at=?
                   WHERE id=?""",
                self._invoice_params(data) + (_now_iso(), invoice_id),
            )
            self._invoices_con.commit()
            return cur.rowcount > 0

    def delete_gider_invoice(self, invoice_id):
        with self._lock:
            cur = self._invoices_con.execute(
                "DELETE FROM expense_invoices WHERE id=?", (invoice_id,)
            )
            self._invoices_con.commit()
            return cur.rowcount

    def delete_multiple_gider_invoices(self, invoice_ids):
        if not invoice_ids:
            return 0
        with self._lock:
            placeholders = ",".join("?" * len(invoice_ids))
            cur = self._invoices_con.execute(
                f"DELETE FROM expense_invoices WHERE id IN ({placeholders})",
                list(invoice_ids),
            )
            self._invoices_con.commit()
            return cur.rowcount

    def get_all_gider_invoices(self, limit=None, offset=None, order_by=None):
        order = order_by or "tarih DESC"
        query = f"SELECT * FROM expense_invoices ORDER BY {order}"
        params = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            query += " OFFSET ?"
            params.append(offset or 0)
        with self._lock:
            rows = self._invoices_con.execute(query, params).fetchall()
        return [_row_to_invoice(r) for r in rows]

    def get_gider_invoice_count(self):
        with self._lock:
            return self._invoices_con.execute(
                "SELECT COUNT(*) FROM expense_invoices"
            ).fetchone()[0]

    def get_gider_invoice_by_id(self, invoice_id):
        with self._lock:
            row = self._invoices_con.execute(
                "SELECT * FROM expense_invoices WHERE id=?", (invoice_id,)
            ).fetchone()
        return _row_to_invoice(row)

    # ------------------------------------------------------------------
    # GEÇMİŞ
    # ------------------------------------------------------------------

    def add_history_record(self, action, details):
        with self._lock:
            self._history_con.execute(
                "INSERT INTO history(action,details,timestamp) VALUES(?,?,?)",
                (action, details, _now_iso()),
            )
            self._history_con.commit()

    def get_recent_history(self, limit):
        with self._lock:
            rows = self._history_con.execute(
                "SELECT id,action,details,timestamp FROM history "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"id": r[0], "action": r[1], "details": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def get_history_by_date_range(self, start_date, end_date):
        with self._lock:
            rows = self._history_con.execute(
                "SELECT id,action,details,timestamp FROM history "
                "WHERE timestamp >= ? AND timestamp <= ? "
                "ORDER BY timestamp DESC",
                (start_date, end_date),
            ).fetchall()
        return [
            {"id": r[0], "action": r[1], "details": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def clear_old_history(self, days):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._lock:
            cur = self._history_con.execute(
                "DELETE FROM history WHERE timestamp < ?", (cutoff,)
            )
            self._history_con.commit()
            return cur.rowcount

    # ------------------------------------------------------------------
    # YILLIK GİDERLER
    # ------------------------------------------------------------------

    def _monthly_vals(self, monthly_data):
        return tuple(float(monthly_data.get(m, 0) or 0) for m in _MONTH_COLS)

    def add_or_update_yearly_expenses(self, year, monthly_data):
        vals = self._monthly_vals(monthly_data)
        with self._lock:
            row = self._invoices_con.execute(
                "SELECT id FROM general_expenses WHERE yil=?", (year,)
            ).fetchone()
            if row:
                self._invoices_con.execute(
                    f"UPDATE general_expenses SET "
                    f"{', '.join(f'{m}=?' for m in _MONTH_COLS)} WHERE yil=?",
                    vals + (year,),
                )
            else:
                cur = self._invoices_con.execute(
                    f"INSERT INTO general_expenses(yil,{','.join(_MONTH_COLS)}) "
                    f"VALUES(?,{','.join('?'*12)})",
                    (year,) + vals,
                )
                self._invoices_con.commit()
                return cur.lastrowid
            self._invoices_con.commit()
        return 1

    def get_yearly_expenses(self, year):
        with self._lock:
            row = self._invoices_con.execute(
                "SELECT id,yil," + ",".join(_MONTH_COLS) +
                " FROM general_expenses WHERE yil=?",
                (year,),
            ).fetchone()
        return _row_to_expense(row)

    def get_yearly_expenses_by_id(self, id):
        with self._lock:
            row = self._invoices_con.execute(
                "SELECT id,yil," + ",".join(_MONTH_COLS) +
                " FROM general_expenses WHERE id=?",
                (id,),
            ).fetchone()
        return _row_to_expense(row)

    def get_yearly_expenses_count(self):
        with self._lock:
            return self._invoices_con.execute(
                "SELECT COUNT(*) FROM general_expenses"
            ).fetchone()[0]

    def get_all_yearly_expenses(self):
        with self._lock:
            rows = self._invoices_con.execute(
                "SELECT id,yil," + ",".join(_MONTH_COLS) +
                " FROM general_expenses ORDER BY yil DESC"
            ).fetchall()
        return [_row_to_expense(r) for r in rows]

    # ------------------------------------------------------------------
    # KURUMLAR VERGİSİ
    # ------------------------------------------------------------------

    def add_or_update_corporate_tax(self, year, monthly_data):
        vals = self._monthly_vals(monthly_data)
        with self._lock:
            row = self._invoices_con.execute(
                "SELECT id FROM corporate_tax WHERE yil=?", (year,)
            ).fetchone()
            if row:
                self._invoices_con.execute(
                    f"UPDATE corporate_tax SET "
                    f"{', '.join(f'{m}=?' for m in _MONTH_COLS)} WHERE yil=?",
                    vals + (year,),
                )
            else:
                cur = self._invoices_con.execute(
                    f"INSERT INTO corporate_tax(yil,{','.join(_MONTH_COLS)}) "
                    f"VALUES(?,{','.join('?'*12)})",
                    (year,) + vals,
                )
                self._invoices_con.commit()
                return cur.lastrowid
            self._invoices_con.commit()
        return 1

    def get_corporate_tax(self, year):
        with self._lock:
            row = self._invoices_con.execute(
                "SELECT id,yil," + ",".join(_MONTH_COLS) +
                " FROM corporate_tax WHERE yil=?",
                (year,),
            ).fetchone()
        return _row_to_expense(row)
