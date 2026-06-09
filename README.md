# Expense Tracker

A secure, self-hosted expense tracker that automatically imports transactions from Gmail (credit card & UPI emails) and provides analytics dashboards with manual entry options.

## Features

- **Secure Authentication**: Username/password with TOTP 2FA
- **Gmail Integration**: Auto-import transactions from bank emails (HDFC, ICICI, SBI, Flash.co)
- **Manual Entry**: Add transactions manually via form
- **File Upload**: Import transactions from CSV/Excel files
- **Analytics Dashboard**: Visual insights with category and payment method breakdowns
- **Multi-bank Support**: Extensible parser system for different banks
- **Privacy-First**: Self-hosted, encrypted credentials, 30-day email retention

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: SQLite with Alembic migrations
- **Authentication**: JWT + TOTP (pyotp)
- **Encryption**: Fernet (cryptography)
- **Email**: Gmail API with OAuth2

### Frontend
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **Charts**: Recharts
- **Forms**: React Hook Form + Zod

## Project Structure

```
expense-tracker/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── api/      # API routes
│   │   ├── services/ # Business logic
│   │   └── parsers/  # Bank email parsers
│   ├── alembic/      # Database migrations
│   └── tests/        # Backend tests
├── frontend/         # React application
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── data/             # SQLite DB, credentials, uploads
└── docs/             # Documentation
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Gmail account with API credentials (for Phase 2)

### Backend Setup

1. **Create virtual environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Initialize database**:
   ```bash
   alembic upgrade head
   python scripts/create_admin.py
   ```

5. **Run backend**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

3. **Run frontend**:
   ```bash
   npm run dev
   ```

4. **Access application**:
   - Open [http://localhost:3000](http://localhost:3000)

## Development Phases

- [x] **Phase 0**: Project structure setup
- [ ] **Phase 1**: MVP - Auth + Manual Entry (Current)
- [ ] **Phase 2**: Gmail Integration
- [ ] **Phase 3**: Multi-Bank Support
- [ ] **Phase 4**: File Upload (CSV/Excel)
- [ ] **Phase 5**: Analytics Dashboard
- [ ] **Phase 6**: Security Hardening
- [ ] **Phase 7**: Deployment

See [Plan](C:/Users/rahul/.claude/plans/robust-puzzling-tome.md) for detailed implementation roadmap.

## Security

- Passwords hashed with bcrypt
- OAuth tokens encrypted at rest
- TOTP 2FA for authentication
- Rate limiting on API endpoints
- CORS restrictions
- Email retention: 30 days

See [docs/SECURITY.md](docs/SECURITY.md) for security best practices.

## Gmail API Setup

Before Phase 2, you'll need to:
1. Create a Google Cloud project
2. Enable Gmail API
3. Configure OAuth consent screen
4. Create OAuth 2.0 credentials

See detailed instructions in the [implementation plan](C:/Users/rahul/.claude/plans/robust-puzzling-tome.md#google-cloud-setup-for-gmail-api-before-phase-2).

## Database Schema

### Core Tables
- **users**: User accounts with encrypted credentials
- **transactions**: All expense transactions
- **emails**: Email processing metadata
- **sessions**: Secure session management
- **upload_history**: File upload tracking
- **audit_log**: Security event logging

See [implementation plan](C:/Users/rahul/.claude/plans/robust-puzzling-tome.md#database-schema) for detailed schema.

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - Login with password
- `POST /api/auth/verify-2fa` - Verify TOTP token
- `POST /api/auth/logout` - Logout

### Transactions
- `GET /api/transactions` - List transactions (with filters)
- `POST /api/transactions` - Create transaction
- `PUT /api/transactions/{id}` - Update transaction
- `DELETE /api/transactions/{id}` - Delete transaction

### Analytics (Phase 5)
- `GET /api/analytics/summary` - Summary statistics
- `GET /api/analytics/trends` - Time series data
- `GET /api/analytics/breakdown` - Category/payment breakdown

## Contributing

This is a personal project. See [implementation plan](C:/Users/rahul/.claude/plans/robust-puzzling-tome.md) for planned features.

## License

Private project - not licensed for public use.

## Next Steps

1. Complete Phase 1 implementation
2. Set up Google Cloud credentials
3. Test authentication flow
4. Begin Gmail integration (Phase 2)
