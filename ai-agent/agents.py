"""
agents.py — Five LangGraph agent node functions.

Agents:
  1. guardrails_node      — Security & Scope Manager
  2. sql_generator_node   — SQL Expert (role-aware)
  3. error_handler_node   — Error Recovery Specialist (max 3 retries)
  4. analysis_node        — Data Analyst
  5. visualization_node   — Visualization Specialist (Plotly JSON)

Supporting nodes (not agents per se, but part of the graph):
  • sql_executor_node     — executes SQL against MySQL via SQLAlchemy
  • viz_decision_node     — decides whether a chart is warranted
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Literal, Optional

import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from sqlalchemy import create_engine, text

from state import AgentState

load_dotenv()
logger = logging.getLogger("datapulse.agents")

# ──────────────────────────────────────────────────────────────────────────────
# Infrastructure: LLM + DB
# ──────────────────────────────────────────────────────────────────────────────

GROQ_KEY = os.environ.get("GROQ_API_KEY")
USE_LLM = GROQ_KEY is not None

if USE_LLM:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=GROQ_KEY)

DB_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:Ayhan2929.@localhost:3306/datapulse_ecommerce",
)

try:
    engine = create_engine(DB_URL, pool_pre_ping=True)
    with engine.connect() as _c:
        _c.execute(text("SELECT 1"))
    DB_OK = True
    logger.info("✅ Database connection OK")
except Exception as _e:
    engine = None
    DB_OK = False
    logger.error(f"❌ DB connection failed: {_e}")

# ──────────────────────────────────────────────────────────────────────────────
# Database schema — injected into every LLM prompt
# ──────────────────────────────────────────────────────────────────────────────

DB_SCHEMA = """
MySQL database — DataPulse e-commerce:

users             (id, full_name, email, role ENUM('ADMIN','CORPORATE','INDIVIDUAL'),
                   gender, age, city, country, enabled, created_at)
stores            (id, owner_id→users.id, name, description, is_open, created_at)
categories        (id, name, parent_id→categories.id)
products          (id, store_id→stores.id, category_id→categories.id, name,
                   description, sku, price DECIMAL, stock INT, image_url,
                   rating DECIMAL, review_count INT, created_at)
orders            (id, user_id→users.id, order_number VARCHAR,
                   status ENUM('PENDING','PROCESSING','SHIPPED','DELIVERED','CANCELLED'),
                   total_amount DECIMAL, payment_method VARCHAR, order_date DATETIME)
order_items       (id, order_id→orders.id, product_id→products.id,
                   quantity INT, unit_price DECIMAL)
shipments         (id, order_id→orders.id, tracking_number, warehouse_block,
                   mode_of_shipment, status, customer_care_calls INT,
                   shipped_date, delivery_date)
reviews           (id, user_id→users.id, product_id→products.id,
                   star_rating INT 1-5, review_text, helpful_votes INT,
                   total_votes INT, created_at)
cart_items        (id, user_id→users.id, product_id→products.id, quantity INT)
wishlist_items    (id, user_id→users.id, product_id→products.id)
customer_profiles (id, user_id→users.id, membership_type VARCHAR,
                   total_spend DECIMAL, items_purchased INT, avg_rating DECIMAL,
                   discount_applied BOOLEAN, satisfaction_level VARCHAR)
