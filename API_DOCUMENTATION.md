# API Documentation - BookMySeat

Complete API reference for the movie booking system.

## Base URL

```
http://127.0.0.1:8000
```

---

## 🎬 Movies Endpoints

### List All Movies (with Filtering)

**Endpoint:** `GET /movies/`

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `search` | string | Search by title, description, cast | `?search=quantum` |
| `genres` | array | Filter by genre IDs (comma-separated) | `?genres=1,2,3` |
| `languages` | array | Filter by language IDs | `?languages=1,2` |
| `sort` | string | Sort field | `?sort=-release_date` |
| `page` | integer | Page number (25 results per page) | `?page=2` |

**Valid Sort Options:**
- `-release_date` (newest first) ⭐ default
- `release_date` (oldest first)
- `-rating` (highest rated first)
- `rating` (lowest rated first)
- `name` (A-Z)
- `-name` (Z-A)

**Example Requests:**

```bash
# List all movies
GET /movies/

# Search for action movies
GET /movies/?search=action&genres=1

# Filter by language (English)
GET /movies/?languages=1

# Multi-filter with pagination
GET /movies/?genres=1,2&languages=1&sort=-rating&page=1

# Search and sort
GET /movies/?search=quantum&sort=name
```

**Response (200 OK):**

```json
{
  "movies": [
    {
      "id": 1,
      "name": "Quantum Nexus",
      "rating": 8.5,
      "description": "An epic adventure...",
      "release_date": "2024-06-15",
      "cast": "John Smith, Emma Johnson",
      "genres": ["Action", "Sci-Fi"],
      "languages": ["English", "Hindi"],
      "image": "/media/movies/poster1.jpg"
    }
  ],
  "paginator": {
    "count": 120,
    "num_pages": 5,
    "current_page": 1,
    "has_next": true
  },
  "filters": {
    "all_genres": [
      {"id": 1, "name": "Action", "movie_count": 15},
      {"id": 2, "name": "Adventure", "movie_count": 12}
    ],
    "all_languages": [
      {"id": 1, "name": "English", "movie_count": 85},
      {"id": 2, "name": "Hindi", "movie_count": 42}
    ]
  }
}
```

---

## 🏛️ Theater Endpoints

### Get Theaters for a Movie

**Endpoint:** `GET /movies/<movie_id>/theaters`

**Path Parameters:**
- `movie_id` (integer) - ID of the movie

**Example:**

```bash
GET /movies/1/theaters
```

**Response (200 OK):**

```json
{
  "movie": {
    "id": 1,
    "name": "Quantum Nexus",
    "rating": 8.5
  },
  "theaters": [
    {
      "id": 1,
      "name": "Grand Arena - Theater 1",
      "time": "2026-07-15T19:00:00Z",
      "available_seats": 28,
      "total_seats": 30
    },
    {
      "id": 2,
      "name": "Silver Screen - Theater 2",
      "time": "2026-07-15T22:00:00Z",
      "available_seats": 25,
      "total_seats": 30
    }
  ]
}
```

---

## 🎫 Booking Endpoints

### Book Seats

**Endpoint:** `POST /movies/theater/<theater_id>/seats/book/`

**Authentication:** Required (login first)

**Path Parameters:**
- `theater_id` (integer) - Theater ID

**Request Body (Form Data):**

```
seats: [1, 2, 3]  # Seat IDs to book
```

**Example:**

```bash
# Assuming user is logged in
curl -X POST http://127.0.0.1:8000/movies/theater/1/seats/book/ \
  -d "seats=1&seats=2&seats=3" \
  -H "Cookie: sessionid=your-session-id"
```

**Response (201 Created):**

```json
{
  "status": "success",
  "message": "Seats reserved successfully. Complete payment to confirm your booking.",
  "booking": {
    "payment_id": "550e8400-e29b-41d4-a716-446655440000",
    "seats": ["A1", "A2", "A3"],
    "total_amount": 30.00,
    "expires_in_minutes": 2
  }
}
```

**Error Response (400 Bad Request):**

```json
{
  "status": "error",
  "message": "The following seats are already reserved or booked: A1, B2"
}
```

### Get Booking Status

**Endpoint:** `GET /movies/payments/<payment_id>/`

**Authentication:** Required (must be booking owner)

**Path Parameters:**
- `payment_id` (UUID) - Payment/Booking ID

**Example:**

```bash
curl http://127.0.0.1:8000/movies/payments/550e8400-e29b-41d4-a716-446655440000/ \
  -H "Cookie: sessionid=your-session-id"
```

**Response (200 OK):**

```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-07-12T14:30:00Z",
  "expires_at": "2026-07-12T14:32:00Z"
}
```

**Possible Status Values:**
- `pending` - Awaiting payment
- `completed` - Payment successful
- `failed` - Payment failed
- `cancelled` - Booking cancelled
- `expired` - 2-minute hold expired

---

## 💳 Payment Webhook

### Process Payment Status Update

**Endpoint:** `POST /movies/payments/webhook/`

**Authentication:** Webhook signature verification (no user auth needed)

**Headers (Required):**
- `X-Razorpay-Signature` - HMAC-SHA256 of the exact raw Razorpay body
- `X-Razorpay-Event-Id` - event identity when supplied by Razorpay
- `Content-Type: application/json`

