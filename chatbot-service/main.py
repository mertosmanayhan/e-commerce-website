"""
DataPulse Text2SQL Multi-Agent Chatbot  v5.0
─────────────────────────────────────────────
Strategy:
  • LLM (OpenAI) available  → LLM generates SQL
  • LLM not available       → Intent-router picks a pre-written real SQL query
  In both cases the SQL is executed against the REAL MySQL database.
  No fake mock data — every response comes from actual rows.

Role-based data isolation (§5.8):
  INDIVIDUAL  → only their own orders/reviews/spend  (WHERE user_id = ?)
  CORPORATE   → only their store's data              (WHERE store_id = ?)
  ADMIN       → full platform access

Endpoints:
  POST /api/chat/ask     — sync JSON
  POST /api/chat/stream  — SSE (thinking animation, then result)
"""

import os, json, logging, asyncio
from typing import TypedDict, Optional, Literal, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("datapulse")

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
USE_LLM    = OPENAI_KEY is not None
DB_URL     = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:Ayhan2929.@localhost:3306/datapulse_ecommerce"
)

if USE_LLM:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_KEY)

try:
    engine = create_engine(DB_URL, pool_pre_ping=True)
    with engine.connect() as _c:
        _c.execute(text("SELECT 1"))
    DB_OK = True
    logger.info("✅ Database connection OK")
except Exception as _e:
    engine = None
    DB_OK  = False
    logger.error(f"❌ DB connection failed: {_e}")

# ──────────────────────────────────────────────────────────────────────────────
# DB Schema string (used in LLM prompts)
# ──────────────────────────────────────────────────────────────────────────────

DB_SCHEMA = """
MySQL database – DataPulse e-commerce (real data):

users             (id, full_name, email, role ENUM('ADMIN','CORPORATE','INDIVIDUAL'), gender, age, city, country, enabled, created_at)
stores            (id, owner_id→users.id, name, description, is_open, created_at)
categories        (id, name, parent_id→categories.id)
products          (id, store_id→stores.id, category_id→categories.id, name, description, sku, price DECIMAL, stock INT, image_url, rating DECIMAL, review_count INT, created_at)
orders            (id, user_id→users.id, order_number VARCHAR, status ENUM('PENDING','PROCESSING','SHIPPED','DELIVERED','CANCELLED'), total_amount DECIMAL, payment_method VARCHAR, order_date DATETIME)
order_items       (id, order_id→orders.id, product_id→products.id, quantity INT, unit_price DECIMAL)
shipments         (id, order_id→orders.id, tracking_number, warehouse_block, mode_of_shipment, status, customer_care_calls INT, shipped_date, delivery_date)
reviews           (id, user_id→users.id, product_id→products.id, star_rating INT 1-5, review_text, helpful_votes INT, total_votes INT, created_at)
cart_items        (id, user_id→users.id, product_id→products.id, quantity INT)
wishlist_items    (id, user_id→users.id, product_id→products.id)
customer_profiles (id, user_id→users.id, membership_type VARCHAR, total_spend DECIMAL, items_purchased INT, avg_rating DECIMAL, discount_applied BOOLEAN, satisfaction_level VARCHAR)
"""

# ──────────────────────────────────────────────────────────────────────────────
# Agent State
# ──────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:           str
    role:               str
    user_id:            Optional[int]
    store_id:           Optional[int]
    is_in_scope:        bool
    is_greeting:        bool
    sql_query:          Optional[str]
    query_result:       Optional[str]   # JSON string of rows
    error:              Optional[str]
    error_message:      Optional[str]
    final_answer:       Optional[str]
    needs_viz:          bool
    visualization_code: Optional[str]
    iteration_count:    int
    intent:             Optional[str]   # detected intent label

# ──────────────────────────────────────────────────────────────────────────────
# Keyword helpers
# ──────────────────────────────────────────────────────────────────────────────

GREETING_KW = {
    "merhaba","selam","hey","hi","hello","nasılsın","naber","iyi günler",
    "günaydın","iyi akşamlar","selamlar"
}
IN_SCOPE_KW = {
    "sipariş","order","ürün","product","satış","sale","gelir","revenue",
    "müşteri","customer","kargo","shipment","teslimat","delivery","kategori",
    "category","stok","stock","envanter","inventory","yorum","review","puan",
    "rating","yıldız","star","mağaza","store","ödeme","payment","harcama",
    "spending","üyelik","membership","trend","analiz","analyz","dağılım",
    "bekleyen","pending","iptal","cancel","teslim","delivered","shipped",
    "en çok","en az","top","lowest","highest","weekly","monthly","haftalık",
    "aylık","grafik","chart","göster","show","karşılaştır","compare","toplam",
    "total","ortalama","average","kaç","how many","ne kadar","how much",
    "şehir","city","şehir dağılım","müşteri şehir","customer city",
    "platform","rapor","report","özet","summary","istatistik","statistic"
}

def _contains(text: str, keywords) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)

# ──────────────────────────────────────────────────────────────────────────────
# Intent detection — priority-ordered, more specific first
# ──────────────────────────────────────────────────────────────────────────────