"""

# ──────────────────────────────────────────────────────────────────────────────
# Keyword helpers
# ──────────────────────────────────────────────────────────────────────────────

GREETING_KW = {
    "merhaba", "selam", "hey", "hi", "hello", "nasılsın", "naber",
    "iyi günler", "günaydın", "iyi akşamlar", "selamlar",
}

IN_SCOPE_KW = {
    "sipariş", "order", "ürün", "product", "satış", "sale", "gelir",
    "revenue", "müşteri", "customer", "kargo", "shipment", "teslimat",
    "delivery", "kategori", "category", "stok", "stock", "envanter",
    "inventory", "yorum", "review", "puan", "rating", "yıldız", "star",
    "mağaza", "store", "ödeme", "payment", "harcama", "spending", "üyelik",
    "membership", "trend", "analiz", "dağılım", "bekleyen", "pending",
    "iptal", "cancel", "teslim", "delivered", "shipped", "en çok", "en az",
    "top", "lowest", "highest", "weekly", "monthly", "haftalık", "aylık",
    "grafik", "chart", "göster", "show", "karşılaştır", "compare", "toplam",
    "total", "ortalama", "average", "kaç", "how many", "ne kadar", "how much",
    "şehir", "city", "platform", "rapor", "report", "özet", "summary",
    "istatistik", "statistic",
}


def _contains(txt: str, keywords: set) -> bool:
    t = txt.lower()
    return any(k in t for k in keywords)


# ──────────────────────────────────────────────────────────────────────────────
# Intent detection
# ──────────────────────────────────────────────────────────────────────────────

INTENT_RULES: list[tuple[str, list[str]]] = [
    ("weekly_revenue",        ["haftalık gelir", "haftalık satış", "weekly revenue", "weekly sales"]),
    ("monthly_revenue",       ["aylık gelir", "aylık satış", "monthly revenue", "monthly sales", "her ay"]),
    ("top_products_monthly",  ["geçen ay en çok", "bu ay en çok sipariş", "bu ay en çok satan",
                                "geçen ay en çok sipariş", "geçen ay en popüler", "son ay en çok",
                                "last month top", "this month top"]),
    ("order_status",          ["sipariş durumu", "order status", "durum dağılım", "kaç sipariş"]),
    ("order_pipeline",        ["bekleyen sipariş", "pending order", "işlemdeki", "iptal sipariş"]),
    ("top_products",          ["en çok satan", "top ürün", "best sell", "en popüler ürün", "top product"]),
    ("product_rating",        ["ürün puan", "en düşük puan", "lowest rating", "star rating", "review dağılım"]),
    ("category_revenue",      ["kategori", "category", "kategori bazlı", "by category"]),
    ("customer_city",         ["müşteri şehir", "şehir bazlı", "city distribution", "hangi şehir"]),
    ("shipment_mode",         ["kargo modu", "kargo istatistik", "shipment mode", "teslimat modu"]),
    ("membership",            ["üyelik", "membership", "gold üye", "silver üye", "bronze üye"]),
    ("payment_method",        ["ödeme yöntemi", "payment method", "hangi ödeme", "ödeme dağılım"]),
    ("stock",                 ["stok", "stock", "envanter", "inventory", "düşük stok", "low stock"]),
    ("spending",              ["harcama", "spending", "ne kadar harcadım", "kişisel harcama"]),
    ("total_revenue",         ["toplam gelir", "total revenue", "toplam satış", "total sales"]),
    # broad fallbacks
    ("order_status",          ["sipariş", "order"]),
    ("top_products",          ["ürün", "product"]),
    ("total_revenue",         ["satış", "gelir", "revenue", "sale"]),
]


def detect_intent(question: str) -> str:
    q = question.lower()
    for intent, patterns in INTENT_RULES:
        if any(p in q for p in patterns):
            return intent
    return "total_revenue"


# ──────────────────────────────────────────────────────────────────────────────
# Pre-written SQL library (used when LLM is unavailable)
# ──────────────────────────────────────────────────────────────────────────────

def get_sql_for_intent(
    intent: str,
    role: str,
    user_id: Optional[int],
    store_id: Optional[int],
) -> str:
    if role == "INDIVIDUAL" and user_id:
        order_filter2 = f"WHERE o.user_id = {user_id}"
    elif role == "CORPORATE" and store_id:
        order_filter2 = (
            f"JOIN order_items oi2 ON o.id = oi2.order_id "
            f"JOIN products p2 ON oi2.product_id = p2.id "
            f"WHERE p2.store_id = {store_id}"
        )
    else:
        order_filter2 = ""

    store_prod_filter = (
        f"WHERE p.store_id = {store_id}" if (role == "CORPORATE" and store_id)
        else f"WHERE o.user_id = {user_id}" if (role == "INDIVIDUAL" and user_id)
        else ""
    )

    # ── Role-specific revenue/order helpers ──────────────────────────────────
    # Dashboard uses SUM(oi.unit_price * oi.quantity) — item-based revenue.
    # AI must use the same formula so numbers match the analytics page.
    if role == "CORPORATE" and store_id:
        _rev_expr   = "ROUND(SUM(oi.unit_price * oi.quantity), 2)"
        _order_cnt  = "COUNT(DISTINCT o.id)"
        # Corporate base join: always go through order_items → products → store filter
        _corp_join  = (
            f"JOIN order_items oi ON o.id = oi.order_id "
            f"JOIN products p ON oi.product_id = p.id "
            f"WHERE p.store_id = {store_id}"
        )
        _corp_and   = f"AND p.store_id = {store_id}"
    elif role == "INDIVIDUAL" and user_id:
        _rev_expr   = "ROUND(SUM(o.total_amount), 2)"
        _order_cnt  = "COUNT(DISTINCT o.id)"
        _corp_join  = f"WHERE o.user_id = {user_id}"
        _corp_and   = f"AND o.user_id = {user_id}"
    else:
        # ADMIN — item-based to match admin dashboard
        _rev_expr   = "ROUND(SUM(oi.unit_price * oi.quantity), 2)"
        _order_cnt  = "COUNT(DISTINCT o.id)"
        _corp_join  = "JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id"
        _corp_and   = ""

    SQLS: dict[str, str] = {

        # Sipariş durum dağılımı — Dashboard countByStoreAndStatus ile aynı mantık
        "order_status": f"""
            SELECT o.status AS durum,
                   COUNT(DISTINCT o.id) AS sipariş_sayısı,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS toplam_gelir
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY o.status ORDER BY sipariş_sayısı DESC;
        """,

        "order_pipeline": f"""
            SELECT o.status AS durum,
                   COUNT(DISTINCT o.id) AS adet,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS bekleyen_tutar
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            WHERE o.status IN ('PENDING','PROCESSING')
            {"AND p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "AND o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY o.status;
        """,

        # En çok satan ürünler — tüm zamanlar
        "top_products": f"""
            SELECT p.name AS ürün,
                   SUM(oi.quantity) AS satış_adedi,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS toplam_gelir,
                   ROUND(p.price, 2) AS birim_fiyat
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o   ON oi.order_id   = o.id
            {store_prod_filter}
            GROUP BY p.id, p.name, p.price
            ORDER BY satış_adedi DESC LIMIT 10;
        """,

        # En çok satan ürünler — bu ay / geçen ay
        "top_products_monthly": f"""
            SELECT p.name AS ürün,
                   SUM(oi.quantity) AS satış_adedi,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS toplam_gelir,
                   ROUND(p.price, 2) AS birim_fiyat
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o   ON oi.order_id   = o.id
            WHERE o.order_date >= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m-01')
              AND o.order_date <  DATE_FORMAT(NOW(), '%Y-%m-01')
            {"AND p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "AND o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY p.id, p.name, p.price
            ORDER BY satış_adedi DESC LIMIT 10;
        """,

        # Kategori geliri — Dashboard getRevenueByCategoryForStore ile aynı
        "category_revenue": f"""
            SELECT COALESCE(c.name,'Kategorisiz') AS kategori,
                   COUNT(DISTINCT p.id) AS ürün_sayısı,
                   SUM(oi.quantity) AS satış_adedi,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS toplam_gelir
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            JOIN orders o ON oi.order_id = o.id
            {store_prod_filter}
            GROUP BY c.name ORDER BY toplam_gelir DESC;
        """,

        "customer_city": f"""
            SELECT COALESCE(u.city,'Bilinmiyor') AS şehir,
                   COUNT(DISTINCT o.user_id) AS müşteri_sayısı,
                   COUNT(DISTINCT o.id) AS sipariş_sayısı,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS toplam_gelir
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            JOIN users u ON o.user_id = u.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY u.city ORDER BY toplam_gelir DESC LIMIT 15;
        """,

        "shipment_mode": f"""
            SELECT sh.mode_of_shipment AS kargo_modu, sh.status AS durum,
                   COUNT(DISTINCT sh.id) AS adet
            FROM shipments sh
            JOIN orders o ON sh.order_id = o.id
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY sh.mode_of_shipment, sh.status ORDER BY adet DESC LIMIT 20;
        """,

        "product_rating": f"""
            SELECT p.name AS ürün,
                   ROUND(AVG(r.star_rating), 2) AS ortalama_puan,
                   COUNT(r.id) AS yorum_sayısı,
                   MIN(r.star_rating) AS min_puan,
                   MAX(r.star_rating) AS max_puan
            FROM reviews r
            JOIN products p ON r.product_id = p.id
            {("WHERE p.store_id = " + str(store_id)) if (role == "CORPORATE" and store_id)
             else ("WHERE r.user_id = " + str(user_id)) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY p.id, p.name HAVING yorum_sayısı >= 1
            ORDER BY ortalama_puan ASC LIMIT 10;
        """,

        # Gelir trendi — Dashboard getDailyRevenueByStore ile aynı (ürün bazlı gelir)
        "weekly_revenue": f"""
            SELECT DAYNAME(o.order_date) AS gün,
                   COUNT(DISTINCT o.id) AS sipariş_sayısı,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS gelir
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) + " AND" if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) + " AND" if (role == "INDIVIDUAL" and user_id)
             else "WHERE"} o.order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DAYNAME(o.order_date), DAYOFWEEK(o.order_date)
            ORDER BY DAYOFWEEK(o.order_date);
        """,

        "monthly_revenue": f"""
            SELECT DATE_FORMAT(o.order_date,'%Y-%m') AS ay,
                   COUNT(DISTINCT o.id) AS sipariş_sayısı,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS gelir
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY DATE_FORMAT(o.order_date,'%Y-%m')
            ORDER BY ay DESC LIMIT 12;
        """,

        "membership": f"""
            SELECT COALESCE(cp.membership_type,'Standart') AS üyelik_tipi,
                   COUNT(DISTINCT cp.id) AS üye_sayısı,
                   ROUND(AVG(cp.total_spend), 2) AS ort_harcama,
                   ROUND(SUM(cp.total_spend), 2) AS toplam_harcama
            FROM customer_profiles cp
            JOIN users u ON cp.user_id = u.id
            {"JOIN orders o ON u.id = o.user_id JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE cp.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY cp.membership_type ORDER BY ort_harcama DESC;
        """,

        "payment_method": f"""
            SELECT COALESCE(o.payment_method,'Bilinmiyor') AS ödeme_yöntemi,
                   COUNT(DISTINCT o.id) AS işlem_sayısı,
                   ROUND(SUM(oi.unit_price * oi.quantity), 2) AS toplam_tutar
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY o.payment_method ORDER BY işlem_sayısı DESC;
        """,

        "stock": f"""
            SELECT p.name AS ürün, p.sku AS sku, p.stock AS stok_adedi,
                   ROUND(p.price, 2) AS birim_fiyat,
                   COALESCE(c.name,'Kategorisiz') AS kategori
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else ("JOIN order_items oi ON p.id = oi.product_id "
                   "JOIN orders o ON oi.order_id = o.id "
                   "WHERE o.user_id = " + str(user_id)) if (role == "INDIVIDUAL" and user_id)
             else ""}
            GROUP BY p.id, p.name, p.sku, p.stock, p.price, c.name
            ORDER BY p.stock ASC LIMIT 15;
        """,

        # Bireysel harcama — Dashboard getTotalSpendByUser / getUserSpendTrend ile aynı
        "spending": f"""
            SELECT DATE_FORMAT(o.order_date,'%Y-%m') AS ay,
                   COUNT(DISTINCT o.id) AS sipariş_sayısı,
                   ROUND(SUM(o.total_amount), 2) AS harcama
            FROM orders o
            {order_filter2 if order_filter2 else ("WHERE o.user_id = " + str(user_id)) if user_id else ""}
            GROUP BY DATE_FORMAT(o.order_date,'%Y-%m') ORDER BY ay DESC LIMIT 12;
        """,

        # Özet — Dashboard totalRevenue/totalOrders/avgRating ile tutarlı
        "total_revenue": f"""
            SELECT 'Toplam Siparis' AS metrik,
                   COUNT(DISTINCT o.id) AS deger
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            UNION ALL
            SELECT 'Teslim Edilen',
                   COUNT(DISTINCT o.id)
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) + " AND" if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) + " AND" if (role == "INDIVIDUAL" and user_id)
             else "WHERE"} o.status = 'DELIVERED'
            UNION ALL
            SELECT 'Toplam Gelir TL',
                   ROUND(SUM(oi.unit_price * oi.quantity), 0)
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""}
            UNION ALL
            SELECT 'Benzersiz Musteri',
                   COUNT(DISTINCT o.user_id)
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            {"WHERE p.store_id = " + str(store_id) if (role == "CORPORATE" and store_id)
             else "WHERE o.user_id = " + str(user_id) if (role == "INDIVIDUAL" and user_id)
             else ""};
        """,
    }

    sql = SQLS.get(intent, SQLS["total_revenue"])
    return " ".join(sql.split())


# ──────────────────────────────────────────────────────────────────────────────
# Plotly chart builder
# ──────────────────────────────────────────────────────────────────────────────

PALETTE = [
    "#8c52ff", "#06b6d4", "#10b981", "#f59e0b", "#ef4444",
    "#a78bfa", "#34d399", "#fbbf24", "#60a5fa", "#fb923c",
]


def build_chart(intent: str, rows: list, question: str) -> Optional[str]:
    if not rows or len(rows) < 2:
        return None
    try:
        keys = list(rows[0].keys())
        if len(keys) < 2:
            return None

        x_key = keys[0]
        y_key = None
        for k in keys[1:]:
            sample = str(rows[0].get(k, ""))
            if any(c.isalpha() for c in sample[:6]):
                continue
            try:
                float(sample)
                y_key = k
                break
            except (ValueError, TypeError):
                continue
        if not y_key:
            return None

        labels = [str(r.get(x_key, ""))[:22] for r in rows[:20]]
        values = []
        for r in rows[:20]:
            try:
                values.append(float(str(r.get(y_key, 0) or 0)))
            except (ValueError, TypeError):
                values.append(0.0)

        if intent in ("weekly_revenue", "monthly_revenue", "spending"):
            trace = {
                "x": labels, "y": values, "type": "scatter",
                "mode": "lines+markers", "fill": "tozeroy",
                "line": {"color": "#8c52ff", "width": 3, "shape": "spline"},
                "marker": {"color": "#8c52ff", "size": 7},
                "fillcolor": "rgba(140,82,255,0.12)",
            }
        elif intent in ("order_status", "payment_method", "membership", "shipment_mode") and len(rows) <= 7:
            trace = {
                "labels": labels, "values": values, "type": "pie",
                "marker": {"colors": PALETTE[: len(labels)]},
                "hole": 0.38, "textinfo": "label+percent+value",
                "textfont": {"color": "#e2e8f0", "size": 11},
            }
        else:
            trace = {
                "x": labels, "y": values, "type": "bar",
                "marker": {"color": PALETTE[: len(labels)], "opacity": 0.9},
                "text": [f"{v:,.0f}" if v >= 1 else f"{v:.2f}" for v in values],
                "textposition": "outside",
                "textfont": {"color": "#94a3b8", "size": 10},
            }

        is_pie = trace.get("type") == "pie"
        title  = question[:60] + ("…" if len(question) > 60 else "")
        layout: dict = {
            "title": {"text": title, "font": {"color": "#e2e8f0", "size": 13}},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor":  "rgba(15,23,42,0.5)",
            "font": {"family": "Segoe UI, sans-serif", "color": "#94a3b8", "size": 11},
            "margin": {"t": 50, "b": 70, "l": 70, "r": 20},
            "showlegend": is_pie,
            "legend": {"font": {"color": "#94a3b8"}, "bgcolor": "rgba(0,0,0,0)"},
        }
        if not is_pie:
            layout["xaxis"] = {
                "gridcolor": "rgba(148,163,184,0.08)",
                "linecolor": "rgba(148,163,184,0.15)",
                "tickfont":  {"color": "#64748b"},
                "title": {"text": x_key.replace("_", " ").title(),
                          "font": {"color": "#64748b", "size": 11}},
            }
            layout["yaxis"] = {
                "gridcolor": "rgba(148,163,184,0.08)",
                "linecolor": "rgba(148,163,184,0.15)",
                "tickfont":  {"color": "#64748b"},
                "rangemode": "tozero",
                "title": {"text": y_key.replace("_", " ").title(),
                          "font": {"color": "#64748b", "size": 11}},
            }

        return json.dumps({"data": [trace], "layout": layout})
    except Exception as ex:
        logger.warning(f"Chart build error: {ex}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Rule-based fallback analysis generator
# ──────────────────────────────────────────────────────────────────────────────

def _f(v) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _i(v) -> int:
    try:
        return int(v or 0)
    except Exception:
        return 0


def generate_analysis(intent: str, rows: list, role: str, question: str) -> str:
    if not rows:
        return "Bu sorgu için veritabanında veri bulunamadı."

    scope = {
        "INDIVIDUAL": "kişisel verilerinizde",
        "CORPORATE":  "mağazanızda",
        "ADMIN":      "platformda",
    }.get(role, "veritabanında")

    try:
        if intent == "order_status":
            total     = sum(_i(r.get("sipariş_sayısı", 0)) for r in rows)
            delivered = next((_i(r.get("sipariş_sayısı", 0)) for r in rows
                              if str(r.get("durum", "")).upper() == "DELIVERED"), 0)
            pct = round(delivered / total * 100) if total else 0
            lines = [
                f"**Sipariş Durum Analizi** ({scope}):",
                f"• Toplam **{total}** sipariş incelendi",
                f"• **{delivered}** sipariş teslim edildi (**%{pct}** tamamlanma)",
            ]
            for r in rows:
                lines.append(f"• {r.get('durum','')}: {_i(r.get('sipariş_sayısı',0))} adet — "
                              f"{_f(r.get('toplam_gelir',0)):,.0f} TL")
            return "\n".join(lines)

        elif intent == "order_pipeline":
            total = sum(_i(r.get("adet", 0)) for r in rows)
            return (f"**Bekleyen İşlem Analizi** ({scope}):\n"
                    f"• Toplam **{total}** sipariş işlem bekliyor\n" +
                    "\n".join(f"• {r.get('durum','')}: {_i(r.get('adet',0))} adet"
                               for r in rows))

        elif intent in ("top_products", "top_products_monthly"):
            top = rows[0]
            n_key = next((k for k in top if "ürün" in k or "name" in k), list(top)[0])
            s_key = next((k for k in top if "satış" in k or "sold" in k or "adet" in k), None)
            r_key = next((k for k in top if "gelir" in k or "revenue" in k), None)
            label = "Aylık En Çok Satan Ürünler" if intent == "top_products_monthly" else "En Çok Satan Ürünler"
            lines = [f"**{label}** ({scope}):"]
            for i, row in enumerate(rows[:5], 1):
                line = f"**{i}.** {row.get(n_key,'')}"
                if s_key: line += f" — {_i(row.get(s_key,0))} adet"
                if r_key: line += f" / {_f(row.get(r_key,0)):,.0f} TL"
                lines.append(f"• {line}")
            return "\n".join(lines)

        elif intent == "category_revenue":
            top = rows[0]
            total_rev = sum(_f(r.get("toplam_gelir", 0)) for r in rows)
            return (f"**Kategori Gelir Analizi** ({scope}):\n"
                    f"• **{top.get('kategori','')}** kategorisi {_f(top.get('toplam_gelir',0)):,.0f} TL ile lider\n"
                    f"• Toplam gelir: {total_rev:,.0f} TL — {len(rows)} kategori analiz edildi")

        elif intent == "customer_city":
            top = rows[0]
            total_cust = sum(_i(r.get("müşteri_sayısı", 0)) for r in rows)
            return (f"**Müşteri Şehir Dağılımı** ({scope}):\n"
                    f"• **{top.get('şehir','')}** {_i(top.get('müşteri_sayısı',0))} müşteri ile lider\n"
                    f"• Toplam {total_cust} benzersiz müşteri, {len(rows)} şehirde")

        elif intent == "shipment_mode":
            total = sum(_i(r.get("adet", 0)) for r in rows)
            top = rows[0]
            return (f"**Kargo Modu Analizi** ({scope}):\n"
                    f"• Toplam {total} gönderi — en yaygın: **{top.get('kargo_modu','')}**\n"
                    f"• {len(rows)} farklı kargo/durum kombinasyonu")

        elif intent == "product_rating":
            worst = rows[0]
            p_key = next((k for k in worst if "ürün" in k or "name" in k), list(worst)[0])
            r_key = next((k for k in worst if "puan" in k or "rating" in k), None)
            stars = int(_f(worst.get(r_key, 0))) if r_key else 0
            total_reviews = sum(_i(r.get("yorum_sayısı", 0)) for r in rows)
            return (f"**Ürün Değerlendirme Analizi** ({scope}):\n"
                    f"• En düşük puanlı: **{worst.get(p_key,'')}** ({stars}/5 yıldız)\n"
                    f"• Toplam {total_reviews} yorum — {len(rows)} ürün değerlendirildi")

        elif intent in ("weekly_revenue", "monthly_revenue"):
            rev_key = next((k for k in rows[0] if "gelir" in k or "revenue" in k), None)
            if rev_key:
                total = sum(_f(r.get(rev_key, 0)) for r in rows)
                best  = max(rows, key=lambda x: _f(x.get(rev_key, 0)))
                period_key = list(rows[0])[0]
                label = "Haftalık" if intent == "weekly_revenue" else "Aylık"
                return (f"**{label} Gelir Trendi** ({scope}):\n"
                        f"• Toplam: {total:,.0f} TL\n"
                        f"• En yüksek dönem: **{best.get(period_key,'')}** — "
                        f"{_f(best.get(rev_key,0)):,.0f} TL\n"
                        f"• {len(rows)} dönem analiz edildi")

        elif intent == "membership":
            total_members = sum(_i(r.get("üye_sayısı", 0)) for r in rows)
            top = rows[0] if rows else {}
            return (f"**Üyelik Tier Analizi** ({scope}):\n"
                    f"• Toplam {total_members} üye — {len(rows)} tier\n"
                    f"• **{top.get('üyelik_tipi','')}** üyeler ort. "
                    f"{_f(top.get('ort_harcama',0)):,.0f} TL harcıyor")

        elif intent == "payment_method":
            total = sum(_i(r.get("işlem_sayısı", 0)) for r in rows)
            top = rows[0]
            return (f"**Ödeme Yöntemi Analizi** ({scope}):\n"
                    f"• **{top.get('ödeme_yöntemi','')}** {_i(top.get('işlem_sayısı',0))} işlemle en popüler\n"
                    f"• Toplam {total} işlem — {len(rows)} farklı ödeme yöntemi")

        elif intent == "stock":
            critical = [r for r in rows if _i(r.get("stok_adedi", 999)) < 10]
            return (f"**Stok Durumu** ({scope}):\n"
                    f"• En düşük stoklu: **{rows[0].get('ürün','')}** "
                    f"({_i(rows[0].get('stok_adedi',0))} adet)\n"
                    f"• **{len(critical)}** ürün kritik stok seviyesinde (< 10 adet)")

        elif intent == "spending":
            rev_key = next((k for k in rows[0] if "harcama" in k), None)
            if rev_key:
                total = sum(_f(r.get(rev_key, 0)) for r in rows)
                best  = max(rows, key=lambda x: _f(x.get(rev_key, 0)))
                period_key = list(rows[0])[0]
                return (f"**Harcama Analizi** ({scope}):\n"
                        f"• Toplam harcama: {total:,.0f} TL\n"
                        f"• En yüksek ay: **{best.get(period_key,'')}** — "
                        f"{_f(best.get(rev_key,0)):,.0f} TL")

        elif intent == "total_revenue":
            kv = {r.get("metrik", ""): r.get("deger", 0) for r in rows}
            return (f"**Platform Gelir Özeti** ({scope}):\n"
                    f"• Toplam Sipariş: **{_i(kv.get('Toplam Siparis',0)):,}**\n"
                    f"• Teslim Edilen: **{_i(kv.get('Teslim Edilen',0)):,}**\n"
                    f"• Toplam Gelir: **{_f(kv.get('Toplam Gelir TL',0)):,.0f} TL**\n"
                    f"• Benzersiz Müşteri: **{_i(kv.get('Benzersiz Musteri',0)):,}**")

    except Exception as ex:
        logger.warning(f"Analysis generation error: {ex}")

    return f"Analiz tamamlandı. {len(rows)} kayıt {scope} bulundu."


# ──────────────────────────────────────────────────────────────────────────────
# ① Guardrails Agent — Security & Scope Manager
# ──────────────────────────────────────────────────────────────────────────────

GUARDRAILS_SYSTEM = """
Sen bir e-ticaret analitik platformunun güvenlik ve kapsam denetçisisin.
Görevin: gelen soruyu değerlendirip SCOPE veya OUT_OF_SCOPE döndürmek.

