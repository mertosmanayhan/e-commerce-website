"""
agents.py — Five LangGraph agent node functions.

Agents:
  1. guardrails_node      — Security & Scope Manager
  2. sql_generator_node   — SQL Expert (role-aware, 100% LLM-driven)
  3. error_handler_node   — Error Recovery Specialist (max 3 retries)
  4. analysis_node        — Data Analyst
  5. visualization_node   — Visualization Specialist (Plotly JSON)

Supporting nodes:
  • sql_executor_node     — executes SQL against MySQL via SQLAlchemy
  • viz_decision_node     — decides whether a chart is warranted
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

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
USE_LLM  = GROQ_KEY is not None

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
    DB_OK  = False
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
# Keyword helpers (used only for guardrails fallback when LLM is unavailable)
# ──────────────────────────────────────────────────────────────────────────────

GREETING_KW = {
    "merhaba", "selam", "hey", "hi", "hello", "nasılsın", "naber",
    "iyi günler", "günaydın", "iyi akşamlar", "selamlar",
}

# ── Security: Prompt-injection patterns (AV-01) ───────────────────────────────
_INJECTION_PATTERNS = [
    # Role override attempts
    r"ignore\s+(previous|all|above|prior)\s+instructions?",
    r"forget\s+(your|all|previous|the)\s+(rules?|instructions?|prompt|context)",
    r"pretend\s+(you\s+are|to\s+be|you're)\s+(?:an?\s+)?(admin|root|superuser|system|god|unrestricted)",
    r"act\s+as\s+(?:an?\s+)?(admin|root|superuser|dba|unrestricted|jailbroken)",
    r"you\s+are\s+now\s+(?:an?\s+)?(admin|unrestricted|dba|superuser)",
    r"roleplay\s+as",
    r"new\s+role\s*:",
    r"override\s+(security|restrictions?|rules?|filters?)",
    r"disable\s+(security|filters?|guardrails?|restrictions?)",
    r"bypass\s+(security|filters?|guardrails?|restrictions?|authentication)",
    r"jailbreak",
    r"developer\s+mode",
    r"sudo\s+",
    # AV-01: System/role override via bracket or colon syntax
    r"\[\s*system\s*(override|prompt|instruction|command|message)\s*\]",
    r"system\s+override",
    r"user\s+role\s*[=:]\s*(admin|corporate|root|superuser)",
    r"role\s*(override|=|:)\s*(admin|corporate|root|superuser)",
    r"disregard\s+(prior|previous|all|above)\s+(role|constraint|instruction|rule)",
    r"ignore\s+(role|constraint|restriction|rule)\s+(constraint|filter|check)?",
    # System prompt extraction (AV-07)
    r"repeat\s+(your|the)\s+system\s+prompt",
    r"what\s+(were\s+you|are\s+your)\s+(instructions?|rules?|prompt)",
    r"print\s+(your|the)\s+(system\s+prompt|instructions?|rules?)",
    r"reveal\s+(your|the)\s+(instructions?|prompt|rules?|context)",
    r"show\s+(me\s+)?(your|the)\s+(instructions?|prompt|system)",
    r"what\s+instructions?\s+were\s+you\s+given",
    r"tell\s+me\s+your\s+(rules?|constraints?|instructions?)",
    r"output\s+your\s+(system|initial)\s+prompt",
    r"what\s+is\s+your\s+system\s+prompt",
    # Indirect injection attempts
    r"execute\s+the\s+following",
    r"run\s+this\s+(command|query|code|sql)",
    r"eval\s*\(",
    r"exec\s*\(",
    # Turkish injection variants
    r"önceki\s+talimatları\s+(unut|yoksay|görmezden\s+gel)",
    r"kuralları\s+(unut|çiğne|görmezden\s+gel)",
    r"sistem\s+prompt(u|unu)\s+(göster|yaz|tekrar\s+et)",
    r"talimatlarını\s+(göster|söyle|tekrar\s+et)",
]

# ── Security: Introspection / system-leakage keywords (AV-07) ────────────────
_INTROSPECTION_KW = {
    "system prompt", "initial prompt", "your instructions", "your rules",
    "your constraints", "what tables exist", "show tables", "list tables",
    "information_schema", "table_schema", "column_names", "schema_name",
    "repeat your", "print your prompt", "reveal your", "output your prompt",
    "what were you told", "what are your restrictions",
    "sistem promptu", "başlangıç promptu", "talimatlarını göster",
    "hangi tablolar var", "tablo listesi", "şema bilgisi",
}

# ── Security: Sensitive account-enumeration keywords (AV-10) ─────────────────
_SENSITIVE_ENUM_KW = {
    # Password / credential fishing
    "password", "passwords", "şifre", "şifreler", "parola", "parolalar",
    "hash", "hashed password", "bcrypt", "credential", "credentials",
    # PII exfiltration
    "email adresleri", "email listesi", "tüm mailler", "bütün mailler",
    "tüm email", "kullanıcı mailleri", "all emails", "list emails",
    "phone", "telefon", "address", "adres",
    # Token / session fishing
    "token", "refresh token", "jwt", "secret", "api key", "api_key",
    "private key", "gizli anahtar",
    # Account enumeration
    "tüm kullanıcı şifre", "bütün kullanıcı şifre",
    "all user passwords", "dump users", "kullanıcı dump",
    "admin şifresi", "admin password", "root password",
}

# ── Security: SQL injection extra patterns (AV-03/AV-12) ──────────────────────
_SQL_INJECTION_PATTERNS = [
    r"union\s+(?:all\s+)?select",
    r"--\s",           # SQL comment
    r"/\*.*?\*/",      # block comment
    r";\s*(?:drop|delete|insert|update|alter|truncate|create|exec|grant|revoke)",
    r"xp_cmdshell",
    r"information_schema",
    r"sleep\s*\(",
    r"benchmark\s*\(",
    r"load_file\s*\(",
    r"into\s+outfile",
    r"into\s+dumpfile",
    r"char\s*\(\s*\d",
    r"0x[0-9a-fA-F]{4,}",  # hex encoding
]

# ── ADMIN banned columns (AV-12 — prevent sensitive SELECT *) ─────────────────
_ADMIN_BANNED_COLS = {
    "users.password", "users.password_hash", "u.password",
    "password_hash", "password",
}


def _check_injection(q: str) -> bool:
    """Returns True if the question matches any injection pattern."""
    ql = q.lower()
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, ql, re.IGNORECASE):
            return True
    return False


def _check_introspection(q: str) -> bool:
    ql = q.lower()
    return any(k in ql for k in _INTROSPECTION_KW)


def _check_sensitive_enum(q: str) -> bool:
    ql = q.lower()
    return any(k in ql for k in _SENSITIVE_ENUM_KW)


def _check_sql_injection(q: str) -> bool:
    ql = q.lower()
    for pat in _SQL_INJECTION_PATTERNS:
        if re.search(pat, ql, re.IGNORECASE | re.DOTALL):
            return True
    return False

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
    "istatistik", "statistic", "geçen", "bu ay", "bu hafta", "last month",
}


def _contains(txt: str, keywords: set) -> bool:
    t = txt.lower()
    return any(k in t for k in keywords)


# ──────────────────────────────────────────────────────────────────────────────
# Plotly chart builder (rule-based fallback when LLM viz fails)
# ──────────────────────────────────────────────────────────────────────────────

PALETTE = [
    "#8c52ff", "#06b6d4", "#10b981", "#f59e0b", "#ef4444",
    "#a78bfa", "#34d399", "#fbbf24", "#60a5fa", "#fb923c",
]


def build_chart(rows: list, question: str) -> Optional[str]:
    if not rows or len(rows) < 2:
        return None
    try:
        keys = list(rows[0].keys())
        if len(keys) < 2:
            return None

        x_key = keys[0]
        y_key = None
        for k in keys[1:]:
            try:
                float(str(rows[0].get(k, "") or 0))
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

        q = question.lower()
        is_time_series = any(w in q for w in ("ay", "hafta", "gün", "month", "week", "trend", "tarih"))
        is_pie_candidate = len(rows) <= 7 and any(
            w in q for w in ("durum", "dağılım", "ödeme", "mod", "üyelik", "status", "distribution")
        )

        if is_time_series:
            trace = {
                "x": labels, "y": values, "type": "scatter",
                "mode": "lines+markers", "fill": "tozeroy",
                "line": {"color": "#8c52ff", "width": 3, "shape": "spline"},
                "marker": {"color": "#8c52ff", "size": 7},
                "fillcolor": "rgba(140,82,255,0.12)",
            }
        elif is_pie_candidate:
            trace = {
                "labels": labels, "values": values, "type": "pie",
                "marker": {"colors": PALETTE[:len(labels)]},
                "hole": 0.38, "textinfo": "label+percent+value",
                "textfont": {"color": "#e2e8f0", "size": 11},
            }
        else:
            trace = {
                "x": labels, "y": values, "type": "bar",
                "marker": {"color": PALETTE[:len(labels)], "opacity": 0.9},
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

_PLATFORM_SCOPE_KW = {
    "sitenizde", "sitenin", "platformda", "platformun", "tüm mağaza",
    "bütün mağaza", "tüm kullanıcı", "bütün kullanıcı", "genel satış",
    "site geneli", "platform geneli", "tüm platform", "bütün platform",
    "sitede en çok", "platformda en çok",
}

_CORP_PLATFORM_KW = {
    "tüm mağaza", "bütün mağaza", "diğer mağaza", "platform geneli",
    "tüm platform", "bütün platform", "site geneli", "tüm satış",
    "bütün satış",
    # English equivalents
    "all stores", "all registered stores", "across all stores",
    "across stores", "every store", "all shops", "platform-wide",
    "all sales", "all registered", "breakdown of sales across",
    "sales across all", "all store sales", "registered stores",
}

# ── INDIVIDUAL veri sızıntısı engeli ──────────────────────────────────────────
# Bireysel kullanıcıların sorularında geçen ve mağaza/envanter alanlarına
# ait olduğu açık olan ifadeler.  "stok", "fiyat maliyeti" vb.  sahip olmadıkları
# bilgilere ulaşmak için kullanılabilir; guardrails bunları erken engeller.
_INDIVIDUAL_RESTRICTED_KW = {
    # stok / envanter
    "stoğu", "stok", "stokta", "stokları", "envanter", "kalan ürün",
    "kaç adet kaldı", "kaç tane kaldı", "ürün kaldı mı",
    # satış istatistikleri (sahip olmadıkları)
    "toplam satış", "kaç kez satıldı", "kaç kişi aldı", "başka kimler aldı",
    "kaç tane satıldı", "satış sayısı", "satış adedi", "ne kadar satıldı",
    "en çok kim aldı", "kimler satın aldı",
    # mağaza / sahiplik perspektifi
    "mağaza geliri", "mağaza karı", "mağaza satışı", "mağaza istatistik",
    "mağaza analiz", "ürünümün satışı", "ürünlerim kaç",
    # maliyet
    "maliyet", "cost", "tedarik fiyatı",
}



def _resolve_role_ids(state: AgentState) -> tuple[str, int | None, int | None]:
    """
    5.8 uyumlu canonical kimlik çözümleyici.
    Hem yeni (current_user_role / buyer_user_id / seller_store_id) hem eski
    (role / user_id / store_id) alanlarını destekler; yeniler varsa öncelikli.
    """
    role     = state.get("current_user_role") or state.get("role", "INDIVIDUAL")
    user_id  = state.get("buyer_user_id")  or state.get("user_id")
    store_id = state.get("seller_store_id") or state.get("store_id")
    return role.upper(), user_id, store_id


def _is_individual_data_leak(q: str) -> bool:
    """
    KURAL 3 — Kavramsal ayrım denetimi.
    Stok / maliyet / satış istatistikleri mağazaya ait verilerdir.
    INDIVIDUAL bunları "aldığım ürünün stoğu" gibi sahiplik bağlamıyla sorse de
    erişim hakkı yoktur — restricted ifade varsa her durumda engelle.
    """
    return any(k in q for k in _INDIVIDUAL_RESTRICTED_KW)


def guardrails_node(state: AgentState) -> AgentState:
    # Canonical kimlik çözümle ve state'e yaz (hem yeni hem eski alanları doldur)
    role, user_id, store_id = _resolve_role_ids(state)
    state["current_user_role"] = role
    state["buyer_user_id"]     = user_id if role == "INDIVIDUAL" else None
    state["seller_store_id"]   = store_id if role == "CORPORATE" else None
    # Geriye dönük uyumluluk
    state["role"]     = role
    state["user_id"]  = user_id
    state["store_id"] = store_id

    q   = state["question"].lower().strip()
    raw = state["question"]  # original for pattern matching

    # ── AV-01: Prompt injection hard-block ──────────────────────────────────
    if _check_injection(raw):
        logger.warning(f"Prompt injection attempt blocked — role={role}: {raw[:120]}")
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Bu tür istekler güvenlik politikası gereği işlenemiyor.\n\n"
            "Yalnızca e-ticaret verileri (satış, sipariş, ürün, müşteri) hakkında "
            "sorular sorabilirsiniz."
        )
        return state

    # ── AV-07: System-prompt / introspection extraction hard-block ──────────
    if _check_introspection(raw):
        logger.warning(f"Introspection attempt blocked — role={role}: {raw[:120]}")
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Sistem yapılandırması ve talimatlar hakkında bilgi paylaşılamaz.\n\n"
            "E-ticaret verileri hakkında sorular sorabilirsiniz."
        )
        return state

    # ── AV-10: Sensitive credential / PII enumeration hard-block ───────────
    if _check_sensitive_enum(raw):
        logger.warning(f"Sensitive enum attempt blocked — role={role}: {raw[:120]}")
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Parola, token veya kişisel kimlik bilgilerine erişim bu sistem "
            "üzerinden mümkün değildir.\n\n"
            "Yalnızca iş analitiği verileri sorgulanabilir."
        )
        return state

    # ── AV-03: SQL injection in question text hard-block ───────────────────
    if _check_sql_injection(raw):
        logger.warning(f"SQL injection attempt in question blocked — role={role}: {raw[:120]}")
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Güvenlik: Sorgu içinde SQL enjeksiyon kalıpları tespit edildi.\n\n"
            "Lütfen doğal dilde soru sorun."
        )
        return state

    # ── Selamlama ────────────────────────────────────────────────────────────
    if any(re.search(r"(^|\s)" + re.escape(k) + r"(\s|$|[!?,.])", q) for k in GREETING_KW):
        state["is_greeting"] = True
        state["is_in_scope"] = False
        if role == "INDIVIDUAL":
            suggestions = (
                "• \"Son siparişlerimin durumu nedir?\"\n"
                "• \"Hangi kategorilere en çok harcama yaptım?\"\n"
                "• \"Aylık harcama trendiim\"\n"
                "• \"En çok satın aldığım ürünler\""
            )
        elif role == "CORPORATE":
            suggestions = (
                "• \"Mağazamın en çok satan ürünleri\"\n"
                "• \"Bu ayki sipariş durum dağılımı\"\n"
                "• \"Mağazamın aylık gelir trendi\"\n"
                "• \"Düşük stoklu ürünlerim\""
            )
        else:
            suggestions = (
                "• \"Sipariş durumu dağılımı nedir?\"\n"
                "• \"En çok satan 5 ürünü göster\"\n"
                "• \"Kategori bazlı gelir analizi\"\n"
                "• \"Aylık satış trendi\""
            )
        state["final_answer"] = (
            "Merhaba! Ben DataPulse AI Asistanım 👋\n\n"
            "E-ticaret verileriniz hakkında soru sorabilirsiniz:\n"
            + suggestions
        )
        return state

    state["is_greeting"] = False

    # ── KURAL 1 — INDIVIDUAL: platform geneli veri yasağı ────────────────────
    if role == "INDIVIDUAL" and any(k in q for k in _PLATFORM_SCOPE_KW):
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Güvenlik prensiplerimiz gereği tüm sitenin satış verilerine erişiminiz bulunmuyor.\n\n"
            "Yalnızca kendi alışveriş geçmişinize erişebilirsiniz:\n"
            "• \"Benim en çok satın aldığım ürünler\"\n"
            "• \"Kendi sipariş durumlarım\"\n"
            "• \"Aylık harcama trendiim\""
        )
        return state

    # ── KURAL 1 — INDIVIDUAL: mağaza/envanter veri sızıntısı yasağı ──────────
    # Bireysel kullanıcı "aldığım ürünün stoğu", "kaç kişi aldı" gibi
    # mağazaya ait bilgileri sorarsa SQL oluşturmadan reddedilir.
    if role == "INDIVIDUAL" and _is_individual_data_leak(q):
        state["is_in_scope"] = False
        state["final_answer"] = (
            "Sadece kendi sipariş detaylarınıza ve ödeme geçmişinize erişebilirsiniz.\n\n"
            "Mağazaya veya ürüne ait stok / satış istatistiklerini görüntüleme "
            "yetkiniz yoktur.\n\n"
            "Sormak isteyebilecekleriniz:\n"
            "• \"Ne zaman sipariş verdim?\"\n"
            "• \"Toplam harcamam ne kadar?\"\n"
            "• \"Hangi ürünleri satın aldım?\""
        )
        return state

    # ── KURAL 2 — CORPORATE: diğer mağazaların verisi yasak ─────────────────
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

    # ── AV-02: CORPORATE — başka store ID'si doğrudan soruda geçiyor mu? ─────
    if role == "CORPORATE" and store_id:
        mentioned_ids = re.findall(r"store(?:\s+id)?\s*[:#=]?\s*(\d+)", q, re.IGNORECASE)
        for mid in mentioned_ids:
            if int(mid) != int(store_id):
                logger.warning(f"AV-02 cross-store in question — own={store_id} requested={mid}")
                state["is_in_scope"] = False
                state["final_answer"] = (
                    "Güvenlik: Başka bir mağazanın verilerine erişim yetkiniz yok.\n\n"
                    "Yalnızca kendi mağazanızın verilerini sorgulayabilirsiniz."
                )
                return state

    # ── LLM kapsam denetimi ──────────────────────────────────────────────────
    if USE_LLM:
        try:
            ans = llm.invoke([HumanMessage(content=(
                f"{GUARDRAILS_SYSTEM}\n\nSoru: {state['question']}"
            ))]).content.strip().upper()
            if "GREETING" in ans:
                state["is_greeting"] = True
                state["is_in_scope"] = False
                state["final_answer"] = "Merhaba! E-ticaret verileri hakkında size nasıl yardımcı olabilirim?"
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
# ② SQL Agent — 100% LLM-driven Text2SQL with Row-Level Security
# ──────────────────────────────────────────────────────────────────────────────

def _build_role_security_block(role: str, user_id, store_id) -> str:
    """
    SQL prompt'una eklenen rol-bazlı güvenlik bloğu.
    5.8 mimarisinin üç kuralını (KURAL 1/2/3) LLM'e iletir.
    """
    if role == "CORPORATE" and store_id:
        return f"""
