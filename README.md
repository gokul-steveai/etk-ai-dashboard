# ETK - Enterprise Toolkit API

A modern, asynchronous FastAPI backend for the ETK AI Dashboard, providing comprehensive user management, authentication, subscription management, and billing integration capabilities.

## Overview

ETK is a full-featured enterprise backend service built with FastAPI, SQLAlchemy ORM, and Stripe integration. It handles user authentication (email/password and OAuth), subscription management with multiple plans, billing operations, and company profile management.

## Features

- **Authentication & Authorization**
  - Email/password authentication with JWT tokens
  - Google OAuth2 integration
  - LinkedIn OAuth integration
  - OTP-based password reset
  - Secure token generation and verification

- **User Management**
  - User registration and profile management
  - Email verification and validation
  - Role-based access control
  - User subscription tracking

- **Subscription Management**
  - Multiple subscription plans (Free, Basic, Individual, Researcher, Enterprise)
  - Subscription status tracking (Active, Trialing, Canceled, Expired)
  - Plan upgrade/downgrade functionality

- **Billing Integration**
  - Stripe payment processing
  - Webhook handling for payment events
  - Invoice management
  - Subscription lifecycle management

- **Company Profiles**
  - Company information management
  - Profile customization

## Tech Stack

- **Framework**: FastAPI 0.116.1
- **Database**: SQLAlchemy 2.0.41 with async support (aiomysql/psycopg2)
- **Authentication**: JWT (python-jose), Google Auth, bcrypt
- **Payments**: Stripe 15.1.0
- **Email**: FastAPI-Mail 1.5.0
- **Validation**: Pydantic 2.11.7
- **Server**: Uvicorn 0.35.0

## Project Structure

```
.
├── main.py                 # Application entry point and FastAPI setup
├── core/
│   ├── database.py        # Database connection and session management
│   └── config.py          # Configuration and environment variables
├── models/                # SQLAlchemy ORM models
│   ├── users.py
│   ├── company_profile.py
│   ├── subscription_plan.py
│   └── user_subscription.py
├── routes/                # API endpoints
│   ├── auth.py           # Authentication endpoints (signup, login, OAuth)
│   ├── user.py           # User management endpoints
│   ├── subscription.py    # Subscription endpoints
│   └── billing.py        # Billing and Stripe integration
├── schemas/               # Pydantic request/response models
│   ├── auth.py
│   ├── users.py
│   ├── subscription.py
│   ├── billing.py
│   └── base.py
├── utils/                 # Utility functions
│   ├── auth.py           # Authentication helpers (token generation, password hashing)
│   ├── users.py          # User helper functions
│   └── subscription.py    # Subscription helper functions
├── enums.py              # Enumeration types (BillingPlan, PlanName, SubscriptionStatus)
├── requirements.txt      # Python dependencies
└── pyproject.toml        # Project metadata and configuration
```

## Installation

### Prerequisites

- Python 3.10 or higher
- MySQL or PostgreSQL database
- Stripe account (for payment processing)
- Google OAuth credentials (for Google authentication)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd etk
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```
   # Database
   DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/etk
   # or for PostgreSQL:
   # DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/etk

   # Email Configuration
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASS=your-app-password

   # Authentication
   SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   GOOGLE_CLIENT_ID=your-google-client-id

   # Stripe
   STRIPE_SECRET_KEY=sk_test_xxxxx
   STRIPE_WEBHOOK_SECRET=whsec_xxxxx
   FRONTEND_URL=http://localhost:3000
   ```

5. **Run the application**
   ```bash
   python main.py
   ```
   
   The API will be available at `http://localhost:8000/api`

## API Endpoints

### Authentication (`/auth`)
- `POST /signup` - User registration
- `POST /login` - Email/password login
- `POST /google-auth` - Google OAuth authentication
- `POST /linkedin-auth` - LinkedIn OAuth authentication
- `POST /forgot-password` - Request password reset
- `POST /reset-password` - Reset password with OTP

### Users (`/users`)
- `GET /profile` - Get current user profile
- `PUT /profile` - Update user profile
- `GET /me` - Get authenticated user details
- `DELETE /account` - Delete user account