INTENT_RULES: list[tuple[str, list[str]]] = [
    # ── most specific patterns first ──
    ("weekly_revenue",   ["haftalık gelir","haftalık satış","weekly revenue","weekly sales","bu hafta gelir","this week revenue"]),
    ("monthly_revenue",  ["aylık gelir","aylık satış","monthly revenue","monthly sales","aylık trend","ay bazlı gelir","her ay"]),
    ("order_status",     ["sipariş durumu","order status","durum dağılım","sipariş dağılım","kaç sipariş","siparişlerin durumu"]),
    ("order_pipeline",   ["bekleyen sipariş","pending order","işlemdeki","processing","iptal sipariş","cancel"]),
    ("top_products",     ["en çok satan","top ürün","best sell","en popüler ürün","çok satan","top product","en fazla satan"]),
    ("product_rating",   ["ürün puan","en düşük puan","lowest rating","en yüksek puan","yıldız dağılım","star rating","ürün yorum","ürün değerlendirme","review dağılım","rating distribution"]),
    ("category_revenue", ["kategori","category","kategori bazlı","by category","hangi kategori"]),
    ("customer_city",    ["müşteri şehir","şehir bazlı","city distribution","hangi şehir","city","şehir dağılım"]),
    ("shipment_mode",    ["kargo modu","kargo istatistik","shipment mode","gönderim modu","hangi kargo","teslimat modu","kargo dağılım"]),
    ("membership",       ["üyelik","membership","gold üye","silver üye","bronze üye","tier","membership type"]),
    ("payment_method",   ["ödeme yöntemi","payment method","hangi ödeme","ödeme dağılım","nasıl ödeme"]),
    ("stock",            ["stok","stock","envanter","inventory","düşük stok","low stock","stok durumu","ürün stok"]),
    ("spending",         ["harcama","spending","ne kadar harcadım","kişisel harcama","toplam harcamam"]),
    ("total_revenue",    ["toplam gelir","total revenue","toplam satış","total sales","genel gelir","platform gelir"]),
    # ── broad fallbacks ──
    ("order_status",     ["sipariş","order","siparişlerim","my orders"]),
    ("top_products",     ["ürün","product"]),
    ("total_revenue",    ["satış","gelir","revenue","sale"]),
]

def detect_intent(question: str) -> str:
    q = question.lower()
    for intent, patterns in INTENT_RULES:
        if any(p in q for p in patterns):
            return intent
    return "total_revenue"  # safe default

# ──────────────────────────────────────────────────────────────────────────────
# Pre-written SQL library — real queries against real schema
# Role filters are injected as format parameters
# ──────────────────────────────────────────────────────────────────────────────