╔══════════════════════════════════════════════════════════════════════╗
║  ROL: CORPORATE  —  MAĞAZA ID: {store_id}
║
║  KURAL 2 — MAĞAZA İZOLASYONU (MUTLAK ZORUNLU):
║  ▸ "Ürünlerim" = mağazana ait envanter (products.store_id = {store_id}).
║    Satın alınan ürünlerle (order_items) KARIŞTIRMA.
║  ▸ Yazdığın HER sorguda şu filtrelerden uygun olanı MUTLAKA ekle:
║       products tablosu    → WHERE p.store_id = {store_id}
║       order_items tablosu → products JOIN yoluyla WHERE p.store_id = {store_id}
║       orders tablosu      → order_items + products JOIN ile aynı filtre
║       reviews tablosu     → products JOIN ile aynı filtre
║  ▸ JOIN zinciri ne kadar uzun olursa olsun filtreyi ATLAMAZSIN.
║  ▸ store_id = {store_id} dışındaki mağazaların verilerine KESİNLİKLE dokunma.
╚══════════════════════════════════════════════════════════════════════╝
"""
    if role == "INDIVIDUAL" and user_id:
        return f"""
╔══════════════════════════════════════════════════════════════════════╗
║  ROL: INDIVIDUAL  —  KULLANICI ID: {user_id}
║
║  KURAL 1 — ALICI İZOLASYONU (MUTLAK ZORUNLU):
║  ▸ Yazdığın HER sorguda şu filtreleri MUTLAKA ekle:
║       orders tablosu     → WHERE o.user_id = {user_id}
║       reviews tablosu    → WHERE r.user_id = {user_id}
║       cart_items tablosu → WHERE ci.user_id = {user_id}
║  ▸ Diğer kullanıcıların verilerine KESİNLİKLE dokunma.
║
║  KURAL 3 — KOLON KISITLAMASI (VERİ SIZINTISI ENGELİ):
║  ▸ "Satın aldığım ürünler" = order_items üzerinden erişilen ürünler.
║    Bu kavramı "mağaza envanteri" ile KARIŞTIRMA.
║  ▸ products tablosuna JOIN atıldığında SADECE şu kolonları SELECT edebilirsin:
║       p.name, p.description, p.category_id, p.image_url, p.rating
║  ▸ Aşağıdaki kolonları ASLA SELECT ETME (mağaza sahibine ait veriler):
║       p.stock        → stok miktarı (mağazanın envanteri)
║       p.price        → birim fiyat listesi   [SADECE oi.unit_price kullan]
║       p.sku          → stok kodu
║       p.review_count → toplam satış/yorum sayısı platformda
║  ▸ Ürün bazlı agregasyon (kaç kez satıldı, toplam satış adedi vb.)
║    sorgularını oluşturma; bu bilgiler mağaza sahibine aittir.
╚══════════════════════════════════════════════════════════════════════╝
"""
    return "\n[ ROL: ADMIN — Kısıtsız erişim, tüm kolonlar ve tablolar sorgulanabilir. ]\n"


def _build_sql_prompt(question: str, role: str, user_id, store_id,
                      prev_err: str = "") -> str:
    fix_ctx = f"\nÖNCEKİ DENEME BAŞARISIZ:\n{prev_err}\nYukarıdaki hatayı düzelt.\n" if prev_err else ""
    return f"""Sen kıdemli bir MySQL geliştiricisisin. Kullanıcının sorusunu analiz edip doğrudan çalıştırılabilir MySQL SELECT sorgusu yaz.

