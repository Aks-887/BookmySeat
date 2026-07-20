# 🎬 BookMySeat - Movie Ticket Booking System

A production-ready Django application for online movie ticket booking with advanced features including concurrent seat reservation, payment gateway integration, automated email notifications, and comprehensive admin analytics.

**Status:** ✅ Production Ready | **Version:** 1.0.0 | **Last Updated:** July 12, 2026

---

## 📋 Quick Links

| Document | Purpose |
|----------|---------|
| **[QUICKSTART.md](QUICKSTART.md)** | 🚀 **START HERE** - Run in 5 minutes |
| **[README_SETUP.md](README_SETUP.md)** | 📖 Complete installation & configuration guide |
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** | 🔌 API reference & endpoint documentation |

---

## ✨ Key Features

### 🎯 Core Features

1. **Scalable Movie Catalog**
   - 100+ movies with multi-select genre/language filtering
   - Optimized database queries (prefetch_related, select_for_update)
   - Pagination (25 movies per page)
   - Real-time filter counts

2. **Secure Seat Reservation**
   - Row-level database locking (prevents race conditions)
   - 2-minute hold on reserved seats
   - Automatic expiration and cleanup
   - Concurrent user support

3. **Payment Gateway Integration**
   - HMAC-SHA256 webhook signature validation
   - Idempotency key support (prevents double bookings)
   - Multiple payment statuses (completed, failed, pending, cancelled)
   - Atomic transactions for data integrity

4. **Automated Email System**
   - Non-blocking background email dispatch
   - Transactional safety (transaction.on_commit)
   - Retry logic with exponential backoff
   - HTML and plain-text templates
   - Sensitive data sanitization

5. **YouTube Trailer Embedding**
   - Strict regex validation
   - Privacy-enhanced youtube-nocookie.com
   - XSS protection
   - Lazy loading optimization

6. **Admin Analytics Dashboard**
   - Revenue tracking (daily, weekly, monthly)
   - Popular movies & theater occupancy
   - Peak hours analysis
   - Cancellation rate metrics
   - Role-based access control

---

## 🏗️ Technology Stack

```
Backend:        Django 5.1.1
Database:       SQLite (dev) / PostgreSQL (prod)
Authentication: Django Auth
Email:          SMTP (Gmail/SendGrid compatible)
Frontend:       Django Templates + Unsplash
Task Queue:     Threading + background processes
```

---

## 🚀 Getting Started (30 seconds)

### Prerequisites
- Python 3.10+
- pip
- Git

### Installation

**Windows (PowerShell):**
```powershell
cd d:\code\Intership
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py generate_test_data --movies 120
python manage.py runserver
```

**macOS/Linux:**
```bash
cd ~/code/Intership
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py generate_test_data --movies 120
python manage.py runserver
```

### 🌐 Access Points

| URL | Purpose |
|-----|---------|
| `http://127.0.0.1:8000/` | Movie catalog & booking |
| `http://127.0.0.1:8000/admin/` | Admin panel |
| `http://127.0.0.1:8000/admin-analytics/` | Analytics dashboard |

**👉 See [QUICKSTART.md](QUICKSTART.md) for detailed steps**

---

## 📁 Project Structure

```
Intership/
├── bookmyseat/              # Django project settings
│   ├── settings.py          # Configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # Production server
├── movies/                  # Main app
│   ├── models.py            # Database models
│   ├── views.py             # Views & business logic
│   ├── urls.py              # App URL patterns
│   ├── email_tasks.py       # Email background tasks
│   └── management/commands/
│       ├── generate_test_data.py
│       └── process_email_queue.py
├── users/                   # User authentication
├── templates/               # HTML templates
├── media/                   # Uploaded files
├── db.sqlite3               # Database (created after migrate)
├── manage.py                # Django CLI
├── requirements.txt         # Dependencies
├── QUICKSTART.md            # Quick start guide ⭐ START HERE
├── README_SETUP.md          # Full setup guide
├── API_DOCUMENTATION.md     # API reference
└── README.md                # This file
```

---

## 🎯 Database Models

### Core Models

```python
Movie
├── name, rating, description
├── genres (ManyToMany)
├── languages (ManyToMany)
├── trailer_url (with sanitization)
└── images (MovieImage)

Theater
├── movie (ForeignKey)
├── name, time
└── seats (Seat)

Seat
├── theater (ForeignKey)
├── seat_number, is_booked
└── reservation (SeatReservation - optional)

Booking
├── user, movie, theater, seat
├── payment_id (UUID, db_indexed)
├── idempotency_key (duplicate prevention)
├── payment_status (pending/completed/failed/cancelled)
├── amount (DecimalField - new!)
└── booked_at (timestamp)

SeatReservation
├── user, seat, theater, movie
├── status (reserved/confirmed/expired/cancelled)
├── expires_at (2-minute hold)
├── payment_reference
└── idempotency_key (linking to booking)

EmailTask
├── recipient, subject, template_name
├── context (JSON), status, attempts
├── next_attempt_at (retry scheduling)
└── last_error
```

---

## 💻 Common Commands

### Development

```bash
# Run server
python manage.py runserver

# Create new app
python manage.py startapp myapp

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Generate test data
python manage.py generate_test_data --movies 120

# Process email queue
python manage.py process_email_queue --limit 20

# Django shell
python manage.py shell
```

### Database

```bash
# Make migrations
python manage.py makemigrations

# Show migration SQL
python manage.py sqlmigrate movies 0007_booking_amount

# Database shell
python manage.py dbshell

# View model schema
python manage.py inspectdb
```

### Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test movies

# Verbose output
python manage.py test --verbosity=2