def get_sql_for_intent(intent: str, role: str, user_id: Optional[int], store_id: Optional[int]) -> str:
    """
    Returns a complete, executable SQL SELECT statement.
    Role-based WHERE clauses are injected here so the query only returns
    data the caller is authorised to see.
    """

    # Build role filters
    if role == "INDIVIDUAL" and user_id:
        # individual sees only their own rows
        order_filter   = f"WHERE o.user_id = {user_id}"
        order_filter2  = f"WHERE user_id = {user_id}"
        review_filter  = f"WHERE r.user_id = {user_id}"
        product_filter = ""          # products are public
    elif role == "CORPORATE" and store_id:
        order_filter   = f"JOIN stores s ON p.store_id = s.id WHERE s.id = {store_id}"
        order_filter2  = (f"JOIN order_items oi2 ON o.id = oi2.order_id "
                          f"JOIN products p2 ON oi2.product_id = p2.id "
                          f"WHERE p2.store_id = {store_id}")
        review_filter  = f"JOIN products rp ON r.product_id = rp.id WHERE rp.store_id = {store_id}"
        product_filter = f"WHERE p.store_id = {store_id}"
    else:
        # ADMIN or unfiltered
        order_filter   = ""
        order_filter2  = ""
        review_filter  = ""
        product_filter = ""

    SQLS: dict[str, str] = {

        "order_status": f"""
            SELECT
                o.status                                AS durum,
                COUNT(*)                                AS sipariş_sayısı,
                ROUND(SUM(o.total_amount), 2)           AS toplam_gelir
            FROM orders o
            {order_filter2}
            GROUP BY o.status
            ORDER BY sipariş_sayısı DESC;
        """,

        "order_pipeline": f"""
            SELECT
                o.status                    AS durum,
                COUNT(*)                    AS adet,
                ROUND(SUM(o.total_amount),2) AS bekleyen_tutar
            FROM orders o
            {order_filter2}
            {"AND" if order_filter2 else "WHERE"} o.status IN ('PENDING','PROCESSING')
            GROUP BY o.status;
        """,

        "top_products": f"""
            SELECT
                p.name                                        AS ürün,
                SUM(oi.quantity)                              AS satış_adedi,
                ROUND(SUM(oi.unit_price * oi.quantity), 2)   AS toplam_gelir,
                ROUND(p.price, 2)                             AS birim_fiyat
            FROM order_items oi
            JOIN products p  ON oi.product_id = p.id
            JOIN orders   o  ON oi.order_id   = o.id
            {('WHERE p.store_id = ' + str(store_id)) if (role == 'CORPORATE' and store_id) else
             ('WHERE o.user_id = '  + str(user_id))  if (role == 'INDIVIDUAL' and user_id) else ''}
            GROUP BY p.id, p.name, p.price
            ORDER BY satış_adedi DESC
            LIMIT 10;
        """,

        "category_revenue": f"""
            SELECT
                COALESCE(c.name, 'Kategorisiz')             AS kategori,
                COUNT(DISTINCT p.id)                         AS ürün_sayısı,
                SUM(oi.quantity)                             AS satış_adedi,
                ROUND(SUM(oi.unit_price * oi.quantity), 2)  AS toplam_gelir
            FROM order_items oi
            JOIN products   p  ON oi.product_id = p.id
            LEFT JOIN categories c ON p.category_id = c.id
            JOIN orders     o  ON oi.order_id = o.id
            {('WHERE p.store_id = ' + str(store_id)) if (role == 'CORPORATE' and store_id) else
             ('WHERE o.user_id = '  + str(user_id))  if (role == 'INDIVIDUAL' and user_id) else ''}
            GROUP BY c.name
            ORDER BY toplam_gelir DESC;
        """,

        "customer_city": f"""
            SELECT
                COALESCE(u.city, 'Bilinmiyor')  AS şehir,
                COUNT(DISTINCT o.user_id)        AS müşteri_sayısı,
                COUNT(o.id)                      AS sipariş_sayısı,
                ROUND(SUM(o.total_amount), 2)    AS toplam_gelir
            FROM orders o
            JOIN users u ON o.user_id = u.id
            {"JOIN order_items oi3 ON o.id = oi3.order_id JOIN products p3 ON oi3.product_id = p3.id WHERE p3.store_id = " + str(store_id) if (role == 'CORPORATE' and store_id) else ""}
            GROUP BY u.city
            ORDER BY toplam_gelir DESC
            LIMIT 15;
        """,

        "shipment_mode": f"""
            SELECT
                sh.mode_of_shipment     AS kargo_modu,
                sh.status               AS durum,
                COUNT(*)                AS adet
            FROM shipments sh
            JOIN orders o ON sh.order_id = o.id
            {order_filter2}
            GROUP BY sh.mode_of_shipment, sh.status
            ORDER BY adet DESC
            LIMIT 20;
        """,

        "product_rating": f"""
            SELECT
                p.name                          AS ürün,
                ROUND(AVG(r.star_rating), 2)    AS ortalama_puan,
                COUNT(r.id)                     AS yorum_sayısı,
                MIN(r.star_rating)              AS min_puan,
                MAX(r.star_rating)              AS max_puan
            FROM reviews r
            JOIN products p ON r.product_id = p.id
            {('WHERE p.store_id = ' + str(store_id)) if (role == 'CORPORATE' and store_id) else
             ('WHERE r.user_id = '  + str(user_id))  if (role == 'INDIVIDUAL' and user_id) else ''}
            GROUP BY p.id, p.name
            HAVING yorum_sayısı >= 1
            ORDER BY ortalama_puan ASC
            LIMIT 10;
        """,

        "weekly_revenue": f"""
            SELECT
                DAYNAME(o.order_date)           AS gün,
                COUNT(o.id)                     AS sipariş_sayısı,
                ROUND(SUM(o.total_amount), 2)   AS gelir
            FROM orders o
            {order_filter2}
            WHERE o.order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DAYNAME(o.order_date), DAYOFWEEK(o.order_date)
            ORDER BY DAYOFWEEK(o.order_date);
        """,

        "monthly_revenue": f"""
            SELECT
                DATE_FORMAT(o.order_date, '%Y-%m')  AS ay,
                COUNT(o.id)                          AS sipariş_sayısı,
                ROUND(SUM(o.total_amount), 2)        AS gelir
            FROM orders o
            {order_filter2}
            GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
            ORDER BY ay DESC
            LIMIT 12;
        """,

        "membership": f"""
            SELECT
                COALESCE(cp.membership_type, 'Standart')  AS üyelik_tipi,
                COUNT(cp.id)                               AS üye_sayısı,
                ROUND(AVG(cp.total_spend), 2)              AS ort_harcama,
                ROUND(SUM(cp.total_spend), 2)              AS toplam_harcama
            FROM customer_profiles cp
            {"JOIN users u ON cp.user_id = u.id JOIN orders o ON u.id = o.user_id JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id WHERE p.store_id = " + str(store_id) if (role == 'CORPORATE' and store_id) else ""}
            GROUP BY cp.membership_type
            ORDER BY ort_harcama DESC;
        """,

        "payment_method": f"""
            SELECT
                COALESCE(o.payment_method, 'Bilinmiyor') AS ödeme_yöntemi,
                COUNT(*)                                   AS işlem_sayısı,
                ROUND(SUM(o.total_amount), 2)             AS toplam_tutar
            FROM orders o
            {order_filter2}
            GROUP BY o.payment_method
            ORDER BY işlem_sayısı DESC;
        """,

        "stock": f"""
            SELECT
                p.name          AS ürün,
                p.sku           AS sku,
                p.stock         AS stok_adedi,
                ROUND(p.price,2) AS birim_fiyat,
                c.name          AS kategori
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            {product_filter}
            ORDER BY p.stock ASC
            LIMIT 15;
        """,

        "spending": f"""
            SELECT
                DATE_FORMAT(o.order_date, '%Y-%m')  AS ay,
                COUNT(o.id)                          AS sipariş_sayısı,
                ROUND(SUM(o.total_amount), 2)        AS harcama
            FROM orders o
            {order_filter2 if order_filter2 else ('WHERE o.user_id = ' + str(user_id)) if user_id else ''}
            GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
            ORDER BY ay DESC
            LIMIT 12;
        """,

        "total_revenue": f"""
            SELECT 'Toplam Siparis' AS metrik, COUNT(*) AS deger
            FROM orders o {order_filter2}
            UNION ALL
            SELECT 'Teslim Edilen', COUNT(*)
            FROM orders o {order_filter2}
            {"AND" if order_filter2 else "WHERE"} o.status = 'DELIVERED'
            UNION ALL
            SELECT 'Toplam Gelir TL', ROUND(SUM(o.total_amount), 0)
            FROM orders o {order_filter2}
            UNION ALL
            SELECT 'Benzersiz Musteri', COUNT(DISTINCT o.user_id)
            FROM orders o {order_filter2};
        """,
    }

    sql = SQLS.get(intent, SQLS["total_revenue"])
    # Clean up extra whitespace
    return " ".join(sql.split())