GENEL KURALLAR:
- Sadece SELECT sorgusu yaz; DROP/DELETE/INSERT/UPDATE/ALTER/TRUNCATE YASAK.
- Varsayılan LIMIT 50 kullan (kullanıcı farklı bir sayı belirtmedikçe).
- Markdown veya açıklama ekleme — sadece ham SQL döndür.
- Geçerli MySQL sözdizimi kullan; alias'ları tutarlı tut.
- Gelir hesaplamalarında (ADMIN/CORPORATE) daima SUM(oi.unit_price * oi.quantity * 1.20) kullan (KDV %20 dahil), SUM(o.total_amount) değil.
- INDIVIDUAL rolü için harcama = SUM(oi.unit_price * oi.quantity) — KDV çarpanı KULLANMA, bu kişisel alışveriş harcamasıdır, mağaza geliri değil.
- Sipariş sayısı için COUNT(DISTINCT o.id) kullan (JOIN çarpımını önler).
- Ürün sayısı/envanteri soruları için SADECE products tablosunu sorgula (SELECT COUNT(*) FROM products). order_items tablosuna JOIN ATMA — zaman filtresi ürün envanterini etkilemez.

════════════════════════════════════════════════════════════════
TABLO İLİŞKİLERİ — KESİN KURALLAR (ASLA İHLAL ETME)
════════════════════════════════════════════════════════════════