Kapsam İÇİ (SCOPE): satış, sipariş, ürün, müşteri, kargo, teslimat, gelir,
  stok, yorum/puan, ödeme, mağaza, üyelik, kategori, trend, analiz, istatistik.
Kapsam DIŞI (OUT_OF_SCOPE): haber, siyaset, matematik, kodlama (e-ticaret dışı),
  kişisel sağlık, tarih, yemek tarifi, vb.
Selamlama tespit edilirse sadece GREETING yaz.

Yalnızca tek kelime yaz: SCOPE, OUT_OF_SCOPE veya GREETING
"""


# Keywords that indicate the user is asking about platform-wide / other users' data
_PLATFORM_SCOPE_KW = {
    "sitenizde", "sitenin", "platformda", "platformun", "tüm mağaza",
    "bütün mağaza", "tüm kullanıcı", "bütün kullanıcı", "genel satış",
    "site geneli", "platform geneli", "tüm platform", "bütün platform",
    "en çok satan ürün", "sitede en çok", "platformda en çok",
}

_CORP_PLATFORM_KW = {
    "tüm mağaza", "bütün mağaza", "diğer mağaza", "platform geneli",
    "tüm platform", "bütün platform", "site geneli", "tüm satış",
    "bütün satış",
}


def guardrails_node(state: AgentState) -> AgentState:
    q    = state["question"].lower().strip()
    role = state.get("role", "INDIVIDUAL")

    if any(re.search(r"(^|\s)" + re.escape(k) + r"(\s|$|[!?,.])", q)
           for k in GREETING_KW):
        state["is_greeting"] = True
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Merhaba! Ben DataPulse AI Asistanım 👋\n\n"
            "E-ticaret verileriniz hakkında soru sorabilirsiniz:\n"
            "• \"Sipariş durumu dağılımı nedir?\"\n"
            "• \"En çok satan 5 ürünü göster\"\n"
            "• \"Kategori bazlı gelir analizi\"\n"
            "• \"Aylık satış trendi\"\n"
            "• \"Kargo modu istatistikleri\""
        )
        return state

    state["is_greeting"] = False

    # Early rejection: INDIVIDUAL asking for platform/site-wide data
    if role == "INDIVIDUAL" and any(k in q for k in _PLATFORM_SCOPE_KW):
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Güvenlik prensiplerimiz gereği tüm sitenin satış verilerine erişiminiz bulunmuyor.\n\n"
            "Yalnızca kendi alışveriş geçmişinize erişebilirsiniz. "
            "Dilerseniz kişisel verileriniz hakkında soru sorabilirsiniz:\n"
            "• \"Benim en çok satın aldığım ürünler\"\n"
            "• \"Kendi sipariş durumlarım\"\n"
            "• \"Aylık harcama trendiim\""
        )
        return state

    # Early rejection: CORPORATE asking for other stores' data
    if role == "CORPORATE" and any(k in q for k in _CORP_PLATFORM_KW):
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Güvenlik prensiplerimiz gereği diğer mağazaların verilerine erişiminiz bulunmuyor.\n\n"
            "Yalnızca kendi mağazanızın verilerine erişebilirsiniz:\n"
            "• \"Mağazamın en çok satan ürünleri\"\n"
            "• \"Mağazamın sipariş durum dağılımı\"\n"
            "• \"Mağazamın aylık gelir trendi\""
        )
        return state

    if USE_LLM:
        try:
            ans = llm.invoke([HumanMessage(content=(
                f"{GUARDRAILS_SYSTEM}\n\nSoru: {state['question']}"
            ))]).content.strip().upper()
            if "GREETING" in ans:
                state["is_greeting"] = True
                state["is_in_scope"] = False
                state["final_answer"] = (
                    "Merhaba! E-ticaret verileri hakkında size nasıl yardımcı olabilirim?"
                )
            else:
                state["is_in_scope"] = "OUT" not in ans
        except Exception:
            state["is_in_scope"] = _contains(state["question"], IN_SCOPE_KW)
    else:
        state["is_in_scope"] = _contains(state["question"], IN_SCOPE_KW)

    if not state.get("is_greeting") and not state["is_in_scope"]:
        state["final_answer"] = (
            "Bu soru e-ticaret analiz kapsamı dışında.\n"
            "Satış, sipariş, ürün, müşteri veya kargo hakkında sorular sorabilirsiniz."
        )
    return state


# ──────────────────────────────────────────────────────────────────────────────
# ② SQL Agent — SQL Expert with Row-Level Security
# ──────────────────────────────────────────────────────────────────────────────

def _build_role_security_block(role: str, user_id, store_id) -> str:
    """
    Builds the role-specific Row-Level Security block injected into every
    SQL Agent and Error Agent prompt. Returns a hard-coded, non-negotiable
    constraint string so the LLM cannot ignore or soften it.
    """
    if role == "CORPORATE" and store_id:
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║  ROL: CORPORATE  —  MAĞAZA ID: {store_id}
║  VERİ İZOLASYONU KURALLARI (MUTLAK ZORUNLU):
║
║  1. Sen YALNIZCA store_id = {store_id} olan mağazanın asistanısın.
║  2. Yazdığın İSTİSNASIZ HER SQL sorgusunda aşağıdaki filtreyi
║     MUTLAKA eklemek ZORUNDASIN:
║       - products tablosuna erişirken:  WHERE p.store_id = {store_id}
║       - order_items tablosuna erişirken: products JOIN ile
║         WHERE p.store_id = {store_id} filtresi ekle
║       - orders tablosuna erişirken: order_items + products JOIN ile
║         WHERE p.store_id = {store_id} filtresi ekle
║       - reviews tablosuna erişirken: products JOIN ile
║         WHERE p.store_id = {store_id} filtresi ekle
║  3. JOIN zinciri ne kadar uzun olursa olsun filtreyi ATLAMAZSIN.
║  4. Diğer mağazaların (store_id != {store_id}) verilerine
║     KESİNLİKLE dokunma.
║  5. Bu kurallara uymayan bir SQL üretirsen GÜVENLİK İHLALİ
║     oluşur — asla kabul edilemez.
╚══════════════════════════════════════════════════════════════════╝
"""
    if role == "INDIVIDUAL" and user_id:
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║  ROL: INDIVIDUAL  —  KULLANICI ID: {user_id}
║  VERİ İZOLASYONU KURALLARI (MUTLAK ZORUNLU):
║
║  1. Sen YALNIZCA user_id = {user_id} olan kullanıcının asistanısın.
║  2. Yazdığın İSTİSNASIZ HER SQL sorgusunda:
║       - orders tablosuna erişirken:    WHERE o.user_id = {user_id}
║       - reviews tablosuna erişirken:   WHERE r.user_id = {user_id}
║       - cart_items tablosuna erişirken: WHERE ci.user_id = {user_id}
║  3. Diğer kullanıcıların verilerine KESİNLİKLE dokunma.
╚══════════════════════════════════════════════════════════════════╝
"""
    # ADMIN
    return "\n[ ROL: ADMIN — Kısıtsız erişim, filtre gerekmez. ]\n"


def _build_sql_prompt(question: str, role: str, user_id, store_id,
                      prev_err: str = "") -> str:
    fix_ctx = f"\nÖNCEKİ DENEME BAŞARISIZ: {prev_err}\nHatayı düzelt.\n" if prev_err else ""
    return f"""Sen kıdemli bir MySQL geliştiricisisin.

