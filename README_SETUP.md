# BookMySeat - Movie Ticket Booking System

A scalable, production-ready Django-based movie ticket booking system with advanced features including concurrent seat reservation, payment gateway integration, email notifications, and admin analytics.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Database Setup](#database-setup)
- [API Endpoints](#api-endpoints)
- [Payment Webhook Integration](#payment-webhook-integration)
- [Admin Dashboard](#admin-dashboard)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

### 1. **Scalable Genre & Language Filtering**
- Multi-select filtering with optimized database queries
- Dynamic filter counts without full-table scans
- Indexed fields for efficient catalog searches
- Pagination (25 movies per page)
- Support for 100+ movies with multiple genres and languages

### 2. **Automated Email Confirmations**
- Non-blocking email dispatch via background threads
- Transactional safety with `transaction.on_commit()`
- Retry logic with exponential backoff (1, 5, 15, 60 minutes)
- HTML and plain-text templates
- Sensitive data sanitization before storage

### 3. **Secure YouTube Trailer Embedding**
- Strict regex validation for YouTube URLs
- Privacy-enhanced `youtube-nocookie.com` endpoints
- XSS protection
- Lazy loading with cross-origin referrer controls

### 4. **Payment Gateway Integration**
- HMAC-SHA256 webhook signature validation
- Idempotency key support to prevent duplicate bookings
- Atomic transactions for safe payment processing
- Support for multiple payment statuses: completed, failed, pending, cancelled
- Automatic seat release on payment failure

### 5. **Concurrency-Safe Seat Reservation**
- Row-level database locking with `select_for_update()`
- 2-minute hold on reserved seats
- Automatic expiration and cleanup
- Race condition prevention

### 6. **Admin Analytics Dashboard**
- Role-based access control
- Revenue tracking (daily, weekly, monthly)
- Popular movies and theater occupancy metrics
- Peak hours analysis
- Cancellation rate calculations
- Database-level aggregations for performance

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.1.1 |
| Database | SQLite (development) / PostgreSQL (production) |
| Email | SMTP (Gmail/SendGrid recommended) |
| Authentication | Django built-in |
| Frontend | Django Templates + Unsplash for images |
| Task Queue | Background threading |

---

## 📦 Installation

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- **Git**
- **Virtual Environment** (recommended)

### Step 1: Clone & Navigate

```bash
cd d:\code\Intership
```

### Step 2: Create Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
pip list | findstr Django
# Should show: Django 5.1.1
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root (or set them in your terminal):

```bash
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@bookmyseat.local

# Payment Gateway (Razorpay; secret stays server-side)
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your-razorpay-key-secret

# Database (optional for production)
DATABASE_URL=postgresql://user:password@localhost:5432/bookmyseat

# Debug Mode (set to False in production)
DEBUG=True
```

### Gmail Setup (Recommended)

1. Enable 2-Step Verification in Google Account
2. Generate App Password:
   - Visit: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer"
   - Copy the 16-character password
3. Use as `EMAIL_HOST_PASSWORD` above

---

## 🚀 Running the Application

### Step 1: Apply Migrations

```bash
python manage.py migrate
```

**Output:**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, movies, sessions, users
Running migrations:
  Applying movies.0007_booking_amount... OK
  (other migrations...)
```

### Step 2: Create Superuser (Admin Account)

```bash
python manage.py createsuperuser
```

**Follow prompts:**
```
Username: admin
Email: admin@example.com
Password: (enter secure password)
Password (again): (confirm)
```

### Step 3: Generate Test Data

```bash
python manage.py generate_test_data --movies 120
```

**Output:**
```
Starting data generation...
Creating genres...
✓ Created 27 genres
Creating languages...
✓ Created 10 languages
Creating 120 movies...
  20/120 movies created...
  40/120 movies created...
  ...
✓ Created 120 movies

========== SUMMARY ==========
Genres: 27
Languages: 10
Movies: 120
Gallery Images: 240
Theaters: 156
Seats: 4680
========== COMPLETE ==========

Test data generated successfully! Visit http://127.0.0.1:8000/
```

### Step 4: Run Development Server

```bash
python manage.py runserver
```

**Output:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
July 12, 2026 - 14:30:15
Django version 5.1.1, using settings 'bookmyseat.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Step 5: Access the Application

| URL | Purpose | Credentials |
|-----|---------|-------------|
| http://127.0.0.1:8000/ | Movie Listing | Public access |
| http://127.0.0.1:8000/admin/ | Django Admin | Username/password |
| http://127.0.0.1:8000/login/ | User Login | Register or use test account |

---

## 💾 Database Setup

### Development (SQLite)

No setup needed. Django auto-creates `db.sqlite3` on first migration.

### Production (PostgreSQL)

```bash
# Install PostgreSQL adapter
pip install psycopg2-binary

# Set connection string
set DATABASE_URL=postgresql://user:password@localhost:5432/bookmyseat

# Run migrations
python manage.py migrate
```

### View Database Schema

```bash
# List all models
python manage.py sqlmigrate movies 0007_booking_amount

# Check database tables
python manage.py dbshell
sqlite> .tables
sqlite> .schema movies_booking
```

---

## 🔌 API Endpoints

### Public Endpoints

```bash
# List movies with filtering
GET /movies/
  ?search=quantum
  &genres=1,2
  &languages=1,2
  &sort=-release_date
  &page=1

# Theater availability for a movie
GET /movies/<movie_id>/theaters

# Get payment status
GET /movies/payments/<payment_id>/
  (requires user authentication)
```

### Admin Endpoints

```bash
# Admin analytics dashboard
GET /movies/admin-analytics/
  (requires staff privileges)
```

### Payment Webhook

```bash
# Receive payment updates
POST /movies/payments/webhook/
Headers:
  X-Razorpay-Signature: <Razorpay HMAC-SHA256>
  Content-Type: application/json

Body: native Razorpay `payment.captured` or `payment.failed` event payload
```

---

## 💳 Payment Webhook Integration

### How It Works

1. **User books seats** → Creates booking with `payment_status='pending'`
2. **Payment processed** → Payment gateway calls webhook
3. **Signature verified** → HMAC-SHA256 validation
4. **Status updated** → Booking and reservation status updated atomically
5. **Seat confirmed** → Reservation moves from RESERVED to CONFIRMED

### Testing Webhook Locally

Use Razorpay test mode and configure a public HTTPS tunnel as the webhook URL.
The endpoint intentionally rejects hand-created success events because they
cannot prove a gateway payment.

### Expected Response (Success)

```json
{
  "status": "processed",
  "message": "Payment status updated",
  "booking_id": 1
}
```

---

## 📊 Admin Dashboard

### Access Admin Panel

1. Navigate to: http://127.0.0.1:8000/admin/
2. Login with superuser credentials
3. Manage:
   - Movies, Genres, Languages
   - Theaters, Seats
   - Bookings, Reservations
   - Email Tasks

### View Analytics

1. Go to: http://127.0.0.1:8000/movies/admin-analytics/
2. View metrics:
   - Daily/Weekly/Monthly Revenue
   - Popular Movies
   - Theater Occupancy
   - Peak Hours
   - Cancellation Rate

---

## 🧪 Testing

### Email Queue Management

```bash
# Process pending emails
python manage.py process_email_queue --limit 20

# View email statistics
python manage.py process_email_queue --stats

# Clean up old emails (older than 30 days)
python manage.py process_email_queue --cleanup 30
```

### Seat Expiration

```bash
# Check expired reservations
python manage.py shell
>>> from movies.models import SeatReservation
>>> SeatReservation.release_expired_reservations()
```

### Test User Account

Create a test account:

```bash
python manage.py shell

>>> from django.contrib.auth.models import User
>>> User.objects.create_user(
...   username='testuser',
...   email='test@example.com',
...   password='testpass123'
... )

# Exit shell
>>> exit()
```

### Run Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test movies

# Run with verbose output
python manage.py test --verbosity=2
```

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Migration Error** | Delete `db.sqlite3` and run `migrate` again |
| **Port Already in Use** | `python manage.py runserver 8001` |
| **Module Not Found** | Ensure virtual environment is activated: `venv\Scripts\Activate.ps1` |
| **Email Not Sending** | Check `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in settings |
| **Webhook Signature Invalid** | Ensure `RAZORPAY_KEY_SECRET` matches the gateway webhook secret |
| **Static Files Missing** | Run `python manage.py collectstatic` |

### Debug Mode

Enable detailed error messages:

```python
# In bookmyseat/settings.py
DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

### Reset Database

```bash
# Remove database
rm db.sqlite3

# Recreate everything
python manage.py migrate
python manage.py createsuperuser
python manage.py generate_test_data
```

---

## 📈 Performance Tuning

### Database Optimization

```python
# Use select_related() for ForeignKey
Movie.objects.select_related('user')

# Use prefetch_related() for ManyToMany
Movie.objects.prefetch_related('genres', 'languages')

# Use only() to fetch specific fields
Movie.objects.only('id', 'name', 'rating')

# Use values() for aggregations
Genre.objects.values('id').annotate(count=Count('movies'))
```

### Query Monitoring

```bash
# Install django-debug-toolbar
pip install django-debug-toolbar

# Add to INSTALLED_APPS in settings.py
INSTALLED_APPS += ['debug_toolbar']

# Add middleware
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

---

## 📚 Project Structure

```
Intership/
├── bookmyseat/          # Project settings
│   ├── settings.py      # Configuration
│   ├── urls.py          # URL routing
│   └── wsgi.py          # Production server
├── movies/              # Movie booking app
│   ├── models.py        # Database models
│   ├── views.py         # Business logic
│   ├── urls.py          # Movie app routes
│   ├── email_tasks.py   # Email background tasks
│   └── management/      # Management commands
│       └── commands/
│           ├── generate_test_data.py
│           └── process_email_queue.py
├── users/               # User authentication
│   ├── models.py
│   ├── views.py
│   └── forms.py
├── templates/           # HTML templates
├── media/               # Uploaded files
├── db.sqlite3           # SQLite database
├── manage.py            # Django CLI
└── requirements.txt     # Dependencies
```

---

## 🔒 Security Best Practices

1. **Change Secret Key in Production**
   ```python
   # bookmyseat/settings.py
   SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production')
   ```

2. **Set DEBUG = False in Production**
   ```python
   DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
   ```

3. **Use HTTPS in Production**
   ```python
   SECURE_SSL_REDIRECT = True
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   ```

4. **Secure Payment Webhook**
   - Keep `RAZORPAY_KEY_SECRET` only in the deployment secret store
   - Validate Razorpay signatures over the raw body always
   - Use HTTPS for webhook endpoint

5. **Database Backups**
   ```bash
   # Regular backups
   cp db.sqlite3 backups/db-$(date +%Y%m%d).sqlite3
   ```

---

## 📞 Support & Documentation

- **Django Docs**: https://docs.djangoproject.com/
- **Project Issues**: Check logs in `logs/` directory
- **Email Issues**: See `django.core.mail` documentation

---

## 📄 License

This project is provided as-is for educational and commercial use.

---

**Version**: 1.0.0  
**Last Updated**: July 12, 2026  
**Status**: Production Ready ✅