▸ KURAL 1 — orders.user_id SADECE ALICIDIR (BUYER):
  orders tablosundaki user_id, siparişi veren MÜŞTERİYİ temsil eder.
  Bu alan ASLA mağaza sahibiyle veya CORPORATE rolle eşleştirilmez.
  ❌ YANLIŞ: JOIN stores s ON o.user_id = s.owner_id
  ❌ YANLIŞ: JOIN users u ON o.user_id = u.id WHERE u.role = 'CORPORATE'
  ✅ DOĞRU : orders.user_id = alıcı müşterinin id'si

▸ KURAL 2 — orders DOĞRUDAN stores'a BAĞLI DEĞİLDİR:
  orders tablosunda store_id kolonu YOKTUR.
  ❌ YANLIŞ: JOIN stores s ON o.store_id = s.id   ← bu kolon yoktur
  ❌ YANLIŞ: WHERE o.store_id = :storeId

▸ KURAL 3 — orders → stores ZORUNLU JOIN YOLU:
  Siparişleri mağazalarla ilişkilendirmek için TEK geçerli yol:
  orders → order_items → products → stores
  ✅ ZORUNLU YAPI:
     FROM orders o
     JOIN order_items oi ON o.id = oi.order_id
     JOIN products p     ON oi.product_id = p.id
     JOIN stores s       ON p.store_id = s.id

