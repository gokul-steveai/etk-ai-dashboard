# ETK AI Dashboard Backend

A robust, production-ready FastAPI backend service for the ETK AI Dashboard platform. Provides comprehensive REST APIs for user authentication, subscription management, billing operations, and user profile management with seamless Stripe integration.

## 🎯 Project Overview

ETK Backend is an enterprise-grade async API built with FastAPI and SQLAlchemy, serving the ETK AI Dashboard frontend. The platform enables users to subscribe to data analysis plans and manage their analytics queries across multiple countries.

**Key Capabilities:**
- Multi-tier subscription plans (Free, Basic, Individual, Researcher, Enterprise)
- Stripe-powered payment processing with webhook support
- OAuth2 authentication (Google & LinkedIn)
- Email-based OTP password reset
- Base64 image upload for user profiles
- Complete billing dashboard with invoice history
- Async database operations for optimal performance

## 📊 Tech Stack

| Component          | Technology                 |
|-------------------|----------------------------|
| Backend Framework | FastAPI                    |
| ASGI Server       | Uvicorn                    |
| ORM               | SQLAlchemy                 |
| Database Drivers  | aiomysql, psycopg2         |
| Authentication    | JWT (`python-jose`)        |
| Password Hashing  | bcrypt                     |
| OAuth Providers   | Google OAuth (`google-auth`) |
| Payment Gateway   | Stripe                     |
| Email Service     | FastAPI-Mail               |
| Data Validation   | Pydantic                   |
| Code Formatting   | Black, isort               |


## 📁 Project Architecture

```
etk/
├── main.py                          # FastAPI application initialization
├── enums.py                         # Shared enumeration types
├── pyproject.toml                   # Project metadata and dependencies
├── requirements.txt                 # Python package dependencies
├── .env                             # Environment configuration (not tracked)
├── .vscode/                         # VS Code workspace settings
├── static/profile_images/           # User profile image storage
│
├── core/
│   ├── config.py                   # Settings and environment variables
│   └── database.py                 # SQLAlchemy async engine & session management
│
├── models/                          # SQLAlchemy ORM models (Database Schema)
│   ├── users.py                    # User model with relationships
│   ├── company_profile.py          # Company profile model
│   ├── subscription_plan.py        # Subscription plan model
│   └── user_subscription.py        # User subscription tracking model
│
├── routes/                          # API endpoint handlers
│   ├── auth.py            # Authentication endpoints (signup/login/OAuth/password reset)
│   ├── user.py            # User profile management endpoints
│   ├── subscription.py    # Subscription listing and management
│   └── billing.py         # Stripe checkout, invoices, webhooks
│
├── schemas/                         # Pydantic request/response models
│   ├── base.py                     # BaseResponse envelope for all API responses
│   ├── auth.py                     # Auth request/response schemas
│   ├── users.py                    # User profile schemas
│   ├── subscription.py             # Subscription plan schemas
│   └── billing.py                  # Billing and invoice schemas
│
└── utils/                           # Shared utility functions
    ├── auth.py                     # JWT generation, password hashing, email sending
    ├── users.py                    # User lookup helpers
    └── subscription.py             # Subscription queries and helpers
```

**Total Codebase:** ~1,910 lines of Python across 28 files

## 🚀 API Endpoints

### Authentication Routes (`/auth`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|----------------|
| POST | `/signup` | User registration with email & password | ❌ |
| POST | `/login` | Email/password authentication | ❌ |
| POST | `/google-auth` | Google OAuth2 authentication | ❌ |
| POST | `/linkedin-auth` | LinkedIn OAuth authentication | ❌ |
| POST | `/forgot-password` | Request OTP for password reset | ❌ |
| POST | `/reset-password` | Reset password using OTP | ❌ |

**Response Format:**
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe"
    },
    "subscription": {
      "plan_name": "GOLD",
      "max_saved_queries": 100,
      "max_compare_countries": 5,
      "status": "active"
    }
  }
}
```

### User Management Routes (`/user`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|----------------|
| PATCH | `/user/account` | Update user profile (name, profile image) | ✅ JWT |
| GET | `/user/profile` | Get authenticated user's profile | ✅ JWT |
| GET | `/user/details` | Get user details with subscription info | ✅ JWT |

**Profile Update Request:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "profile_image": "data:image/png;base64,iVBORw0KGgoAAAANS..."
}
```