GENEL KURALLAR:
- Sadece SELECT sorgusu yaz; DROP/DELETE/INSERT/UPDATE/ALTER YASAK.
- LIMIT 100 ekle (aksi belirtilmedikçe).
- Markdown kullanma — sadece ham SQL döndür.
- Sözdizimi hatası içermeyen geçerli MySQL yaz.

VERİTABANI ŞEMASI:
{DB_SCHEMA}
{_build_role_security_block(role, user_id, store_id)}
{fix_ctx}
SORU: {question}
SQL:"""


# Intents that use pre-written SQL even when LLM is available.
# These require precise date math or role-based joins that LLMs frequently get wrong.
_FORCE_PREWRITTEN = {"top_products_monthly", "monthly_revenue", "weekly_revenue",
                     "stock", "spending"}


def sql_generator_node(state: AgentState) -> AgentState:
    intent = detect_intent(state["question"])
    state["intent"] = intent

    role     = state.get("role", "INDIVIDUAL")
    user_id  = state.get("user_id")
    store_id = state.get("store_id")

    # Always use pre-written SQL for date-sensitive or isolation-critical intents
    if not USE_LLM or intent in _FORCE_PREWRITTEN:
        state["sql_query"] = get_sql_for_intent(intent, role, user_id, store_id)
        state["error"]         = None
        state["error_message"] = None
        return state

    prev_err = state.get("error_message", "")
    prompt = _build_sql_prompt(state["question"], role, user_id, store_id, prev_err)
    try:
        raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        sql = raw.replace("```sql", "").replace("```", "").strip()
        if not sql.endswith(";"):
            sql += ";"
        state["sql_query"]     = sql
        state["error"]         = None
        state["error_message"] = None
    except Exception as ex:
        state["error"]         = "generation_failed"
        state["error_message"] = str(ex)

    return state


# ──────────────────────────────────────────────────────────────────────────────
# SQL Executor node (not an LLM agent — direct DB execution)
# ──────────────────────────────────────────────────────────────────────────────

_BLOCKED_KEYWORDS = (
    "DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE",
    "ALTER", "CREATE", "EXEC", "GRANT", "REVOKE",
)


def sql_executor_node(state: AgentState) -> AgentState:
    sql = (state.get("sql_query") or "").strip()
    if not sql:
        state["error"] = "no_sql"
        return state

    sql_up = sql.upper()
    if not sql_up.lstrip().startswith("SELECT"):
        state["error"]         = "security_violation"
        state["final_answer"]  = "Güvenlik: Yalnızca SELECT sorguları çalıştırılabilir."
        return state
    for bad in _BLOCKED_KEYWORDS:
        if bad in sql_up:
            state["error"]        = "security_violation"
            state["final_answer"] = f"Güvenlik ihlali: '{bad}' komutu yasak."
            return state

    # Second-layer data isolation — hard block if LLM ignored role filter
    role     = state.get("role", "")
    store_id = state.get("store_id")
    user_id  = state.get("user_id")

    if role == "CORPORATE" and store_id:
        if f"STORE_ID" not in sql_up:
            logger.warning(f"CORPORATE isolation violation — store_id missing. SQL: {sql[:200]}")
            state["error"]        = "security_violation"
            state["final_answer"] = (
                "Güvenlik prensiplerimiz gereği tüm platformun verilerine erişiminiz bulunmuyor.\n\n"
                "Yalnızca kendi mağazanızın verilerine erişebilirsiniz. "
                "Sorunuzu mağazanıza özel olarak yeniden sorabilirsiniz:\n"
                "• \"Mağazamın en çok satan ürünleri\"\n"
                "• \"Mağazamdaki sipariş durum dağılımı\"\n"
                "• \"Mağazamın aylık gelir trendi\""
            )
            return state

    if role == "INDIVIDUAL" and user_id:
        if f"USER_ID" not in sql_up:
            logger.warning(f"INDIVIDUAL isolation violation — user_id missing. SQL: {sql[:200]}")
            state["error"]        = "security_violation"
            state["final_answer"] = (
                "Güvenlik prensiplerimiz gereği tüm sitenin verilerine erişiminiz bulunmuyor.\n\n"
                "Yalnızca kendi alışveriş geçmişinize erişebilirsiniz. "
                "Sorunuzu kişisel verilerinize özel olarak yeniden sorabilirsiniz:\n"
                "• \"Benim en çok satın aldığım ürünler\"\n"
                "• \"Kendi sipariş durum dağılımım\"\n"
                "• \"Aylık harcama trendiim\""
            )
            return state

    if not DB_OK or engine is None:
        state["error"]        = "db_unavailable"
        state["error_message"] = "Veritabanına bağlanılamıyor."
        state["final_answer"] = (
            "⚠️ Veritabanına bağlanılamıyor. "
            "Lütfen MySQL servisinin çalıştığını kontrol edin."
        )
        return state

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows   = result.fetchmany(100)
            cols   = list(result.keys())
            df     = pd.DataFrame(rows, columns=cols)
            state["query_result"]  = (
                df.to_json(orient="records", force_ascii=False) if not df.empty else "[]"
            )
            state["error"]         = None
            state["error_message"] = None
            logger.info(f"Query OK — {len(df)} rows, intent={state.get('intent')}")
    except Exception as ex:
        state["error"]         = "sql_error"
        state["error_message"] = str(ex)
        state["query_result"]  = None
        logger.warning(f"SQL error: {ex}\nSQL: {sql[:200]}")

    return state


# ──────────────────────────────────────────────────────────────────────────────
# ③ Error Agent — Error Recovery Specialist
# ──────────────────────────────────────────────────────────────────────────────

def _build_error_prompt(state: AgentState) -> str:
    role     = state.get("role", "INDIVIDUAL")
    user_id  = state.get("user_id")
    store_id = state.get("store_id")
    return f"""Sen bir MySQL hata uzmanısın. Hatalı SQL sorgusunu düzelt.