▸ KURAL 4 — ADMIN rolünde WHERE kısıtlaması YOKTUR:
  Eğer current_user_role = 'ADMIN' ise:
  - WHERE içinde user_id veya store_id filtresi EKLEME.
  - Tüm verilere global erişim vardır; GROUP BY ile özetleyebilirsin.
  ❌ YANLIŞ (Admin için): WHERE o.user_id = 1
  ❌ YANLIŞ (Admin için): WHERE s.owner_id = 1
  ✅ DOĞRU  (Admin için): Filtresiz sorgula, GROUP BY ile grupla.

════════════════════════════════════════════════════════════════

ZAMAN FİLTRELERİ:
- "bu ay"      → WHERE YEAR(tarih_alanı) = YEAR(NOW()) AND MONTH(tarih_alanı) = MONTH(NOW())
- "geçen ay"   → WHERE tarih_alanı >= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m-01')
                   AND tarih_alanı <  DATE_FORMAT(NOW(), '%Y-%m-01')
- "bu hafta"   → WHERE tarih_alanı >= DATE_SUB(NOW(), INTERVAL 7 DAY)
- "son N gün"  → WHERE tarih_alanı >= DATE_SUB(NOW(), INTERVAL N DAY)
- "bu yıl"     → WHERE YEAR(tarih_alanı) = YEAR(NOW())
- Zaman belirtilmemişse filtre ekleme.