# ──────────────────────────────────────────────────────────────────────────────
# Analysis text generator — reads actual data rows
# ──────────────────────────────────────────────────────────────────────────────

def _f(v) -> float:
    """Safe float conversion for DB Decimal/str/None values."""
    try: return float(v or 0)
    except: return 0.0

def _i(v) -> int:
    try: return int(v or 0)
    except: return 0


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
            delivered = next((_i(r.get("sipariş_sayısı", 0)) for r in rows if str(r.get("durum","")).upper() == "DELIVERED"), 0)
            pct = round(delivered / total * 100) if total else 0
            lines = [f"**Sipariş Durum Analizi** ({scope}):",
                     f"• Toplam **{total}** sipariş incelendi",
                     f"• **{delivered}** sipariş teslim edildi (**%{pct}** tamamlanma)"]
            for r in rows:
                lines.append(f"• {r.get('durum','')}: {_i(r.get('sipariş_sayısı',0))} adet  —  {_f(r.get('toplam_gelir',0)):,.0f} TL")
            return "\n".join(lines)

        elif intent == "order_pipeline":
            total = sum(_i(r.get("adet", 0)) for r in rows)
            return (f"**Bekleyen İşlem Analizi** ({scope}):\n"
                    f"• Toplam **{total}** sipariş işlem bekliyor\n" +
                    "\n".join(f"• {r.get('durum','')}: {_i(r.get('adet',0))} adet" for r in rows))

        elif intent == "top_products":
            top = rows[0]
            name_key = next((k for k in top.keys() if "ürün" in k.lower() or "name" in k.lower()), list(top.keys())[0])
            sold_key = next((k for k in top.keys() if "satış" in k.lower() or "sold" in k.lower() or "adet" in k.lower()), None)
            rev_key  = next((k for k in top.keys() if "gelir" in k.lower() or "revenue" in k.lower()), None)
            lines = [f"**En Çok Satan Ürünler** ({scope}):"]
            for i, r in enumerate(rows[:5], 1):
                line = f"**{i}.** {r.get(name_key,'')}"
                if sold_key: line += f" — {_i(r.get(sold_key,0))} adet"
                if rev_key:  line += f" / {_f(r.get(rev_key,0)):,.0f} TL"
                lines.append(f"• {line}")
            return "\n".join(lines)

        elif intent == "category_revenue":
            top = rows[0]
            total_rev = sum(_f(r.get("toplam_gelir", 0)) for r in rows)
            lines = [f"**Kategori Gelir Analizi** ({scope}):",
                     f"• **{top.get('kategori','')}** kategorisi {_f(top.get('toplam_gelir',0)):,.0f} TL ile lider",
                     f"• Toplam gelir: {total_rev:,.0f} TL",
                     f"• {len(rows)} kategori analiz edildi"]
            return "\n".join(lines)

        elif intent == "customer_city":
            top = rows[0]
            total_cust = sum(_i(r.get("müşteri_sayısı", 0)) for r in rows)
            return (f"**Müşteri Şehir Dağılımı** ({scope}):\n"
                    f"• **{top.get('şehir','')}** {_i(top.get('müşteri_sayısı',0))} müşteri ile lider\n"
                    f"• Toplam {total_cust} benzersiz müşteri, {len(rows)} şehirde\n"
                    f"• En yüksek şehir geliri: {_f(top.get('toplam_gelir',0)):,.0f} TL")

        elif intent == "shipment_mode":
            total = sum(_i(r.get("adet", 0)) for r in rows)
            top = rows[0]
            return (f"**Kargo Modu Analizi** ({scope}):\n"
                    f"• Toplam {total} gönderi incelendi\n"
                    f"• En yaygın: **{top.get('kargo_modu','')}** – {top.get('durum','')} ({_i(top.get('adet',0))} adet)\n"
                    f"• {len(rows)} farklı kargo/durum kombinasyonu mevcut")

        elif intent == "product_rating":
            worst  = rows[0]
            p_key  = next((k for k in worst.keys() if "ürün" in k.lower() or "name" in k.lower()), list(worst.keys())[0])
            r_key  = next((k for k in worst.keys() if "puan" in k.lower() or "rating" in k.lower()), None)
            stars  = int(_f(worst.get(r_key, 0))) if r_key else 0
            lines  = [f"**Ürün Değerlendirme Analizi** ({scope}):"]
            lines.append(f"• En düşük puanlı: **{worst.get(p_key,'')}** ({stars}/5 yildiz)")
            total_reviews = sum(_i(r.get("yorum_sayısı", 0)) for r in rows)
            lines.append(f"• Toplam {total_reviews} yorum incelendi")
            lines.append(f"• {len(rows)} ürün değerlendirildi")
            return "\n".join(lines)

        elif intent in ("weekly_revenue", "monthly_revenue"):
            rev_key = next((k for k in rows[0].keys() if "gelir" in k.lower() or "revenue" in k.lower()), None)
            if rev_key:
                total = sum(_f(r.get(rev_key, 0)) for r in rows)
                best  = max(rows, key=lambda x: _f(x.get(rev_key, 0)))
                period_key = list(rows[0].keys())[0]
                label = "Haftalık" if intent == "weekly_revenue" else "Aylık"
                return (f"**{label} Gelir Trendi** ({scope}):\n"
                        f"• Toplam: {total:,.0f} TL\n"
                        f"• En yüksek dönem: **{best.get(period_key,'')}** – {_f(best.get(rev_key,0)):,.0f} TL\n"
                        f"• {len(rows)} dönem analiz edildi")

        elif intent == "membership":
            total_members = sum(_i(r.get("üye_sayısı", 0)) for r in rows)
            top = rows[0] if rows else {}
            return (f"**Üyelik Tier Analizi** ({scope}):\n"
                    f"• Toplam {total_members} üye\n"
                    f"• **{top.get('üyelik_tipi','')}** üyeler ortalama {_f(top.get('ort_harcama',0)):,.0f} TL harcıyor\n"
                    f"• {len(rows)} üyelik tipi mevcut")

        elif intent == "payment_method":
            total = sum(_i(r.get("işlem_sayısı", 0)) for r in rows)
            top = rows[0]
            return (f"**Ödeme Yöntemi Analizi** ({scope}):\n"
                    f"• **{top.get('ödeme_yöntemi','')}** {_i(top.get('işlem_sayısı',0))} işlemle en popüler\n"
                    f"• Toplam {total} işlem analiz edildi\n"
                    f"• {len(rows)} farklı ödeme yöntemi kullanılıyor")

        elif intent == "stock":
            critical = [r for r in rows if _i(r.get("stok_adedi", 999)) < 10]
            return (f"**Stok Durumu** ({scope}):\n"
                    f"• En düşük stoklu ürün: **{rows[0].get('ürün','')}** ({_i(rows[0].get('stok_adedi',0))} adet)\n"
                    f"• **{len(critical)}** ürün kritik stok seviyesinde (< 10 adet)\n"
                    f"• {len(rows)} ürün listelendi")

        elif intent == "spending":
            rev_key = next((k for k in rows[0].keys() if "harcama" in k.lower()), None)
            if rev_key:
                total = sum(_f(r.get(rev_key, 0)) for r in rows)
                best  = max(rows, key=lambda x: _f(x.get(rev_key, 0)))
                period_key = list(rows[0].keys())[0]
                return (f"**Harcama Analizi** ({scope}):\n"
                        f"• Toplam harcama: {total:,.0f} TL\n"
                        f"• En yüksek ay: **{best.get(period_key,'')}** – {_f(best.get(rev_key,0)):,.0f} TL\n"
                        f"• {len(rows)} ay analiz edildi")

        elif intent == "total_revenue":
            kv = {r.get("metrik", ""): r.get("deger", 0) for r in rows}
            return (f"**Platform Gelir Ozeti** ({scope}):\n"
                    f"• Toplam Siparis: **{_i(kv.get('Toplam Siparis', 0)):,}**\n"
                    f"• Teslim Edilen: **{_i(kv.get('Teslim Edilen', 0)):,}**\n"
                    f"• Toplam Gelir: **{_f(kv.get('Toplam Gelir TL', 0)):,.0f} TL**\n"
                    f"• Benzersiz Musteri: **{_i(kv.get('Benzersiz Musteri', 0)):,}**")

    except Exception as ex:
        logger.warning(f"Analysis generation error: {ex}")

    # Fallback
    return f"Analiz tamamlandı. {len(rows)} kayıt {scope} bulundu."


