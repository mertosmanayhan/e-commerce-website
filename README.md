# DataPulse E-Commerce Platform

A full-stack e-commerce platform with AI-powered analytics, built with Spring Boot, Angular, and FastAPI.

## Features

- **Multi-role system** — Individual shoppers, Corporate store owners, and Admin users
- **E-Commerce core** — Product catalog, shopping cart, wishlist, checkout, order tracking
- **Stripe payments** — Real card payments via Stripe Elements (test mode ready)
- **AI Chatbot** — Natural language to SQL analytics powered by LangGraph + GPT-4o-mini
- **Analytics dashboards** — Role-specific dashboards with charts and insights
- **Admin panel** — User management, store management, system analytics, audit logs
- **Store management** — Corporate users can manage their own stores and products
- **Shipment tracking** — End-to-end shipment monitoring and analytics
- **Swagger UI** — Full REST API documentation at `/swagger-ui.html`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Spring Boot 3.4.4 (Java 21), Spring Security, JPA/Hibernate |
| Frontend | Angular 21, TypeScript, Chart.js |
| Database | MySQL 8 (PostgreSQL profile also supported) |
| Authentication | JWT (JJWT 0.12.6) |
| Payments | Stripe Java SDK 26.3.0 + Stripe.js v3 |
| AI Chatbot | FastAPI, LangGraph, OpenAI GPT-4o-mini, SQLAlchemy |
| ETL | Python, pandas, SQLAlchemy |
| API Docs | SpringDoc OpenAPI (Swagger UI) |

## Project Structure

```
AdvancedProje/
├── backend/               # Spring Boot REST API (port 8080)
│   └── src/main/java/com/datapulse/ecommerce/
│       ├── controller/    # 13 REST controllers
│       ├── service/       # Business logic layer
│       ├── entity/        # JPA entities
│       ├── repository/    # Data access layer
│       ├── dto/           # Request/Response DTOs
│       └── security/      # JWT & Spring Security config
│
├── frontend/              # Angular SPA (port 4200)
│   └── src/app/
│       ├── checkout/      # Stripe payment checkout
│       ├── dashboard/     # Corporate/Admin dashboards
│       ├── admin/         # Admin management panel
│       ├── ai-assistant/  # Text-to-SQL chatbot UI
│       └── ...            # Product, cart, orders, etc.
│
├── chatbot-service/       # FastAPI AI service (port 8000)
│   └── main.py            # LangGraph multi-agent pipeline
│
└── kaggle_etl/            # Data ingestion pipeline
    └── etl_pipeline.py    # Loads Kaggle datasets into MySQL
```

## Getting Started

### Prerequisites

- Java 21+
- Node.js 18+ / npm
- Python 3.9+
- MySQL 8.0+

### 1. Database

MySQL will auto-create the database on first run (`createDatabaseIfNotExist=true`). Copy the config template and fill in your credentials:

```bash
cp backend/src/main/resources/application.yml.example \
   backend/src/main/resources/application.yml
```

Edit `application.yml` and set:
- `spring.datasource.username` / `password` — your MySQL credentials
- `app.jwt.secret` — any Base64-encoded secret string
- `stripe.secret-key` / `publishable-key` — your Stripe test keys (optional, falls back to simulation mode)
- `chatbot.service.url` — set to `http://localhost:8000` if running the chatbot

### 2. Backend

```bash
cd backend
mvn spring-boot:run
```

API runs at `http://localhost:8080`  
Swagger UI: `http://localhost:8080/swagger-ui.html`

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

App runs at `http://localhost:4200`

### 4. AI Chatbot (optional)

```bash
cd chatbot-service
pip install -r requirements.txt
```

Create a `.env` file:
```
OPENAI_API_KEY=your_openai_key   # leave blank for mock/demo mode
DATABASE_URL=mysql+pymysql://root:password@localhost/datapulse_ecommerce
PORT=8000
```

```bash
python main.py
```

If `OPENAI_API_KEY` is not set, the chatbot runs in **mock mode** and returns demo responses.

### 5. ETL Pipeline (optional)

Loads sample datasets from Kaggle into the database:

```bash
cd kaggle_etl
pip install -r requirements.txt
python etl_pipeline.py
```

## User Roles

| Role | Access |
|------|--------|
| `INDIVIDUAL` | Browse, buy, wishlist, reviews, personal analytics |
| `CORPORATE` | All individual features + store management, store analytics |
| `ADMIN` | Full access — user management, all stores, system analytics, audit logs |

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/register` | Register new user |
| `POST /api/auth/login` | Login, returns JWT |
| `GET /api/products` | Browse products (with search & filter) |
| `GET/POST /api/cart` | Cart management |
| `POST /api/orders` | Place order |
| `POST /api/payment/create-intent` | Create Stripe PaymentIntent |
| `POST /api/chat/ask` | AI chatbot query |
| `GET /api/analytics/dashboard` | Role-based analytics data |
| `GET /api/stores` | Store listing |

Full API documentation available at `http://localhost:8080/swagger-ui.html` when the backend is running.

## Payment Testing

The app uses **Stripe test mode**. Use these test card numbers:

| Card | Number |
|------|--------|
| Visa (success) | `4242 4242 4242 4242` |
| Declined | `4000 0000 0000 0002` |
| 3D Secure | `4000 0025 0000 3155` |

Use any future expiry date and any 3-digit CVC.

If no Stripe keys are configured, the app automatically falls back to **simulation mode** — orders are placed without real card processing.

## Configuration Reference

See `backend/src/main/resources/application.yml.example` for all configurable properties.