VERİTABANI ŞEMASI:
{DB_SCHEMA}
{_build_role_security_block(role, user_id, store_id)}
{fix_ctx}
SORU: {question}
SQL:"""


def sql_generator_node(state: AgentState) -> AgentState:
    role, user_id, store_id = _resolve_role_ids(state)
    prev_err = state.get("error_message", "")

    # intent is used only by analysis/viz nodes for labeling — derive it from question
    state["intent"] = _infer_intent_label(state["question"])

    if not USE_LLM:
        state["error"]        = "llm_unavailable"
        state["error_message"] = "LLM yapılandırılmamış. GROQ_API_KEY eksik."
        return state

    prompt = _build_sql_prompt(state["question"], role, user_id, store_id, prev_err)
    try:
        raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        sql = raw.replace("```sql", "").replace("```", "").strip()
        if not sql.upper().startswith("SELECT"):
            # LLM added explanation before SQL — extract first SELECT block
            match = re.search(r"(SELECT\s.+)", sql, re.IGNORECASE | re.DOTALL)
            sql = match.group(1).strip() if match else sql
        if not sql.endswith(";"):
            sql += ";"
        state["sql_query"]     = sql
        state["error"]         = None
        state["error_message"] = None
        logger.info(f"SQL generated — intent={state['intent']} role={role}")
    except Exception as ex:
        state["error"]         = "generation_failed"
        state["error_message"] = str(ex)

    return state


def _infer_intent_label(question: str) -> str:
    """Lightweight label used only for analysis/viz context — not for routing."""
    q = question.lower()
    if any(w in q for w in ("aylık", "monthly", "her ay", "geçen ay", "bu ay")):
        return "monthly_revenue"
    if any(w in q for w in ("haftalık", "weekly", "bu hafta", "geçen hafta")):
        return "weekly_revenue"
    if any(w in q for w in ("en çok satan", "top ürün", "popüler ürün")):
        return "top_products"
    if any(w in q for w in ("sipariş durum", "durum dağılım", "kaç sipariş", "bekleyen")):
        return "order_status"
    if any(w in q for w in ("kategori", "category")):
        return "category_revenue"
    if any(w in q for w in ("şehir", "city")):
        return "customer_city"
    if any(w in q for w in ("kargo", "shipment", "teslimat")):
        return "shipment_mode"
    if any(w in q for w in ("ödeme", "payment")):
        return "payment_method"
    if any(w in q for w in ("stok", "stock", "envanter")):
        return "stock"
    if any(w in q for w in ("harcama", "spending")):
        return "spending"
    if any(w in q for w in ("puan", "yorum", "rating", "review")):
        return "product_rating"
    if any(w in q for w in ("üyelik", "membership")):
        return "membership"
    return "general"


# ──────────────────────────────────────────────────────────────────────────────
# SQL Executor node
# ──────────────────────────────────────────────────────────────────────────────

_BLOCKED_KEYWORDS = (
    "DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE",
    "ALTER", "CREATE", "EXEC", "GRANT", "REVOKE",
    "UNION",  # AV-03/AV-12: block UNION-based data exfiltration
)

# Sensitive tables whose password/token columns must never be SELECTed (AV-12)
_BANNED_SELECT_PATTERNS = [
    r"\bpassword\b",
    r"\bpassword_hash\b",
    r"\brefresh_token\b",
    r"\bsecret\b",
    r"information_schema",
    r"\bxp_cmdshell\b",
    r"--\s",
    r"/\*.*?\*/",
]


def _strip_sql_comments(sql: str) -> str:
    """Remove SQL line comments and block comments before keyword checks."""
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql


def sql_executor_node(state: AgentState) -> AgentState:
    sql = (state.get("sql_query") or "").strip()
    if not sql:
        state["error"] = "no_sql"
        return state

    # Strip comments before analysis (AV-03: comment-based bypass)
    sql_clean = _strip_sql_comments(sql)
    sql_up    = sql_clean.upper()

    if not sql_up.lstrip().startswith("SELECT"):
        state["error"]        = "security_violation"
        state["final_answer"] = "Güvenlik: Yalnızca SELECT sorguları çalıştırılabilir."
        return state

    for bad in _BLOCKED_KEYWORDS:
        if re.search(r"\b" + bad + r"\b", sql_up):
            state["error"]        = "security_violation"
            state["final_answer"] = f"Güvenlik ihlali: '{bad}' komutu yasak."
            return state

    # AV-12: block queries that attempt to read sensitive columns
    for pat in _BANNED_SELECT_PATTERNS:
        if re.search(pat, sql_clean, re.IGNORECASE | re.DOTALL):
            state["error"]        = "security_violation"
            state["final_answer"] = "Güvenlik: Hassas sütunlar veya yasaklı SQL kalıpları tespit edildi."
            return state

    # AV-03: detect multi-statement injection (semicolon-separated statements)
    statements = [s.strip() for s in sql_clean.split(";") if s.strip()]
    if len(statements) > 1:
        state["error"]        = "security_violation"
        state["final_answer"] = "Güvenlik: Tek seferde yalnızca bir SQL sorgusu çalıştırılabilir."
        return state

    # ── İkinci katman izolasyon — LLM filtreyi atladıysa hard-block ────────────
    role, user_id, store_id = _resolve_role_ids(state)

    if role == "CORPORATE" and store_id:
        if f"{store_id}" not in sql_up and "STORE_ID" not in sql_up:
            logger.warning(f"CORPORATE isolation violation — store_id={store_id} missing. SQL: {sql[:200]}")
            state["error"]        = "security_violation"
            state["final_answer"] = (
                "Güvenlik prensiplerimiz gereği tüm platformun verilerine erişiminiz bulunmuyor.\n\n"
                "Yalnızca kendi mağazanızın verilerine erişebilirsiniz:\n"
                "• \"Mağazamın en çok satan ürünleri\"\n"
                "• \"Mağazamdaki sipariş durum dağılımı\"\n"
                "• \"Mağazamın aylık gelir trendi\""
            )
            return state
        # AV-02: SQL'deki tüm sayısal store_id değerlerini çıkar; kendi ID'si dışında bir değer varsa blokla
        store_id_refs = re.findall(r"store_id\s*=\s*(\d+)", sql_clean, re.IGNORECASE)
        for ref in store_id_refs:
            if int(ref) != int(store_id):
                logger.warning(f"AV-02 cross-store access attempt — own={store_id} requested={ref}. SQL: {sql[:200]}")
                state["error"]        = "security_violation"
                state["final_answer"] = (
                    "Güvenlik: Başka bir mağazanın verilerine erişim yetkiniz yok.\n\n"
                    "Yalnızca kendi mağazanızın verilerini sorgulayabilirsiniz."
                )
                return state

    if role == "INDIVIDUAL" and user_id:
        if f"{user_id}" not in sql_up and "USER_ID" not in sql_up:
            logger.warning(f"INDIVIDUAL isolation violation — user_id={user_id} missing. SQL: {sql[:200]}")
            state["error"]        = "security_violation"
            state["final_answer"] = (
                "Güvenlik prensiplerimiz gereği tüm sitenin verilerine erişiminiz bulunmuyor.\n\n"
                "Yalnızca kendi alışveriş geçmişinize erişebilirsiniz:\n"
                "• \"Benim en çok satın aldığım ürünler\"\n"
                "• \"Kendi sipariş durum dağılımım\"\n"
                "• \"Aylık harcama trendiim\""
            )
            return state

    # ── KURAL 3 ikinci katman — LLM yasak kolonu SELECT ettiyse hard-block ────
    if role == "INDIVIDUAL":
        _BANNED_COLS = ("P.STOCK", "P.SKU", "P.REVIEW_COUNT", "PRODUCTS.STOCK",
                        "PRODUCTS.SKU", "PRODUCTS.REVIEW_COUNT")
        for col in _BANNED_COLS:
            if col in sql_up:
                logger.warning(f"INDIVIDUAL column leak — banned col '{col}' in SQL: {sql[:200]}")
                state["error"]        = "security_violation"
                state["final_answer"] = (
                    "Sadece kendi sipariş detaylarınıza ve ödeme geçmişinize erişebilirsiniz.\n\n"
                    "Mağazaya ait stok / fiyat listesi / satış istatistiklerini "
                    "görüntüleme yetkiniz yoktur."
                )
                return state

    if not DB_OK or engine is None:
        state["error"]         = "db_unavailable"
        state["error_message"] = "Veritabanına bağlanılamıyor."
        state["final_answer"]  = (
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
    role, user_id, store_id = _resolve_role_ids(state)
    return f"""Sen bir MySQL hata uzmanısın. Aşağıdaki hatalı SQL sorgusunu düzelt ve sadece ham SQL döndür.