### Subscriptions (`/subscriptions`)
- `GET /plans` - List all subscription plans
- `GET /my-subscription` - Get user's current subscription
- `POST /subscribe` - Subscribe to a plan
- `POST /upgrade` - Upgrade subscription
- `POST /cancel` - Cancel subscription

### Billing (`/billing`)
- `GET /invoices` - List user invoices
- `GET /invoices/{id}` - Get invoice details
- `POST /payment-method` - Add payment method
- `POST /webhook` - Stripe webhook handler

## API Documentation

Once the application is running, interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`

## Configuration

Configuration is managed through environment variables using Pydantic Settings:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | Yes | - | Database connection string |
| EMAIL_USER | Yes | - | Email address for sending emails |
| EMAIL_PASS | Yes | - | Email password or app password |
| SECRET_KEY | No | TheSecretKey | JWT secret key |
| ALGORITHM | No | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | No | 1440 | Token expiration in minutes |
| GOOGLE_CLIENT_ID | Yes | - | Google OAuth client ID |
| STRIPE_SECRET_KEY | Yes | - | Stripe API secret key |
| STRIPE_WEBHOOK_SECRET | No | - | Stripe webhook signing secret |
| FRONTEND_URL | No | http://localhost:3000 | Frontend application URL |

## Database Models

### Users
- User ID (UUID)
- Email (unique)
- Password (hashed)
- Full name
- Profile picture
- Email verification status
- Timestamps

### Company Profile
- Company ID
- Name
- Description
- Logo
- Website URL

### Subscription Plan
- Plan ID
- Plan name (Free, Basic, Individual, Researcher, Enterprise)
- Description
- Price
- Features list
- Billing cycle

### User Subscription
- Subscription ID
- User ID
- Plan ID
- Status (Active, Trialing, Canceled, Expired)
- Start date
- End date
- Stripe subscription ID

## Development

### Code Style
The project uses:
- **Black** for code formatting
- **isort** for import sorting
- **Pydantic** for data validation

Format code before committing:
```bash
black .
isort .
```

### Database Initialization

The application automatically creates all database tables on startup through SQLAlchemy's declarative base. Connection pooling is configured with:
- Connection recycling every 3600 seconds (prevents MySQL timeout errors)
- Pre-ping connections (detects disconnected DB connections)

## Security Features

- **Password Security**: Passwords hashed using bcrypt
- **JWT Authentication**: Secure token-based authentication
- **Email Verification**: Email validation before account activation
- **OAuth2**: Supports multiple OAuth providers
- **Stripe Webhooks**: Secure webhook verification
- **CORS**: Configurable cross-origin resource sharing
- **Validation**: Input validation using Pydantic

## Error Handling

The API provides consistent error responses with validation error details:

```json
{
  "success": false,
  "message": "field_name: error description"
}
```

## Logging

The application uses async-aware logging for monitoring database connections and critical operations. Check console output for:
- Database connection status
- Authentication events
- Payment processing results

## Deployment

### Using Gunicorn with Uvicorn Workers

```bash
pip install gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Environment-Specific Configuration

### Development
```env
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/etk_dev
DEBUG=True
```

### Production
```env
DATABASE_URL=mysql+aiomysql://user:password@prod-db.com:3306/etk
STRIPE_SECRET_KEY=sk_live_xxxxx
```

## Troubleshooting

### Database Connection Issues
- Ensure MySQL/PostgreSQL is running and accessible
- Check DATABASE_URL format matches your database driver
- Verify database user has appropriate permissions

### Email Sending Issues
- Use Gmail app passwords instead of regular passwords
- Enable "Less secure app access" if needed
- Check EMAIL_USER and EMAIL_PASS in .env

### Stripe Integration
- Verify STRIPE_SECRET_KEY is correct
- Test webhook signing with STRIPE_WEBHOOK_SECRET
- Use Stripe CLI for local webhook testing

## License

This project is proprietary software for the ETK AI Dashboard.

## Support

For issues or questions, please contact the development team or create an issue in the project repository.