Sadece ham SQL döndür, açıklama yapma. Sözdizimi hatası içermeyen geçerli MySQL yaz.

VERİTABANI ŞEMASI:
{DB_SCHEMA}
{_build_role_security_block(role, user_id, store_id)}
SORU: {state["question"]}
HATALI SQL:
{state.get("sql_query", "")}
HATA: {state.get("error_message", "")}

DÜZELTİLMİŞ SQL:"""


def error_handler_node(state: AgentState) -> AgentState:
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    if state["iteration_count"] >= 3:
        state["final_answer"] = (
            "Sorgu 3 denemeden sonra çalışmadı. Soruyu farklı şekilde deneyin."
        )
        state["error"] = "max_retries"
        return state

    if state.get("error") == "db_unavailable":
        return state

    if USE_LLM:
        try:
            prompt = _build_error_prompt(state)
            fixed = llm.invoke([HumanMessage(content=prompt)]).content.strip()
            fixed = fixed.replace("```sql", "").replace("```", "").strip()
            if not fixed.endswith(";"):
                fixed += ";"
            state["sql_query"]     = fixed
            state["error"]         = None
            state["error_message"] = None
        except Exception as ex:
            state["error"]         = "fix_failed"
            state["error_message"] = str(ex)
    else:
        state["sql_query"] = get_sql_for_intent(
            "total_revenue",
            state.get("role", "INDIVIDUAL"),
            state.get("user_id"),
            state.get("store_id"),
        )
        state["error"]         = None
        state["error_message"] = None

    return state


# ──────────────────────────────────────────────────────────────────────────────
# ④ Analysis Agent — Data Analyst
# ──────────────────────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM = """
Sen yardımsever bir iş zekası analistsin. Veritabanından dönen JSON sonucunu
iş kullanıcısına anlaşılır, içgörü odaklı bir dille açıkla.
2-4 cümle, temel bulgular ve dikkat çekici noktalar.
Türkçe yanıt ver. Markdown bold kullanabilirsin.
"""


def analysis_node(state: AgentState) -> AgentState:
    result = state.get("query_result", "[]")
    if not result or result == "[]":
        state["final_answer"] = "Bu sorgu için veritabanında veri bulunamadı."
        return state

    try:
        rows   = json.loads(result)
        intent = state.get("intent") or detect_intent(state["question"])

        if USE_LLM:
            try:
                prompt = (
                    f"{ANALYSIS_SYSTEM}\n\n"
                    f"KULLANICI SORUSU: {state['question']}\n"
                    f"ROL: {state.get('role','INDIVIDUAL')}\n"
                    f"VERİ ({len(rows)} satır):\n{result[:3000]}\n\n"
                    "ANALİZ:"
                )
                ans = llm.invoke([HumanMessage(content=prompt)]).content.strip()
                state["final_answer"] = ans
                return state
            except Exception:
                pass  # fall through to rule-based

        state["final_answer"] = generate_analysis(
            intent, rows, state.get("role", "INDIVIDUAL"), state["question"]
        )
    except Exception as ex:
        logger.warning(f"Analysis error: {ex}")
        state["final_answer"] = "Veriler başarıyla getirildi."

    return state


# ──────────────────────────────────────────────────────────────────────────────
# Viz decision node
# ──────────────────────────────────────────────────────────────────────────────

def viz_decision_node(state: AgentState) -> AgentState:
    try:
        rows = json.loads(state.get("query_result") or "[]")
        state["needs_viz"] = len(rows) >= 2
    except Exception:
        state["needs_viz"] = False
    return state


# ──────────────────────────────────────────────────────────────────────────────
# ⑤ Visualization Agent — Plotly Specialist
# ──────────────────────────────────────────────────────────────────────────────

VIZ_SYSTEM = """
Sen bir veri görselleştirme uzmanısın. Aşağıdaki verilere bakarak en uygun
Plotly grafiğini JSON formatında üret.

