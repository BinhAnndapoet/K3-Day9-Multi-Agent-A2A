"""Data access layer: load 9 CSV Olist, build index, expose lookup theo key.

Chỉ load các CSV cần cho ra quyết định (bỏ geolocation 62MB và reviews không dùng làm evidence).
Một agent chỉ thấy domain của nó qua các hàm lookup hẹp → tôn trọng least-privilege.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from config import DATA_DIR
from models import ItemRow, OrderRow, PaymentRow


def _open_csv(path: Path) -> csv.DictReader:
    # UTF-8 vì dữ liệu có tiếng Bồ Đào Nha (city/category). Cột trong Olist không quote nhất quán →
    # dùng QUOTE_MINIMAL mặc định là đủ.
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]
    return rows


def _f(value, default=0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _i(value, default=0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=1)
def load_orders() -> dict[str, OrderRow]:
    rows = _open_csv(DATA_DIR / "olist_orders_dataset.csv")
    out: dict[str, OrderRow] = {}
    for r in rows:
        oid = r["order_id"]
        out[oid] = OrderRow(
            order_id=oid,
            customer_id=r.get("customer_id", ""),
            order_status=(r.get("order_status") or "").strip(),
            order_purchase_timestamp=(r.get("order_purchase_timestamp") or "").strip(),
            order_approved_at=(r.get("order_approved_at") or "").strip(),
            order_delivered_carrier_date=(r.get("order_delivered_carrier_date") or "").strip(),
            order_delivered_customer_date=(r.get("order_delivered_customer_date") or "").strip(),
            order_estimated_delivery_date=(r.get("order_estimated_delivery_date") or "").strip(),
        )
    return out


@lru_cache(maxsize=1)
def load_items_by_order() -> dict[str, list[ItemRow]]:
    rows = _open_csv(DATA_DIR / "olist_order_items_dataset.csv")
    out: dict[str, list[ItemRow]] = {}
    for r in rows:
        oid = r["order_id"]
        item = ItemRow(
            order_id=oid,
            order_item_id=_i(r.get("order_item_id")),
            product_id=r.get("product_id", ""),
            seller_id=r.get("seller_id", ""),
            shipping_limit_date=(r.get("shipping_limit_date") or "").strip(),
            price=_f(r.get("price")),
            freight_value=_f(r.get("freight_value")),
        )
        out.setdefault(oid, []).append(item)
    # đảm bảo item sắp xếp theo order_item_id để evidence/id ổn định
    for oid in out:
        out[oid].sort(key=lambda it: it.order_item_id)
    return out


@lru_cache(maxsize=1)
def load_payments_by_order() -> dict[str, list[PaymentRow]]:
    rows = _open_csv(DATA_DIR / "olist_order_payments_dataset.csv")
    out: dict[str, list[PaymentRow]] = {}
    for r in rows:
        oid = r["order_id"]
        pay = PaymentRow(
            order_id=oid,
            payment_sequential=_i(r.get("payment_sequential")),
            payment_type=(r.get("payment_type") or "").strip(),
            payment_installments=_i(r.get("payment_installments")),
            payment_value=_f(r.get("payment_value")),
        )
        out.setdefault(oid, []).append(pay)
    for oid in out:
        out[oid].sort(key=lambda p: p.payment_sequential)
    return out


@lru_cache(maxsize=1)
def load_sellers() -> dict[str, dict]:
    rows = _open_csv(DATA_DIR / "olist_sellers_dataset.csv")
    return {r["seller_id"]: r for r in rows}


@lru_cache(maxsize=1)
def load_customers() -> dict[str, dict]:
    rows = _open_csv(DATA_DIR / "olist_customers_dataset.csv")
    return {r["customer_id"]: r for r in rows}


@lru_cache(maxsize=1)
def load_products() -> dict[str, dict]:
    rows = _open_csv(DATA_DIR / "olist_products_dataset.csv")
    return {r["product_id"]: r for r in rows}


# ---- API hẹp cho agent ----
def get_order(order_id: str) -> OrderRow | None:
    return load_orders().get(order_id)


def get_items(order_id: str) -> list[ItemRow]:
    return load_items_by_order().get(order_id, [])


def get_payments(order_id: str) -> list[PaymentRow]:
    return load_payments_by_order().get(order_id, [])


def get_seller(seller_id: str) -> dict | None:
    return load_sellers().get(seller_id)