# Run specific test
python manage.py test movies.tests.BookingTests
```

---

## 🔌 API Quick Reference

### Movies
```bash
GET /movies/                              # List all movies
GET /movies/?search=quantum               # Search
GET /movies/?genres=1,2&languages=1      # Filter
GET /movies/<id>/theaters                 # Get showtimes
```

### Booking
```bash
POST /movies/theater/<id>/seats/book/    # Create booking
GET /movies/payments/<payment_id>/        # Check status
```

### Webhook
```bash
POST /movies/payments/webhook/            # Payment notification
  Headers: X-Razorpay-Signature: <Razorpay HMAC-SHA256>
```

### Admin
```bash
GET /movies/admin-analytics/              # Dashboard
GET /admin/                                # Django admin
```

**👉 See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete reference**

---

## 🔒 Security Features

✅ **HMAC-SHA256 Webhook Signature Validation**
- Prevents unauthorized payment updates
- Constant-time comparison (prevents timing attacks)

✅ **Idempotency Key Support**
- Prevents duplicate bookings
- Safe webhook retries

✅ **Row-Level Database Locking**
- Prevents race conditions
- Concurrent user support

✅ **SQL Injection Prevention**
- Django ORM parameterization

✅ **XSS Protection**
- YouTube URL validation
- Template auto-escaping

✅ **CSRF Protection**
- Django CSRF middleware

✅ **Sensitive Data Sanitization**
- Context scrubbing before logging
- No passwords in email tasks

---

## 📊 Performance Optimizations

### Database Queries
- `select_related()` for ForeignKey joins
- `prefetch_related()` for ManyToMany
- `only()` to fetch specific fields
- Indexes on frequently queried fields

### Caching
- Django's cache framework ready
- Query result caching available

### Pagination
- 25 movies per page (optimal)
- Configurable in settings

### Email
- Non-blocking background threads
- Exponential backoff retry (1, 5, 15, 60 min)
- Queue management via management command

---

## 🧪 Testing the System

### Test User Account
```bash
# Create via admin or shell
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_user('testuser', 'test@example.com', 'pass123')
```

### Test Booking Flow
1. Login as test user
2. Browse movies on homepage
3. Filter by genre/language
4. Select a movie → View theaters
5. Book seats (select 2-3 seats)
6. Mock payment webhook
7. Check booking status

### Test Admin Features
1. Login as superuser
2. Visit `/admin/` → Manage movies/bookings
3. Visit `/admin-analytics/` → View metrics

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Port already in use** | `python manage.py runserver 8001` |
| **ModuleNotFoundError** | Activate venv: `.\venv\Scripts\Activate.ps1` |
| **No such table** | Run: `python manage.py migrate` |
| **Email not sending** | Check `EMAIL_HOST_USER` & password |
| **Webhook signature error** | Verify `RAZORPAY_KEY_SECRET` matches the dashboard webhook secret |

**👉 See [README_SETUP.md](README_SETUP.md#troubleshooting) for detailed troubleshooting**

---

## 📈 Deployment

### Development
```bash
python manage.py runserver
```

### Production

1. **Set Environment Variables**
```bash
export SECRET_KEY="your-production-secret"
export DEBUG="False"
export ALLOWED_HOSTS="yourdomain.com"
export DATABASE_URL="postgresql://..."
export RAZORPAY_KEY_ID="rzp_test_..."
export RAZORPAY_KEY_SECRET="your-secret"
```

2. **Run Gunicorn**
```bash
gunicorn bookmyseat.wsgi:application --bind 0.0.0.0:8000
```

3. **Use Nginx Reverse Proxy**
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
    
    location /static/ {
        alias /path/to/static/;
    }
}
```

**👉 See [README_SETUP.md](README_SETUP.md#production-deployment) for detailed guide**

---

## 📝 Features Checklist

- ✅ Scalable movie catalog with filtering
- ✅ Concurrent-safe seat reservation
- ✅ Payment webhook integration
- ✅ Email confirmation system
- ✅ YouTube trailer embedding
- ✅ Admin analytics dashboard
- ✅ User authentication
- ✅ Role-based access control
- ✅ Database optimization
- ✅ Error handling & logging

---

## 📚 Documentation Files

1. **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes ⭐ START HERE
2. **[README_SETUP.md](README_SETUP.md)** - Complete setup guide
3. **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API reference
4. **[README.md](README.md)** - This file

---

## 🤝 Contributing

To contribute:

1. Create a feature branch
2. Make changes with clear commit messages
3. Test thoroughly
4. Submit pull request

---

## 📞 Support

**Issues?** Check:
1. [QUICKSTART.md](QUICKSTART.md#troubleshooting) - Quick troubleshooting
2. [README_SETUP.md](README_SETUP.md#troubleshooting) - Detailed troubleshooting
3. Django logs in console output

---

## 📄 License

This project is provided as-is for educational and commercial use.

---

## 🎯 Next Steps

### 🚀 **New to this project?**
👉 Start with **[QUICKSTART.md](QUICKSTART.md)**

### 📖 **Need detailed setup?**
👉 Read **[README_SETUP.md](README_SETUP.md)**

### 🔌 **Building an integration?**
👉 Check **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)**

---

## 📊 Project Stats

```
Total Models:           8
API Endpoints:          10+
Test Data:              120 movies
Genres:                 27
Languages:              10
Database Indexes:       15+
Management Commands:    2
Email Templates:        2
Test Coverage:          Configurable
```

---

**Version 1.0.0** | **Production Ready** ✅

Last Updated: July 12, 2026

---

### 🎉 Ready to get started?

```bash
cd d:\code\Intership
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

Visit: **http://127.0.0.1:8000/**
