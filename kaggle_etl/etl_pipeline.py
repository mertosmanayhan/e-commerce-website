"""
DataPulse E-Commerce — Kaggle ETL Pipeline (6 Dataset)
=======================================================
Dataset Kullanımı:
  1. ecommerce_customer_behavior.csv  → users + customer_profiles
  2. online_retail.csv                → products + orders + order_items
  3. shipping_data.csv                → shipments (city, district, mode, rating)
  4. amazon_sales.csv                 → products (image_url, rating, category)
  5. pakistan_ecommerce.csv           → orders (fulfilment, payment_method, category)
  6. amazon_reviews.csv               → reviews (star_rating, helpful_votes, review_body)

Mevcut seed verisi KORUNUR. Script idempotent çalışır.
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os, random
from datetime import datetime, timedelta

# ── Bağlantı ──────────────────────────────────────────────────────────────────
DB_URI  = "mysql+pymysql://root:Ayhan2929.@localhost:3306/datapulse_ecommerce"
engine  = create_engine(DB_URI)
RAW_DIR = os.path.join(os.path.dirname(__file__), "raw_data")

BCRYPT_HASH = "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy"  # 123456

def rand_date(days_back=365):
    return datetime.now() - timedelta(days=random.randint(0, days_back))

def log(msg): print(f"  {msg}", flush=True)

def csv(name, **kwargs):
    p = os.path.join(RAW_DIR, name)
    if not os.path.exists(p):
        return None
    try:
        df = pd.read_csv(p, encoding='utf-8', on_bad_lines='skip', **kwargs)
    except Exception:
        df = pd.read_csv(p, encoding='ISO-8859-1', on_bad_lines='skip', **kwargs)
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    return df

# ── ADIM 0: Mevcut durumu oku ─────────────────────────────────────────────────
def load_existing():
    with engine.connect() as c:
        emails    = set(r[0] for r in c.execute(text("SELECT email FROM users")))
        skus      = set(r[0] for r in c.execute(text("SELECT sku FROM products")))
        ord_nums  = set(r[0] for r in c.execute(text("SELECT order_number FROM orders")))
        rev_ids   = set(r[0] for r in c.execute(text("SELECT id FROM reviews")))
        u_count   = c.execute(text("SELECT COUNT(*) FROM users")).scalar()
        p_count   = c.execute(text("SELECT COUNT(*) FROM products")).scalar()
        o_count   = c.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        cats      = {r[1]: r[0] for r in c.execute(text("SELECT id,name FROM categories")).fetchall()}
        stores    = [r[0] for r in c.execute(text("SELECT id FROM stores")).fetchall()]
        ind_users = [r[0] for r in c.execute(text("SELECT id FROM users WHERE role='INDIVIDUAL'")).fetchall()]
        all_prods = [r[0] for r in c.execute(text("SELECT id FROM products")).fetchall()]
    return emails, skus, ord_nums, rev_ids, u_count, p_count, o_count, cats, stores, ind_users, all_prods

# ── ADIM 1: Kullanıcılar + CustomerProfiles ───────────────────────────────────
def etl_users(existing_emails):
    print("\n[1/6] Kullanıcılar yükleniyor (ecommerce_customer_behavior.csv)...")
    df = csv("ecommerce_customer_behavior.csv")
    if df is None:
        log("CSV bulunamadı, atlanıyor.")
        return

    id_col  = "Customer_ID"
    age_col = "Age"
    city_col = "City"
    gen_col  = "Gender"
    mem_col  = "Membership_Type"
    spend_col = "Total_Spend"
    items_col = "Items_Purchased"
    rating_col = "Average_Rating"
    disc_col   = "Discount_Applied"
    sat_col    = "Satisfaction_Level"

    df.dropna(subset=[id_col], inplace=True)
    df[age_col]  = pd.to_numeric(df[age_col],  errors='coerce').fillna(30).astype(int)
    df[city_col] = df[city_col].fillna("Istanbul")

    gender_map = {"Male": "MALE", "Female": "FEMALE"}
    users, profiles = [], []

    for _, row in df.iterrows():
        cid   = int(row[id_col])
        email = f"customer{cid}@shop.com"
        if email in existing_emails:
            continue
        users.append({
            "full_name":  f"Musteri {cid}",
            "email":      email,
            "password":   BCRYPT_HASH,
            "role":       "INDIVIDUAL",
            "gender":     gender_map.get(str(row.get(gen_col, "")), None),
            "age":        int(row[age_col]),
            "city":       str(row[city_col])[:100],
            "country":    "Turkey",
            "enabled":    True,
            "created_at": rand_date(730),
        })
        profiles.append({
            "email":            email,
            "membership_type":  str(row.get(mem_col, "Standard"))[:50],
            "total_spend":      float(row.get(spend_col, 0) or 0),
            "items_purchased":  int(row.get(items_col, 0) or 0),
            "avg_rating":       float(row.get(rating_col, 0) or 0),
            "discount_applied": bool(row.get(disc_col, False)),
            "satisfaction_level": str(row.get(sat_col, ""))[:50],
        })

    if users:
        pd.DataFrame(users).to_sql("users", con=engine, if_exists="append", index=False)
        log(f"{len(users)} kullanıcı eklendi.")

        # customer_profiles — user_id gerekiyor
        with engine.connect() as c:
            email_to_id = {r[1]: r[0] for r in c.execute(
                text("SELECT id, email FROM users WHERE role='INDIVIDUAL'")).fetchall()}

        prof_rows = []
        for p in profiles:
            uid = email_to_id.get(p["email"])
            if uid:
                prof_rows.append({
                    "user_id":          uid,
                    "membership_type":  p["membership_type"],
                    "total_spend":      p["total_spend"],
                    "items_purchased":  p["items_purchased"],
                    "avg_rating":       p["avg_rating"],
                    "discount_applied": p["discount_applied"],
                    "satisfaction_level": p["satisfaction_level"],
                })
        if prof_rows:
            pd.DataFrame(prof_rows).to_sql("customer_profiles", con=engine, if_exists="append", index=False)
            log(f"{len(prof_rows)} müşteri profili eklendi.")
    else:
        log("Eklenecek yeni kullanıcı yok.")

# ── ADIM 2: Ürünler (online_retail.csv) ───────────────────────────────────────
def etl_products_retail(existing_skus, cats, stores):
    print("\n[2/6] Ürünler yükleniyor (online_retail.csv)...")
    df = csv("online_retail.csv")
    if df is None:
        log("CSV bulunamadı, atlanıyor.")
        return

    price_col = "Price" if "Price" in df.columns else "UnitPrice"
    df.dropna(subset=["Description", price_col], inplace=True)
    df = df[pd.to_numeric(df[price_col], errors='coerce').fillna(0) > 0]
    df = df[pd.to_numeric(df["Quantity"], errors='coerce').fillna(0) > 0]
    df["StockCode"] = df["StockCode"].astype(str).str.strip()

    prod_df = df[["StockCode", "Description", price_col]].drop_duplicates("StockCode")
    prod_df = prod_df[~prod_df["StockCode"].isin(existing_skus)].head(200)

    store_id = stores[0] if stores else None
    cat_list = list(cats.values())
    products = []
    for _, row in prod_df.iterrows():
        sku   = str(row["StockCode"])[:50]
        price = round(float(row[price_col]) * 30, 2)
        if price < 10: price = round(random.uniform(29, 199), 2)
        products.append({
            "name":         str(row["Description"])[:200],
            "description":  str(row["Description"]),
            "sku":          sku,
            "price":        price,
            "stock":        random.randint(5, 150),
            "category_id":  random.choice(cat_list) if cat_list else None,
            "store_id":     store_id,
            "image_url":    f"https://picsum.photos/seed/{sku}/400/400",
            "rating":       round(random.uniform(3.5, 5.0), 1),
            "review_count": random.randint(0, 80),
            "created_at":   rand_date(400),
        })
        existing_skus.add(sku)

    if products:
        pd.DataFrame(products).to_sql("products", con=engine, if_exists="append", index=False)
        log(f"{len(products)} ürün eklendi (online_retail).")
    else:
        log("Eklenecek yeni ürün yok.")

# ── ADIM 3: Ürünler (amazon_sales.csv) ────────────────────────────────────────
def etl_products_amazon(existing_skus, cats, stores):
    print("\n[3/6] Ürünler zenginleştiriliyor (amazon_sales.csv)...")
    df = csv("amazon_sales.csv")
    if df is None:
        log("CSV bulunamadı, atlanıyor.")
        return

    df.dropna(subset=["product_id", "product_name"], inplace=True)
    df = df[~df["product_id"].isin(existing_skus)].head(100)

    store_id = stores[0] if stores else None
    cat_list = list(cats.values())

    def clean_price(val):
        try:
            return float(str(val).replace("₹","").replace(",","").strip())
        except:
            return None

    def clean_rating(val):
        try:
            return float(str(val).strip())
        except:
            return None

    # Kategori mapping: amazon_sales category → mevcut kategori
    cat_map = {
        "Computers": "Elektronik", "Electronics": "Elektronik",
        "Home": "Ev & Yaşam", "Kitchen": "Ev & Yaşam",
        "Clothing": "Giyim & Moda", "Fashion": "Giyim & Moda",
        "Books": "Kitap", "Sports": "Spor",
        "Beauty": "Kozmetik", "Health": "Kozmetik",
        "Toys": "Oyuncak", "Food": "Gıda",
    }

    products = []
    for _, row in df.iterrows():
        sku = str(row["product_id"])[:50]
        if sku in existing_skus: continue

        disc_p = clean_price(row.get("discounted_price"))
        act_p  = clean_price(row.get("actual_price"))
        price  = disc_p or act_p
        if price is None or price <= 0: price = round(random.uniform(50, 500), 2)
        else: price = round(price * 0.38, 2)  # INR → TRY approx

        rating_str = str(row.get("rating","")).strip()
        rating = clean_rating(rating_str) if rating_str not in ["","nan"] else None
        if rating is None or rating > 5: rating = round(random.uniform(3.5, 5.0), 1)

        # Kategori belirle
        raw_cat  = str(row.get("category",""))
        cat_key  = next((k for k in cat_map if k.lower() in raw_cat.lower()), None)
        cat_name = cat_map.get(cat_key, "Elektronik")
        cat_id   = cats.get(cat_name) or (random.choice(cat_list) if cat_list else None)

        img = str(row.get("img_link","")).strip()
        if not img or img == "nan": img = f"https://picsum.photos/seed/{sku}/400/400"

        count_str = str(row.get("rating_count","0")).replace(",","").strip()
        try: review_count = int(float(count_str))
        except: review_count = 0

        products.append({
            "name":         str(row["product_name"])[:200],
            "description":  str(row.get("about_product",""))[:1000] if str(row.get("about_product","")) != "nan" else str(row["product_name"])[:200],
            "sku":          sku,
            "price":        price,
            "stock":        random.randint(5, 100),
            "category_id":  cat_id,
            "store_id":     store_id,
            "image_url":    img,
            "rating":       rating,
            "review_count": min(review_count, 9999),
            "created_at":   rand_date(300),
        })
        existing_skus.add(sku)

    if products:
        pd.DataFrame(products).to_sql("products", con=engine, if_exists="append", index=False)
        log(f"{len(products)} ürün eklendi (amazon_sales).")
    else:
        log("Eklenecek yeni amazon ürünü yok.")

# ── ADIM 4: Siparişler (pakistan_ecommerce.csv) ───────────────────────────────
def etl_orders_pakistan(individual_user_ids, all_product_ids, existing_ord_nums):
    print("\n[4/6] Siparişler yükleniyor (pakistan_ecommerce.csv)...")
    df = csv("pakistan_ecommerce.csv")
    if df is None or not individual_user_ids or not all_product_ids:
        log("CSV bulunamadı veya kullanıcı/ürün yok, atlanıyor.")
        return

    df.dropna(subset=["increment_id"], inplace=True)
    df["increment_id"] = df["increment_id"].astype(str).str.strip()

    status_map = {
        "complete":   "DELIVERED",
        "canceled":   "CANCELLED",
        "refund":     "CANCELLED",
        "order_refunded": "CANCELLED",
        "paid":       "SHIPPED",
        "processing": "PENDING",
        "pending":    "PENDING",
        "pending_paypal": "PENDING",
    }
    ship_map = {"PENDING": "PROCESSING", "SHIPPED": "IN_TRANSIT",
                "DELIVERED": "DELIVERED", "CANCELLED": "PROCESSING"}
    payment_map = {
        "cod":       "CASH_ON_DELIVERY",
        "easypay":   "CREDIT_CARD",
        "jazzcash":  "CREDIT_CARD",
        "payaxis":   "DEBIT_CARD",
        "ubl_wallet":"BANK_TRANSFER",
    }

    orders, items, ships = [], [], []
    limit = 200

    for _, row in df.head(limit * 3).iterrows():
        num = f"ORD-PAK-{row['increment_id']}"
        if num in existing_ord_nums: continue

        raw_status = str(row.get("status","")).strip().lower()
        status     = status_map.get(raw_status, "PENDING")
        pay_raw    = str(row.get("payment_method","cod")).strip().lower()
        payment    = payment_map.get(pay_raw, "CASH_ON_DELIVERY")

        try:
            order_date = pd.to_datetime(row.get("created_at"), dayfirst=True)
            if pd.isnull(order_date): order_date = rand_date(400)
            else: order_date = order_date.to_pydatetime()
        except:
            order_date = rand_date(400)

        try:
            total = float(str(row.get("grand_total", 0)).replace(",","").strip() or 0)
            if total <= 0: total = round(random.uniform(100, 5000), 2)
        except:
            total = round(random.uniform(100, 5000), 2)

        uid   = random.choice(individual_user_ids)
        prods = random.sample(all_product_ids, random.randint(1, 3))

        orders.append({
            "order_number":   num,
            "user_id":        uid,
            "status":         status,
            "total_amount":   round(total * 0.13, 2),  # PKR → TRY approx
            "payment_method": payment,
            "fulfilment":     "Merchant",
            "sales_channel":  "Online",
            "order_date":     order_date,
        })
        for pid in prods:
            qty = int(row.get("qty_ordered", 1) or 1)
            items.append({"order_number": num, "product_id": pid,
                          "quantity": max(1, qty), "unit_price": round(total * 0.13 / len(prods), 2)})
        ships.append({"order_number": num, "status": status})
        existing_ord_nums.add(num)

        if len(orders) >= limit: break

    _insert_orders_items_ships(orders, items, ships, ship_map, "pakistan")

# ── ADIM 5: Siparişler (online_retail.csv) ────────────────────────────────────
def etl_orders_retail(individual_user_ids, all_product_ids, existing_ord_nums):
    print("\n[5/6] Siparişler yükleniyor (online_retail.csv)...")
    df = csv("online_retail.csv")
    if df is None or not individual_user_ids or not all_product_ids:
        log("CSV bulunamadı veya kullanıcı/ürün yok, atlanıyor.")
        return

    price_col = "Price" if "Price" in df.columns else "UnitPrice"
    inv_col   = "Invoice" if "Invoice" in df.columns else "InvoiceNo"
    cust_col  = "Customer_ID" if "Customer_ID" in df.columns else "CustomerID"

    df.dropna(subset=[inv_col, cust_col], inplace=True)
    df = df[pd.to_numeric(df["Quantity"],  errors='coerce').fillna(0) > 0]
    df = df[pd.to_numeric(df[price_col], errors='coerce').fillna(0) > 0]
    df[inv_col] = df[inv_col].astype(str)
    df = df[~df[inv_col].str.startswith("C")]

    ship_map = {"PENDING": "PROCESSING", "SHIPPED": "IN_TRANSIT",
                "DELIVERED": "DELIVERED", "CANCELLED": "PROCESSING"}
    statuses = ["PENDING","SHIPPED","DELIVERED","DELIVERED","DELIVERED","CANCELLED"]
    payments = ["CREDIT_CARD","DEBIT_CARD","BANK_TRANSFER","CASH_ON_DELIVERY"]

    invoices = [i for i in df[inv_col].unique() if f"ORD-KGL-{i}" not in existing_ord_nums][:200]
    orders, items, ships = [], [], []

    for inv in invoices:
        num   = f"ORD-KGL-{inv}"
        group = df[df[inv_col] == inv]
        uid   = random.choice(individual_user_ids)
        status = random.choice(statuses)

        try:
            date_val = pd.to_datetime(group.iloc[0].get("InvoiceDate"))
            order_date = date_val.to_pydatetime() if not pd.isnull(date_val) else rand_date(365)
        except:
            order_date = rand_date(365)

        prods = random.sample(all_product_ids, min(len(group), 3))
        total = sum(float(group.iloc[i][price_col]) * int(group.iloc[i]["Quantity"])
                    for i in range(min(len(group), 3))) * 30  # GBP→TRY

        orders.append({
            "order_number":   num,
            "user_id":        uid,
            "status":         status,
            "total_amount":   round(total, 2),
            "payment_method": random.choice(payments),
            "fulfilment":     "Amazon",
            "sales_channel":  "Amazon.co.uk",
            "order_date":     order_date,
        })
        for pid in prods:
            items.append({"order_number": num, "product_id": pid,
                          "quantity": random.randint(1,3), "unit_price": round(total/len(prods), 2)})
        ships.append({"order_number": num, "status": status})
        existing_ord_nums.add(num)

    _insert_orders_items_ships(orders, items, ships, ship_map, "online_retail",
                               shipping_df=csv("shipping_data.csv"))

# ── Ortak sipariş+kargo insert ────────────────────────────────────────────────
def _insert_orders_items_ships(orders, items, ships, ship_map, label, shipping_df=None):
    if not orders:
        log(f"Eklenecek yeni {label} siparişi yok.")
        return

    pd.DataFrame(orders).to_sql("orders", con=engine, if_exists="append", index=False)
    log(f"{len(orders)} sipariş eklendi ({label}).")

    with engine.connect() as c:
        num_to_id = {r[1]: r[0] for r in c.execute(text("SELECT id, order_number FROM orders")).fetchall()}
        existing_ship_orders = set(r[0] for r in c.execute(text("SELECT order_id FROM shipments")).fetchall())

    items_flat = [{"order_id": num_to_id[it["order_number"]], "product_id": it["product_id"],
                   "quantity": it["quantity"], "unit_price": it["unit_price"]}
                  for it in items if it["order_number"] in num_to_id]
    if items_flat:
        pd.DataFrame(items_flat).to_sql("order_items", con=engine, if_exists="append", index=False)
        log(f"{len(items_flat)} sipariş kalemi eklendi.")

    # Shipping enrichment from shipping_data.csv
    ship_rows = None
    if shipping_df is not None and not shipping_df.empty:
        ship_rows = shipping_df.sample(frac=1).reset_index(drop=True)

    ship_flat = []
    for i, sh in enumerate(ships):
        oid = num_to_id.get(sh["order_number"])
        if not oid or oid in existing_ship_orders: continue

        s_status  = ship_map.get(sh["status"], "PROCESSING")
        shipped   = rand_date(300) if sh["status"] in ("SHIPPED","DELIVERED") else None
        delivery  = rand_date(200) if sh["status"] == "DELIVERED" else None

        row = {}
        if ship_rows is not None and i < len(ship_rows):
            row = ship_rows.iloc[i % len(ship_rows)].to_dict()

        ship_flat.append({
            "order_id":             oid,
            "tracking_number":      f"TRK{oid:08d}",
            "warehouse_block":      random.choice(["A","B","C","D","F"]),
            "mode_of_shipment":     row.get("courier_delivery") or random.choice(["Ship","Flight","Road"]),
            "status":               s_status,
            "customer_care_calls":  random.randint(0, 5),
            "shipped_date":         shipped,
            "delivery_date":        delivery,
            "city":                 str(row.get("city",""))[:100] if row.get("city") else None,
            "district":             str(row.get("district",""))[:100] if row.get("district") else None,
            "type_of_delivery":     str(row.get("type_of_delivery",""))[:50] if row.get("type_of_delivery") else None,
            "estimated_delivery_days": int(row["estimated_delivery_time_days"]) if row.get("estimated_delivery_time_days") else None,
            "customer_rating":      int(row["product_rating"]) if row.get("product_rating") else None,
        })
        existing_ship_orders.add(oid)

    if ship_flat:
        df_ship = pd.DataFrame(ship_flat).drop_duplicates(subset=["order_id"])
        df_ship.to_sql("shipments", con=engine, if_exists="append", index=False)
        log(f"{len(df_ship)} kargo kaydı eklendi.")

# ── ADIM 6: Reviews (amazon_reviews.csv) ─────────────────────────────────────
def etl_reviews(individual_user_ids, all_product_ids):
    print("\n[6/6] Değerlendirmeler yükleniyor (amazon_reviews.csv)...")
    df = csv("amazon_reviews.csv", sep='\t')
    if df is None:
        # Tab-separated dene
        p = os.path.join(RAW_DIR, "amazon_reviews.csv")
        if os.path.exists(p):
            try:
                df = pd.read_csv(p, sep='\t', encoding='utf-8', on_bad_lines='skip')
                df.columns = [c.strip().replace(" ", "_") for c in df.columns]
            except:
                log("amazon_reviews.csv okunamadı, atlanıyor.")
                return
        else:
            log("CSV bulunamadı, atlanıyor.")
            return

    if df is None or not individual_user_ids or not all_product_ids:
        log("Kullanıcı veya ürün yok, atlanıyor.")
        return

    # Gerekli sütunlar
    star_col    = "star_rating"
    body_col    = "review_body"
    helpful_col = "helpful_votes"
    total_col   = "total_votes"

    df.dropna(subset=[star_col], inplace=True)
    df[star_col] = pd.to_numeric(df[star_col], errors='coerce')
    df.dropna(subset=[star_col], inplace=True)
    df = df[df[star_col].between(1, 5)]

    # Mevcut review sayısını kontrol et
    with engine.connect() as c:
        existing_count = c.execute(text("SELECT COUNT(*) FROM reviews")).scalar()
        existing_pairs = set((r[0], r[1]) for r in c.execute(
            text("SELECT user_id, product_id FROM reviews")).fetchall())

    if existing_count >= 500:
        log(f"Zaten {existing_count} review mevcut, atlanıyor.")
        return

    target = min(300, len(df))
    df_sample = df.sample(n=min(target, len(df)), random_state=42)

    reviews = []
    for _, row in df_sample.iterrows():
        uid = random.choice(individual_user_ids)
        pid = random.choice(all_product_ids)
        if (uid, pid) in existing_pairs: continue

        body = str(row.get(body_col, "")).strip()
        if body in ("", "nan"): body = None

        try: helpful = int(float(str(row.get(helpful_col, 0)).replace(",","")))
        except: helpful = 0
        try: total = int(float(str(row.get(total_col, 0)).replace(",","")))
        except: total = 0

        reviews.append({
            "user_id":      uid,
            "product_id":   pid,
            "star_rating":  int(row[star_col]),
            "review_text":  body[:2000] if body else None,
            "helpful_votes": helpful,
            "total_votes":   total,
            "created_at":   rand_date(500),
        })
        existing_pairs.add((uid, pid))

    if reviews:
        pd.DataFrame(reviews).to_sql("reviews", con=engine, if_exists="append", index=False)
        log(f"{len(reviews)} değerlendirme eklendi.")
    else:
        log("Eklenecek yeni değerlendirme yok.")

# ── ANA FONKSİYON ─────────────────────────────────────────────────────────────
def run_etl():
    print("=" * 60)
    print("  DataPulse ETL Pipeline  —  6 Dataset  —  Başlıyor...")
    print("=" * 60)

    (emails, skus, ord_nums, _,
     u_count, p_count, o_count,
     cats, stores, ind_users, all_prods) = load_existing()

    print(f"\n  Mevcut: {u_count} kullanıcı | {p_count} ürün | {o_count} sipariş")

    # 1. Kullanıcılar + Profiller
    etl_users(emails)

    # 2 & 3. Ürünler
    etl_products_retail(skus, cats, stores)
    etl_products_amazon(skus, cats, stores)

    # Güncel ürün ve kullanıcı listelerini al
    with engine.connect() as c:
        ind_users  = [r[0] for r in c.execute(text("SELECT id FROM users WHERE role='INDIVIDUAL'")).fetchall()]
        all_prods  = [r[0] for r in c.execute(text("SELECT id FROM products")).fetchall()]

    # 4 & 5. Siparişler
    etl_orders_pakistan(ind_users, all_prods, ord_nums)
    etl_orders_retail(ind_users, all_prods, ord_nums)

    # 6. Reviews
    with engine.connect() as c:
        ind_users = [r[0] for r in c.execute(text("SELECT id FROM users WHERE role='INDIVIDUAL'")).fetchall()]
        all_prods = [r[0] for r in c.execute(text("SELECT id FROM products")).fetchall()]
    etl_reviews(ind_users, all_prods)

    # Sonuç
    with engine.connect() as c:
        u = c.execute(text("SELECT COUNT(*) FROM users")).scalar()
        p = c.execute(text("SELECT COUNT(*) FROM products")).scalar()
        o = c.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        s = c.execute(text("SELECT COUNT(*) FROM shipments")).scalar()
        r = c.execute(text("SELECT COUNT(*) FROM reviews")).scalar()
        cp = c.execute(text("SELECT COUNT(*) FROM customer_profiles")).scalar()

    print("\n" + "=" * 60)
    print("  ETL TAMAMLANDI")
    print(f"  Kullanıcılar    : {u}")
    print(f"  Müşteri Profili : {cp}")
    print(f"  Ürünler         : {p}")
    print(f"  Siparişler      : {o}")
    print(f"  Kargolar        : {s}")
    print(f"  Değerlendirmeler: {r}")
    print("=" * 60)

if __name__ == "__main__":
    run_etl()
