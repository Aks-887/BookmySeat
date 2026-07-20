# Quick Start Guide - BookMySeat

## ⚡ Run in 5 Minutes

### Windows PowerShell

```powershell
# 1. Navigate to project
cd d:\code\Intership

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Apply database migrations
python manage.py migrate

# 4. Create admin account
python manage.py createsuperuser

# 5. Generate test data (movies, theaters, seats)
python manage.py generate_test_data --movies 120

# 6. Start server
python manage.py runserver
```

### macOS/Linux

```bash
# 1. Navigate to project
cd ~/code/Intership

# 2. Activate virtual environment
source venv/bin/activate

# 3. Apply database migrations
python manage.py migrate

# 4. Create admin account
python manage.py createsuperuser

# 5. Generate test data
python manage.py generate_test_data --movies 120

# 6. Start server
python manage.py runserver
```

---

## 🌐 Access Points

Once the server is running at `http://127.0.0.1:8000/`:

| URL | Purpose |
|-----|---------|
| `http://127.0.0.1:8000/` | **Browse Movies** - Search, filter by genre/language |
| `http://127.0.0.1:8000/admin/` | **Admin Panel** - Manage movies, bookings, analytics |
| `http://127.0.0.1:8000/admin-analytics/` | **Analytics** - Revenue, popular movies, peak hours |
| `http://127.0.0.1:8000/login/` | **User Login** - Create account or sign in |

---

## 🎬 Try the System

### 1. Browse Movies
- Visit homepage
- Filter by Genre (e.g., "Action", "Romance")
- Filter by Language (e.g., "English", "Hindi")
- Click on movie to see showtimes

### 2. Book Tickets
- Select a theater/showtime
- Click "Book Seats"
- Select seats (e.g., A1, A2, B1)
- Click "Reserve"
- Proceed to payment

### 3. Check Booking Status
- Go to your profile
- View booking history
- Check payment status

### 4. View Analytics (Admin Only)
- Login with admin account
- Navigate to `/admin-analytics/`
- View daily/weekly/monthly revenue
- See popular movies and peak hours

---

## 📧 Email Setup (Optional)

### Using Gmail

1. Go to: https://myaccount.google.com/apppasswords
2. Generate app password (16 characters)
3. Set environment variable (Windows PowerShell):

```powershell
$env:EMAIL_HOST_USER = "your-email@gmail.com"
$env:EMAIL_HOST_PASSWORD = "your-16-char-password"
```

Then run:
```powershell
python manage.py runserver
```

### Without Email

By default, emails are printed to console (no setup needed):

```
[Email Backend: Console]
To: testuser@example.com
Subject: Your Movie Ticket Confirmation - BookMySeat
```

---

## 💾 Reset Everything

```powershell
# Delete database
Remove-Item db.sqlite3 -Force

# Recreate everything
python manage.py migrate
python manage.py createsuperuser
python manage.py generate_test_data --movies 120
```

---

## 🐛 Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'django'"

**Solution**: Activate virtual environment
```powershell
.\venv\Scripts\Activate.ps1
```

### ❌ "Port 8000 already in use"

**Solution**: Use different port
```powershell
python manage.py runserver 8001
```

### ❌ "django.db.utils.OperationalError"

**Solution**: Run migrations
```powershell
python manage.py migrate
```

### ❌ "No such table: movies_movie"

**Solution**: Apply migrations and generate test data
```powershell
python manage.py migrate
python manage.py generate_test_data
```

---

## 📋 What to Test

- [ ] Browse movies on homepage
- [ ] Filter by genre and language
- [ ] Click on movie to see details
- [ ] View theaters and showtimes
- [ ] Login/Register new account
- [ ] Book seats for a movie
- [ ] Check booking in profile
- [ ] Login as admin
- [ ] View admin panel at `/admin/`
- [ ] View analytics at `/admin-analytics/`

---

## 🎯 API Testing (Advanced)

### Test Payment Webhook

```powershell
# Generate signature
$secret = "dev-secret-key-change-in-production"
$body = '{"payment_id":"test","idempotency_key":"test","status":"completed","amount":"10.00"}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$secretBytes = [System.Text.Encoding]::UTF8.GetBytes($secret)

$hmac = New-Object System.Security.Cryptography.HMACSHA256($secretBytes)
$signature = [System.BitConverter]::ToString($hmac.ComputeHash($bytes)).Replace("-", "").ToLower()

# Send webhook
Invoke-WebRequest -Uri "http://127.0.0.1:8000/movies/payments/webhook/" `
  -Method POST `
  -Headers @{"X-Razorpay-Signature" = $signature; "Content-Type" = "application/json"} `
  -Body $body
```

---

## 📊 Database Commands

### Check Database Contents

```powershell
python manage.py shell

# Count movies
>>> from movies.models import Movie
>>> Movie.objects.count()
120

# List all genres
>>> from movies.models import Genre
>>> Genre.objects.all()

# Exit
>>> exit()
```

### Create Test Booking

```powershell
python manage.py shell

>>> from django.contrib.auth.models import User
>>> from movies.models import Movie, Theater, Seat, Booking
>>> from django.utils import timezone

# Get a user
>>> user = User.objects.first()

# Get a movie
>>> movie = Movie.objects.first()

# Get a theater for that movie
>>> theater = movie.theaters.first()

# Get a seat
>>> seat = theater.seats.first()

# Create booking
>>> booking = Booking.objects.create(
...     user=user,
...     seat=seat,
...     movie=movie,
...     theater=theater,
...     amount=10.00
... )

>>> print(f"Booking created: {booking}")
>>> exit()
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `manage.py` | Django management CLI |
| `bookmyseat/settings.py` | Project configuration |
| `movies/models.py` | Database models |
| `movies/views.py` | Business logic |
| `movies/email_tasks.py` | Background email tasks |
| `templates/` | HTML files |

---

## 🚀 Production Deployment

See `README_SETUP.md` for full production setup with:
- PostgreSQL database
- Gunicorn server
- Nginx reverse proxy
- SSL/HTTPS
- Environment variables
- Docker support

---

**Ready to go?** Start with:
```powershell
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

Open browser: `http://127.0.0.1:8000/` 🎉