### Subscription Routes (`/subscriptions`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|----------------|
| GET | `/subscriptions` | List all available subscription plans | Yes |

**Plan Response Example:**
```json
{
  "success": true,
  "message": "Subscriptions retrieved successfully",
  "data": [
    {
      "id": "plan_123",
      "plan_name": "GOLD",
      "description": "For individual researchers",
      "features": ["100 saved queries", "5 country comparisons"],
      "max_saved_queries": 100,
      "max_compare_countries": 5,
      "amount": 29.99,
      "currency": "USD",
      "interval": "month",
      "is_custom_pricing": false
    }
  ]
}
```

### Billing Routes (`/billing`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|----------------|
| POST | `/billing/create-checkout-session` | Create Stripe checkout session | ✅ JWT |
| GET | `/billing/invoices` | List user's invoices | ✅ JWT |
| GET | `/billing/invoices/{invoice_id}` | Get specific invoice details | ✅ JWT |
| POST | `/billing/webhook` | Stripe webhook endpoint | ⚠️ Signature |

## 📋 Data Models

### User
```python
- id: UUID (Primary Key, indexed)
- email: String (Unique, indexed)
- password: String (hashed with bcrypt)
- first_name: String (nullable)
- last_name: String (nullable)
- profile_image: String (URL path to uploaded image)
- otp: String (6 digits, for password reset)
- otp_expiry: DateTime (5-minute validity)
- deleted_at: DateTime (soft delete support)
- created_at: DateTime (auto-timestamp)
- updated_at: DateTime (auto-timestamp)
```

### UserSubscription
```python
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key)
- plan_id: UUID (Foreign Key)
- stripe_customer_id: String (Stripe customer token)
- stripe_subscription_id: String (Stripe subscription token)
- status: Enum (active, trialing, canceled, expired)
- current_period_end: DateTime (subscription renewal date)
- created_at: DateTime
- updated_at: DateTime
```

### SubscriptionPlan
```python
- id: UUID (Primary Key)
- name: Enum (FREE, SILVER, GOLD, PLATINUM)
- description: String
- features: JSON Array
- max_saved_queries: Integer
- max_compare_countries: Integer
- stripe_price_id: String (Stripe pricing tier)
- is_active: Boolean
- created_at: DateTime
```

### CompanyProfile
```python
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key)
- company_name: String
- description: String (nullable)
- logo_url: String (nullable)
- website: String (nullable)
- created_at: DateTime
- updated_at: DateTime
```

## ⚙️ Configuration & Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
# MySQL example:
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/etk_db
# PostgreSQL example:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/etk_db

# Email Configuration (Gmail recommended)
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=your-gmail-app-password

# JWT Authentication
SECRET_KEY=your-super-secret-jwt-key-min-32-chars-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx  # or sk_live_xxx for production
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxx

# Frontend URL (for CORS and redirects)
FRONTEND_URL=http://localhost:3000
```

## 🔧 Installation & Setup

### Prerequisites
- **Python 3.10+** (check with `python --version`)
- **MySQL 8.0+** or **PostgreSQL 12+**
- **Stripe Account** (free tier available at stripe.com)
- **Google OAuth Credentials** (for social login)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/etk-backend.git
   cd etk
   ```