VERİTABANI ŞEMASI:
{DB_SCHEMA}
{_build_role_security_block(role, user_id, store_id)}
ZAMAN FİLTRELERİ HATIRLATMA:
- "geçen ay" → tarih >= DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m-01') AND tarih < DATE_FORMAT(NOW(), '%Y-%m-01')
- "bu ay"    → YEAR(tarih) = YEAR(NOW()) AND MONTH(tarih) = MONTH(NOW())
- Gelir için SUM(oi.unit_price * oi.quantity * 1.20) kullan (KDV %20 dahil).

ZORUNLU JOIN KURALLARI (hata düzeltirken bunlara özellikle dikkat et):
- orders.user_id = alıcı müşteri id'si — ASLA mağaza sahibiyle eşleştirme.
- orders tablosunda store_id kolonu YOKTUR — direkt JOIN YAPMA.
- orders → stores için TEK yol: orders → order_items → products → stores
- ADMIN sorgularında WHERE'e user_id veya store_id filtresi EKLEME.

KULLANICI SORUSU: {state["question"]}
HATALI SQL:
{state.get("sql_query", "")}
HATA MESAJI: {state.get("error_message", "")}

DÜZELTİLMİŞ SQL:"""


def error_handler_node(state: AgentState) -> AgentState:
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    if state["iteration_count"] >= 3:
        state["final_answer"] = "Sorgu 3 denemeden sonra çalışmadı. Soruyu farklı şekilde deneyin."
        state["error"] = "max_retries"
        return state

    if state.get("error") in ("db_unavailable", "llm_unavailable"):
        return state

    if not USE_LLM:
        state["final_answer"] = "LLM yapılandırılmamış, sorgu düzeltilemedi."
        state["error"] = "fix_failed"
        return state

    try:
        prompt = _build_error_prompt(state)
        fixed  = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        fixed  = fixed.replace("```sql", "").replace("```", "").strip()
        if not fixed.endswith(";"):
            fixed += ";"
        state["sql_query"]     = fixed
        state["error"]         = None
        state["error_message"] = None
    except Exception as ex:
        state["error"]         = "fix_failed"
        state["error_message"] = str(ex)

    return state


# ──────────────────────────────────────────────────────────────────────────────
# ④ Analysis Agent — Data Analyst
# ──────────────────────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM = """
Sen yardımsever bir iş zekası analistsin. Veritabanından dönen JSON sonucunu
iş kullanıcısına anlaşılır, içgörü odaklı bir dille açıkla.
2-4 cümle, temel bulgular ve dikkat çekici noktalar.
Türkçe yanıt ver. Markdown bold kullanabilirsin.