Kurallar:
- Sadece geçerli Plotly JSON döndür ({"data": [...], "layout": {...}})
- Açıklama veya markdown ekleme.
- Arka plan: paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.5)"
- Font rengi: "#e2e8f0", grid rengi: "rgba(148,163,184,0.08)"
- Renk paleti: ["#8c52ff","#06b6d4","#10b981","#f59e0b","#ef4444"]
- Zaman serisi için scatter (lines+markers+fill), pasta için pie (hole=0.38),
  karşılaştırma için bar kullan.
"""


def visualization_node(state: AgentState) -> AgentState:
    try:
        rows   = json.loads(state.get("query_result") or "[]")
        intent = state.get("intent") or detect_intent(state["question"])

        if USE_LLM:
            try:
                prompt = (
                    f"{VIZ_SYSTEM}\n\n"
                    f"SORU: {state['question']}\n"
                    f"İNTENT: {intent}\n"
                    f"VERİ ({len(rows[:20])} satır):\n"
                    f"{json.dumps(rows[:20], ensure_ascii=False)}\n\n"
                    "PLOTLY JSON:"
                )
                raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
                raw = raw.replace("```json", "").replace("```", "").strip()
                json.loads(raw)  # validate
                state["visualization_code"] = raw
                return state
            except Exception:
                pass  # fall through to rule-based

        state["visualization_code"] = build_chart(intent, rows, state["question"])
    except Exception as ex:
        logger.warning(f"Viz error: {ex}")
        state["visualization_code"] = None

    return state