2. **Create Python virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # or using uv (faster):
   uv sync
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   nano .env
   ```

5. **Initialize database**
   ```bash
   # Tables auto-create on app startup via SQLAlchemy
   python main.py
   ```

6. **Verify API is running**
   ```bash
   curl http://localhost:8000/api/docs
   ```

## 📚 API Documentation

Interactive API documentation available at:

- **Swagger UI** (Recommended): http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

## 🔐 Authentication Flow

### JWT Token Flow
1. User calls `/auth/login` or `/auth/signup`
2. API returns JWT token with 24-hour expiry
3. Client stores token in localStorage
4. All authenticated requests include: `Authorization: Bearer <token>`
5. JWT payload includes user_id for verification

### Google OAuth Flow
1. Frontend redirects to Google consent screen
2. User grants permissions
3. Frontend receives `id_token`
4. Frontend calls `/auth/google-auth` with token
5. Backend verifies token with Google
6. If user doesn't exist, creates new account
7. Returns JWT and subscription details

## 💳 Stripe Integration

### Checkout Flow
1. User selects subscription plan on frontend
2. Frontend calls `/billing/create-checkout-session`
3. Backend creates Stripe Checkout session
4. Returns session URL
5. User redirected to Stripe-hosted checkout
6. User enters payment details
7. Stripe processes payment
8. Webhook confirms subscription

### Webhook Events Handled
- `checkout.session.completed` - Create/update user subscription
- `customer.subscription.updated` - Update subscription status
- `customer.subscription.deleted` - Downgrade to FREE plan
- `invoice.payment_succeeded` - Process successful invoice

**Webhook Verification:**
```python
# All webhooks include Stripe-Signature header
# Backend verifies using STRIPE_WEBHOOK_SECRET
# Prevents unauthorized webhook calls
```

## 🛠️ Development

### Code Style & Formatting
```bash
# Format with Black
black .

# Sort imports with isort
isort .
```


### Local Development Server
```bash
# Auto-reload on code changes
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the direct Python script
python main.py
```

### Database Connection Pooling
- **Pool Recycle**: 3600 seconds (prevents MySQL timeout)
- **Pre-ping**: Enabled (detects stale connections)
- **Pool Size**: Default async pool
- **Async**: Fully async with aiomysql/asyncpg

## 📦 File Upload Handling

### Profile Image Upload
- **Format**: Base64-encoded data URL
- **Max Size**: 5 MB
- **Supported Types**: PNG, JPEG, WebP
- **Storage**: `/static/profile_images/`
- **URL Pattern**: `/static/profile_images/{user-id}.{ext}`

**Example Request:**
```json
{
  "profile_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..."
}
```

## 📊 Response Format

All API responses follow a standardized envelope:

```json
{
  "success": true,
  "message": "Operation successful",
  "data": { /* response payload */ }
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "email: Email already exists",
  "data": null
}
```

## 🐛 Troubleshooting

### Database Connection Failed
```
Error: (2003, "Can't connect to MySQL server")
Solution:
- Verify MySQL is running: mysql -u root -p
- Check DATABASE_URL format
- Ensure database user has permissions
```

### Email Not Sending
```
Error: SMTPAuthenticationError
Solution:
- Use Gmail app password (not regular password)
- Enable "Less secure apps" if needed
- Verify EMAIL_USER and EMAIL_PASS in .env
```

### Stripe Webhook Not Triggering
```
Solution:
- Verify STRIPE_WEBHOOK_SECRET matches Stripe dashboard
- Test locally with: stripe listen --forward-to localhost:8000/api/billing/webhook
- Check webhook signature in Stripe dashboard logs
```

### JWT Token Expired
```
Error: "Token has expired"
Solution:
- Frontend should re-call /auth/login
- Or implement refresh token mechanism (future enhancement)
```

## 📈 Performance Optimization

- **Async Processing**: All I/O operations are async
- **Connection Pooling**: Automatic connection reuse
- **Lazy Loading**: SQLAlchemy relationships optimized
- **Response Caching**: Stripe plan cache (future)
- **Database Indexing**: Indexed email, user_id fields

## 🔐 Security Features

- ✅ **Bcrypt Password Hashing**: Industry-standard password security
- ✅ **JWT Tokens**: Secure, stateless authentication
- ✅ **Email Verification**: OTP-based account security
- ✅ **OAuth2 Support**: Multiple identity providers
- ✅ **CORS Protection**: Configurable cross-origin access
- ✅ **Pydantic Validation**: Type-safe input validation
- ✅ **Stripe Webhook Verification**: Cryptographic signature checks
- ✅ **SQL Injection Prevention**: SQLAlchemy parameterized queries
- ✅ **Soft Deletes**: User data retention with deletion flag

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/amazing-feature`
2. Commit changes: `git commit -m 'Add amazing feature'`
3. Push to branch: `git push origin feature/amazing-feature`
4. Open pull request

## 📄 License

© 2026 ETK Dashboard. All rights reserved.