This endpoint accepts only native Razorpay event payloads, such as
`payment.captured` and `payment.failed`; it does not accept a browser-selected
status or amount. Configure it in the Razorpay dashboard rather than sending
hand-written test payment updates. See [payment_lifecycle.md](payment_lifecycle.md)
for the server verification, idempotency, and replay protections.

**Response (200 OK - Payment Processed):**

```json
{
  "status": "processed",
  "message": "Payment status updated",
  "booking_id": 42
}
```

**Response (200 OK - Booking Not Found):**

```json
{
  "status": "acknowledged",
  "message": "Booking not found"
}
```

**Response (403 Forbidden - Invalid Signature):**

```json
{
  "error": "Invalid signature"
}
```

**Response (400 Bad Request - Missing Fields):**

```json
{
  "error": "Missing required fields: payment_id, idempotency_key, status"
}
```

---

## 📊 Admin Analytics

### Get Analytics Dashboard Data

**Endpoint:** `GET /movies/admin-analytics/`

**Authentication:** Required (staff/admin only)

**Query Parameters:** None

**Example:**

```bash
curl http://127.0.0.1:8000/movies/admin-analytics/ \
  -H "Cookie: sessionid=your-admin-session-id"
```

**Response (200 OK):**

```json
{
  "daily_revenue": 450.00,
  "weekly_revenue": 2800.50,
  "monthly_revenue": 12340.75,
  "popular_movies": [
    {
      "id": 1,
      "name": "Quantum Nexus",
      "booking_count": 45
    },
    {
      "id": 2,
      "name": "The Last Guardian",
      "booking_count": 38
    }
  ],
  "busiest_theaters": [
    {
      "id": 1,
      "name": "Grand Arena",
      "occupancy": 42
    }
  ],
  "peak_hours": [
    {"hour": "19", "count": 23},
    {"hour": "22", "count": 18}
  ],
  "cancellation_rate": 5.2
}
```

---

## 👤 User Authentication

### Register New Account

**Endpoint:** `POST /register/`

**Request Body (Form Data):**

```
username: john_doe
email: john@example.com
password1: secure_password_123
password2: secure_password_123
```

### Login

**Endpoint:** `POST /login/`

**Request Body (Form Data):**

```
username: john_doe
password: secure_password_123
```

### Logout

**Endpoint:** `GET /logout/`

---

## 🛠️ Admin Interface

### Django Admin Panel

**URL:** `http://127.0.0.1:8000/admin/`

**Authentication:** Username/Password (staff/admin users)

**Manage:**
- Movies, Genres, Languages
- Theaters, Seats
- Bookings, Seat Reservations
- Email Tasks

### Create Movie (via Admin)

1. Login to `/admin/`
2. Click "Movies" section
3. Click "Add Movie"
4. Fill form:
   - Name
   - Rating
   - Cast
   - Description
   - Release Date
   - Genres (multi-select)
   - Languages (multi-select)
5. Click "Save"

---

## 📧 Email Notifications

### Booking Confirmation Email

**Triggered:** When booking is created and payment is confirmed

**Template:** `emails/booking_confirmation.html`

**Variables:**
- `user_full_name`
- `movie_name`
- `theater_name`
- `show_time`
- `seat_list`
- `payment_id`
- `booking_date`

**Plain Text Version:** `emails/booking_confirmation.txt`

### Email Queue Management

**Process pending emails:**

```bash
python manage.py process_email_queue --limit 20
```

**View statistics:**

```bash
python manage.py process_email_queue --stats
```

**Clean old emails:**

```bash
python manage.py process_email_queue --cleanup 30
```

---

## ✋ Rate Limiting & Throttling

Currently no rate limiting is enforced. For production, add:

```python
# In settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

---

## 🔐 Security Headers

All responses include:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

---

## 📝 Error Codes

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | OK | Successful request |
| 201 | Created | Booking created |
| 400 | Bad Request | Missing fields |
| 403 | Forbidden | Invalid signature |
| 404 | Not Found | Movie doesn't exist |
| 500 | Server Error | Database error |

---

## 🧪 Test Scenarios

### Scenario 1: Book Tickets

```bash
# 1. Login
curl -X POST http://127.0.0.1:8000/login/ \
  -d "username=testuser&password=testpass123"

# 2. Get payment ID
PAYMENT_ID="550e8400-e29b-41d4-a716-446655440000"

# 3. Check booking status
curl http://127.0.0.1:8000/movies/payments/$PAYMENT_ID/ \
  -H "Cookie: sessionid=your-session-id"

# 4. Complete the Razorpay test checkout and let Razorpay deliver the
# signed payment.captured webhook. Do not simulate payment success from curl.
```

### Scenario 2: Filter Movies

```bash
# Get action movies in English, sorted by rating
curl "http://127.0.0.1:8000/movies/?genres=1&languages=1&sort=-rating"
```

### Scenario 3: Admin Analytics

```bash
# View revenue and metrics
curl http://127.0.0.1:8000/movies/admin-analytics/ \
  -H "Cookie: sessionid=admin-session-id"
```

---

## 📚 Related Documentation

- See `README_SETUP.md` for setup instructions
- See `QUICKSTART.md` for quick start guide
- See `README.md` for project overview