# ──────────────────────────────────────────────────────────────────────────────
# Chart builder — always produces clean Plotly JSON from real rows
# ──────────────────────────────────────────────────────────────────────────────

PALETTE = ["#8c52ff","#06b6d4","#10b981","#f59e0b","#ef4444","#a78bfa","#34d399","#fbbf24","#60a5fa","#fb923c"]

def build_chart(intent: str, rows: list, question: str) -> Optional[str]:
    if not rows or len(rows) < 2:
        return None
    try:
        keys = list(rows[0].keys())
        if len(keys) < 2:
            return None

        x_key = keys[0]
        # first numeric column after the first key — skip string-only columns like sku/name
        y_key = None
        for k in keys[1:]:
            sample = str(rows[0].get(k, ""))
            # skip obvious non-numeric columns
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

        # Chart type by intent
        if intent in ("weekly_revenue", "monthly_revenue", "spending"):
            trace = {
                "x": labels, "y": values,
                "type": "scatter", "mode": "lines+markers",
                "fill": "tozeroy",
                "line":   {"color": "#8c52ff", "width": 3, "shape": "spline"},
                "marker": {"color": "#8c52ff", "size": 7},
                "fillcolor": "rgba(140,82,255,0.12)"
            }
        elif intent in ("order_status", "payment_method", "membership", "shipment_mode") and len(rows) <= 7:
            trace = {
                "labels": labels, "values": values, "type": "pie",
                "marker": {"colors": PALETTE[:len(labels)]},
                "hole": 0.38,
                "textinfo": "label+percent+value",
                "textfont": {"color": "#e2e8f0", "size": 11}
            }
        else:
            trace = {
                "x": labels, "y": values, "type": "bar",
                "marker": {"color": PALETTE[:len(labels)], "opacity": 0.9},
                "text": [f"{v:,.0f}" if v >= 1 else f"{v:.2f}" for v in values],
                "textposition": "outside",
                "textfont": {"color": "#94a3b8", "size": 10}
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
                "gridcolor": "rgba(148,163,184,0.08)", "linecolor": "rgba(148,163,184,0.15)",
                "tickfont":  {"color": "#64748b"},
                "title": {"text": x_key.replace("_", " ").title(), "font": {"color": "#64748b", "size": 11}}
            }
            layout["yaxis"] = {
                "gridcolor": "rgba(148,163,184,0.08)", "linecolor": "rgba(148,163,184,0.15)",
                "tickfont":  {"color": "#64748b"}, "rangemode": "tozero",
                "title": {"text": y_key.replace("_", " ").title(), "font": {"color": "#64748b", "size": 11}}
            }

        return json.dumps({"data": [trace], "layout": layout})
    except Exception as ex:
        logger.warning(f"Chart build error: {ex}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# LangGraph Node Functions
# ──────────────────────────────────────────────────────────────────────────────

def guardrails_node(state: AgentState) -> AgentState:
    import re as _re
    q = state["question"].lower().strip()
    # Use word-boundary match so "hi" inside "şehir" doesn't trigger greeting
    if any(_re.search(r'(^|\s)' + _re.escape(k) + r'(\s|$|[!?,.])', q) for k in GREETING_KW):
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

    if USE_LLM:
        try:
            ans = llm.invoke([HumanMessage(content=(
                "E-ticaret analitik platformu. Soru kapsam dahilinde mi?\n"
                "Kapsam: satış, sipariş, ürün, müşteri, kargo, gelir, stok, yorum, ödeme, mağaza.\n"
                "Sadece SCOPE veya OUT_OF_SCOPE yaz.\n\n"
                f"Soru: {state['question']}"
            ))]).content.strip().upper()
            state["is_in_scope"] = "OUT" not in ans
        except Exception:
            state["is_in_scope"] = _contains(state["question"], IN_SCOPE_KW)
    else:
        state["is_in_scope"] = _contains(state["question"], IN_SCOPE_KW)

    if not state["is_in_scope"]:
        state["final_answer"] = (
            "Bu soru e-ticaret analiz kapsamı dışında.\n"
            "Satış, sipariş, ürün, müşteri veya kargo hakkında sorular sorabilirsiniz."
        )
    return state


def sql_generator_node(state: AgentState) -> AgentState:
    intent = detect_intent(state["question"])
    state["intent"] = intent

    if USE_LLM:
        role     = state.get("role", "INDIVIDUAL")
        user_id  = state.get("user_id")
        store_id = state.get("store_id")

        role_ctx = ""
        if role == "INDIVIDUAL" and user_id:
            role_ctx = (f"\nCRITICAL: INDIVIDUAL user (user_id={user_id}). "
                        "Every query MUST filter with WHERE o.user_id={user_id} or equivalent.")
        elif role == "CORPORATE" and store_id:
            role_ctx = (f"\nCRITICAL: CORPORATE user (store_id={store_id}). "
                        "Only return data belonging to this store.")
        else:
            role_ctx = "\nADMIN: full platform access."

        prev_err = state.get("error_message", "")
        fix = f"\nPrevious attempt failed: {prev_err}\nFix the error." if prev_err else ""

        try:
            raw = llm.invoke([HumanMessage(content=(
                f"Senior MySQL developer. E-commerce analytics.\n{DB_SCHEMA}\n{role_ctx}{fix}\n"
                "Rules: SELECT only, LIMIT 100, no markdown.\n\n"
                f"Question: {state['question']}\nSQL:"
            ))]).content.strip()
            sql = raw.replace("```sql","").replace("```","").strip()
            if not sql.endswith(";"): sql += ";"
            state["sql_query"] = sql
            state["error"] = None
            state["error_message"] = None
        except Exception as ex:
            state["error"] = "generation_failed"
            state["error_message"] = str(ex)
    else:
        # Use pre-written SQL for the detected intent
        sql = get_sql_for_intent(
            intent,
            state.get("role", "INDIVIDUAL"),
            state.get("user_id"),
            state.get("store_id")
        )
        state["sql_query"] = sql
        state["error"] = None
        state["error_message"] = None

    return state


def sql_executor_node(state: AgentState) -> AgentState:
    sql = (state.get("sql_query") or "").strip()
    if not sql:
        state["error"] = "no_sql"
        return state

    sql_up = sql.upper()
    # Security: SELECT only
    if not sql_up.lstrip().startswith("SELECT"):
        state["error"] = "security_violation"
        state["final_answer"] = "Güvenlik: Yalnızca SELECT sorguları çalıştırılabilir."
        return state
    for bad in ("DROP","DELETE","INSERT","UPDATE","TRUNCATE","ALTER","CREATE","EXEC","GRANT"):
        if bad in sql_up:
            state["error"] = "security_violation"
            state["final_answer"] = f"Güvenlik ihlali: '{bad}' komutu yasak."
            return state

    if not DB_OK or engine is None:
        state["error"] = "db_unavailable"
        state["error_message"] = "Veritabanına bağlanılamıyor."
        state["final_answer"] = "⚠️ Veritabanına bağlanılamıyor. Lütfen MySQL servisinin çalıştığını kontrol edin."
        return state

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows   = result.fetchmany(100)
            cols   = list(result.keys())
            df     = pd.DataFrame(rows, columns=cols)
            state["query_result"]  = df.to_json(orient="records", force_ascii=False) if not df.empty else "[]"
            state["error"]         = None
            state["error_message"] = None
            logger.info(f"Query OK — {len(df)} rows, intent={state.get('intent')}")
    except Exception as ex:
        state["error"]         = "sql_error"
        state["error_message"] = str(ex)
        state["query_result"]  = None
        logger.warning(f"SQL error: {ex}\nSQL: {sql[:200]}")
    return state


def error_handler_node(state: AgentState) -> AgentState:
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    if state["iteration_count"] >= 3:
        state["final_answer"] = "Sorgu 3 denemeden sonra çalışmadı. Soruyu farklı şekilde deneyin."
        state["error"] = "max_retries"
        return state

    if state.get("error") == "db_unavailable":
        return state  # can't recover without DB

    if USE_LLM:
        try:
            fixed = llm.invoke([HumanMessage(content=(
                f"Fix this MySQL error.\nQuestion: {state['question']}\n"
                f"Bad SQL: {state['sql_query']}\nError: {state['error_message']}\n"
                f"{DB_SCHEMA}\nReturn only corrected SQL:"
            ))]).content.strip()
            fixed = fixed.replace("```sql","").replace("```","").strip()
            if not fixed.endswith(";"): fixed += ";"
            state["sql_query"] = fixed
            state["error"] = None
            state["error_message"] = None
        except Exception as ex:
            state["error"] = "fix_failed"
            state["error_message"] = str(ex)
    else:
        # Fallback to a simpler pre-written SQL
        intent = state.get("intent") or detect_intent(state["question"])
        state["sql_query"] = get_sql_for_intent(
            "total_revenue",          # safest fallback
            state.get("role","INDIVIDUAL"),
            state.get("user_id"),
            state.get("store_id")
        )
        state["error"] = None
        state["error_message"] = None
    return state


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
                ans = llm.invoke([HumanMessage(content=(
                    "Helpful data analyst. Explain results to a business user.\n"
                    "2-4 sentences, key findings. Reply in Turkish.\n\n"
                    f"Question: {state['question']}\nData: {result[:2500]}\nAnalysis:"
                ))]).content.strip()
                state["final_answer"] = ans
                return state
            except Exception:
                pass  # fall through to rule-based

        state["final_answer"] = generate_analysis(
            intent, rows, state.get("role","INDIVIDUAL"), state["question"]
        )
    except Exception as ex:
        logger.warning(f"Analysis error: {ex}")
        state["final_answer"] = "Veriler başarıyla getirildi."
    return state


def viz_decision_node(state: AgentState) -> AgentState:
    result = state.get("query_result", "[]")
    try:
        rows = json.loads(result) if result else []
        state["needs_viz"] = len(rows) >= 2
    except Exception:
        state["needs_viz"] = False
    return state


def visualization_node(state: AgentState) -> AgentState:
    result = state.get("query_result", "[]")
    try:
        rows   = json.loads(result) if result else []
        intent = state.get("intent") or detect_intent(state["question"])
        state["visualization_code"] = build_chart(intent, rows, state["question"])
    except Exception as ex:
        logger.warning(f"Viz error: {ex}")
        state["visualization_code"] = None
    return state


# ──────────────────────────────────────────────────────────────────────────────
# Routing
# ──────────────────────────────────────────────────────────────────────────────

def route_guardrails(state: AgentState) -> Literal["sql_generator","__end__"]:
    return "sql_generator" if state["is_in_scope"] and not state.get("is_greeting") else END

def route_executor(state: AgentState) -> Literal["error_handler","analyzer"]:
    err = state.get("error")
    return "error_handler" if err and err not in ("security_violation","db_unavailable") else "analyzer"

def route_error(state: AgentState) -> Literal["sql_executor","__end__"]:
    return END if state.get("error") in ("max_retries","fix_failed","security_violation","db_unavailable") else "sql_executor"

def route_viz(state: AgentState) -> Literal["visualizer","__end__"]:
    return "visualizer" if state.get("needs_viz") else END


# ──────────────────────────────────────────────────────────────────────────────
# Build graph
# ──────────────────────────────────────────────────────────────────────────────

def build_graph():
    wf = StateGraph(AgentState)
    wf.add_node("guardrails",    guardrails_node)
    wf.add_node("sql_generator", sql_generator_node)
    wf.add_node("sql_executor",  sql_executor_node)
    wf.add_node("error_handler", error_handler_node)
    wf.add_node("analyzer",      analysis_node)
    wf.add_node("viz_decision",  viz_decision_node)
    wf.add_node("visualizer",    visualization_node)
    wf.set_entry_point("guardrails")
    wf.add_conditional_edges("guardrails",    route_guardrails, {"sql_generator":"sql_generator",END:END})
    wf.add_edge("sql_generator",  "sql_executor")
    wf.add_conditional_edges("sql_executor",  route_executor,   {"error_handler":"error_handler","analyzer":"analyzer"})
    wf.add_conditional_edges("error_handler", route_error,      {"sql_executor":"sql_executor",END:END})
    wf.add_edge("analyzer",       "viz_decision")
    wf.add_conditional_edges("viz_decision",  route_viz,        {"visualizer":"visualizer",END:END})
    wf.add_edge("visualizer", END)
    return wf.compile()

agent_graph = build_graph()
logger.info(f"LangGraph ready — LLM={'ON' if USE_LLM else 'OFF'}, DB={'OK' if DB_OK else 'FAIL'}")


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="DataPulse Text2SQL API", version="5.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    message:  str
    role:     str           = "INDIVIDUAL"
    user_id:  Optional[int] = None
    store_id: Optional[int] = None


def make_state(req: ChatRequest) -> AgentState:
    return {
        "question": req.message, "role": req.role,
        "user_id": req.user_id, "store_id": req.store_id,
        "is_in_scope": False, "is_greeting": False,
        "sql_query": None, "query_result": None,
        "error": None, "error_message": None,
        "final_answer": None, "needs_viz": False,
        "visualization_code": None, "iteration_count": 0,
        "intent": None,
    }


@app.post("/api/chat/ask")
def chat_ask(req: ChatRequest):
    try:
        final = agent_graph.invoke(make_state(req))
    except Exception as ex:
        logger.error(f"Graph error: {ex}")
        return {"answer": "Beklenmedik bir hata oluştu.", "sql": None, "plotData": None}
    return {
        "answer":   final.get("final_answer") or "Yanıt üretilemedi.",
        "sql":      final.get("sql_query"),
        "plotData": final.get("visualization_code"),
    }


THINKING_PHASES = [
    "Sorgunuz analiz ediliyor...",
    "Kapsam doğrulanıyor...",
    "SQL sorgusu oluşturuluyor...",
    "Veritabanı sorgulanıyor...",
    "Sonuçlar yorumlanıyor...",
    "Grafik hazırlanıyor...",
]


async def _event_stream(req: ChatRequest) -> AsyncGenerator[str, None]:
    def sse(ev: str, data: dict) -> str:
        return f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    loop = asyncio.get_event_loop()
    task = loop.run_in_executor(None, agent_graph.invoke, make_state(req))

    for phase in THINKING_PHASES:
        if task.done(): break
        yield sse("thinking", {"text": phase})
        await asyncio.sleep(0.55)

    try:
        final = await task
    except Exception as ex:
        yield sse("error", {"message": str(ex)})
        return

    yield sse("result", {
        "answer":   final.get("final_answer") or "Yanıt üretilemedi.",
        "sql":      final.get("sql_query"),
        "plotData": final.get("visualization_code"),
    })
    yield sse("done", {})


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        _event_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no","Connection":"keep-alive"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "llm": USE_LLM, "db": DB_OK}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