KRİTİK ROL KURALI:
- ROL = INDIVIDUAL ise: bu kullanıcı bir ALICI müşteridir. Veriler onun KENDİ HARCAMASINI gösterir.
  "Gelir", "kazanç", "ciro" gibi ifadeler ASLA kullanma. Yalnızca "harcama", "ödeme", "alışveriş tutarı" kullan.
- ROL = CORPORATE ise: bu bir mağaza sahibidir. Veriler mağaza GELİRİNİ gösterir.
- ROL = ADMIN ise: tüm platform verisi gösterilir, gelir/ciro ifadeleri uygundur.
"""


def analysis_node(state: AgentState) -> AgentState:
    result = state.get("query_result", "[]")
    if not result or result == "[]":
        state["final_answer"] = "Bu sorgu için veritabanında veri bulunamadı."
        return state

    try:
        rows = json.loads(result)

        if USE_LLM:
            try:
                prompt = (
                    f"{ANALYSIS_SYSTEM}\n\n"
                    f"KULLANICI SORUSU: {state['question']}\n"
                    f"ROL: {state.get('role', 'INDIVIDUAL')}\n"
                    f"VERİ ({len(rows)} satır):\n{result[:3000]}\n\n"
                    "ANALİZ:"
                )
                ans = llm.invoke([HumanMessage(content=prompt)]).content.strip()
                state["final_answer"] = ans
                return state
            except Exception:
                pass

        state["final_answer"] = f"Analiz tamamlandı. {len(rows)} kayıt bulundu."
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
        rows = json.loads(state.get("query_result") or "[]")

        if USE_LLM:
            try:
                prompt = (
                    f"{VIZ_SYSTEM}\n\n"
                    f"SORU: {state['question']}\n"
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
                pass

        state["visualization_code"] = build_chart(rows, state["question"])
    except Exception as ex:
        logger.warning(f"Viz error: {ex}")
        state["visualization_code"] = None

    return state