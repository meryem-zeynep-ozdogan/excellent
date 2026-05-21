# Mock rust_db for testing UI when linker is missing
import copy
from datetime import datetime


class Database:
    def __init__(self):
        self._gelir = []      # Gelir (outgoing) faturaları
        self._gider = []      # Gider (incoming) faturaları
        self._next_id = 1
        self._history = []    # Son işlemler
        self._history_id = 1

    def init_connections(self): return None
    def create_tables(self): return None
    def get_all_settings(self): return {"lang": "tr", "theme_mode": "light"}
    def save_exchange_rates(self, usd, eur): return None
    def load_exchange_rates(self): return (0.03, 0.02)
    def save_setting(self, key, value): return None
    def get_yearly_expenses(self, year): return {}
    def add_or_update_yearly_expenses(self, year, data): return True
    def get_corporate_tax(self, year): return {}
    def add_or_update_corporate_tax(self, year, data): return True
    def get_all_yearly_expenses(self): return []
    def get_yearly_expenses_count(self): return 0
    def get_yearly_expenses_by_id(self, id): return None

    # ---- Yardımcı sıralama ----
    def _sorted(self, lst, order_by, offset, limit):
        result = list(lst)
        if order_by and "DESC" in str(order_by).upper():
            result.sort(key=lambda x: x.get("id", 0), reverse=True)
        elif order_by and "ASC" in str(order_by).upper():
            result.sort(key=lambda x: x.get("id", 0))
        if offset:
            result = result[offset:]
        if limit:
            result = result[:limit]
        return result

    # ---- Gelir faturaı ----
    def add_gelir_invoice(self, data):
        record = copy.deepcopy(data)
        record["id"] = self._next_id
        self._next_id += 1
        self._gelir.append(record)
        return record["id"]

    def update_gelir_invoice(self, id, data):
        for i, inv in enumerate(self._gelir):
            if inv.get("id") == id:
                updated = copy.deepcopy(data)
                updated["id"] = id
                self._gelir[i] = updated
                return True
        return False

    def delete_gelir_invoice(self, id):
        for i, inv in enumerate(self._gelir):
            if inv.get("id") == id:
                self._gelir.pop(i)
                return True
        return False

    def get_all_gelir_invoices(self, limit=None, offset=None, order_by=None):
        return self._sorted(self._gelir, order_by, offset, limit)

    def get_gelir_invoice_count(self): return len(self._gelir)

    def get_gelir_invoice_by_id(self, id):
        return next((inv for inv in self._gelir if inv.get("id") == id), None)

    def delete_multiple_gelir_invoices(self, ids):
        before = len(self._gelir)
        self._gelir = [inv for inv in self._gelir if inv.get("id") not in ids]
        return before - len(self._gelir)

    # ---- Gider faturaı ----
    def add_gider_invoice(self, data):
        record = copy.deepcopy(data)
        record["id"] = self._next_id
        self._next_id += 1
        self._gider.append(record)
        return record["id"]

    def update_gider_invoice(self, id, data):
        for i, inv in enumerate(self._gider):
            if inv.get("id") == id:
                updated = copy.deepcopy(data)
                updated["id"] = id
                self._gider[i] = updated
                return True
        return False

    def delete_gider_invoice(self, id):
        for i, inv in enumerate(self._gider):
            if inv.get("id") == id:
                self._gider.pop(i)
                return True
        return False

    def get_all_gider_invoices(self, limit=None, offset=None, order_by=None):
        return self._sorted(self._gider, order_by, offset, limit)

    def get_gider_invoice_count(self): return len(self._gider)

    def get_gider_invoice_by_id(self, id):
        return next((inv for inv in self._gider if inv.get("id") == id), None)

    def delete_multiple_gider_invoices(self, ids):
        before = len(self._gider)
        self._gider = [inv for inv in self._gider if inv.get("id") not in ids]
        return before - len(self._gider)

    # ---- İşlem geçmişi ----
    def add_history_record(self, action, details):
        record = {
            "id": self._history_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self._history_id += 1
        self._history.insert(0, record)
        return record["id"]

    def get_recent_history(self, limit):
        return self._history[:limit] if limit else list(self._history)

    def get_history_by_date_range(self, start, end):
        return [r for r in self._history if start <= r.get("timestamp", "") <= end]

    def clear_old_history(self, days): return 0

    def handle_invoice_operation(self, operation, invoice_type, limit=100, offset=0, order_by=None, invoice_data=None):
        if operation == "get":
            return []
        return True

