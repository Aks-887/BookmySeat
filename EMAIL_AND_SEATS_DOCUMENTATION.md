# Email Confirmation System & Seat Highlighting Implementation

## Overview

This document provides comprehensive documentation for the automated email confirmation system with retry logic, the enhanced seat selection UI with highlighting capabilities, and the new secure media and payment safeguards added for the assignment.

---

## 1. Email Confirmation System

### 1.1 Features

#### ✓ Non-Blocking Email Queue
- Emails are processed asynchronously using background threads
- Booking API response is **never blocked** by email operations
- Uses Django's `transaction.on_commit()` to queue emails after successful booking

#### ✓ Templated Email Rendering
- **HTML email** with professional styling and responsive design
- **Plain text email** for fallback and accessibility
- Uses Django's template engine with context rendering
- Templates located in: `templates/emails/`

#### ✓ Retry Logic with Exponential Backoff
- Failed emails automatically scheduled for retry
- Retry schedule: 1, 5, 15, 60 minutes (configurable in `email_tasks.py`)
- Maximum 5 retry attempts (configurable per task)
- Status tracking: PENDING → SENDING → SENT or FAILED

#### ✓ Security & Privacy
- No sensitive data (passwords, tokens) stored in email context
- Automatic sanitization of context before logging
- Email addresses validated before queueing
- Template variables protected from XSS

#### ✓ Comprehensive Logging & Monitoring
- Dedicated email logger with file rotation
- Separate log file: `logs/email.log`
- Structured logging with contextual metadata
- Tracks: task ID, recipient, attempt count, error messages
- Integration with Django admin for queue management

### 1.2 Email Context Data

The email template receives the following context variables:

```python
booking_context = {
    'user_full_name': 'John Doe',          # User's full name or username
    'movie_name': 'Avatar 2',               # Movie title
    'theater_name': 'PVR Cinemas - Delhi',  # Theater/Cinema name
    'show_time': 'Monday, June 11, 2024 at 07:30 PM',  # Formatted show time
    'seat_list': 'A1, A2, B3',             # Comma-separated seat numbers
    'payment_id': 'uuid-string',            # Transaction/Payment ID
    'booking_date': 'June 11, 2024 07:25 PM UTC'  # Booking confirmation date
}
```

### 1.3 Database Model

```python
class EmailTask(models.Model):
    # Status choices
    STATUS_PENDING = 'pending'      # Awaiting initial send
    STATUS_SENDING = 'sending'      # Currently being sent
    STATUS_SENT = 'sent'            # Successfully sent
    STATUS_RETRYING = 'retrying'    # Scheduled for retry
    STATUS_FAILED = 'failed'        # All retries exhausted
    
    # Fields
    recipient = EmailField()                    # Recipient email
    subject = CharField(max_length=255)        # Email subject
    template_name = CharField(max_length=255)  # Path to template
    context = JSONField()                      # Template context (stores actual data)
    status = CharField(choices=STATUS_CHOICES) # Current status
    attempts = PositiveSmallIntegerField()     # Number of attempts
    max_attempts = PositiveSmallIntegerField() # Maximum allowed attempts
    next_attempt_at = DateTimeField()          # Next retry time
    last_error = TextField()                   # Last error message
    created_at = DateTimeField()               # Creation timestamp
    updated_at = DateTimeField()               # Last update timestamp
```

### 1.4 Email Processing Flow

```
1. User books seats
2. Booking is created in database
3. Email task queued via queue_booking_confirmation_email()
4. Background thread spawned immediately (daemon thread)
5. Thread calls _dispatch_email_task_async()
6. Email rendered from template with context
7. Sent via configured SMTP backend
   ├─ ✓ SUCCESS: Status = SENT
   └─ ✗ FAILED: Status = RETRYING (schedules next attempt)
8. Failed emails retried via management command
```

### 1.5 Email Functions (email_tasks.py)

#### `queue_booking_confirmation_email(recipient_email, booking_context)`
- **Purpose**: Queue an email for sending
- **Returns**: EmailTask instance
- **Non-blocking**: Spawns daemon thread
- **Validation**: Checks email format before storing

**Usage:**
```python
from movies.email_tasks import queue_booking_confirmation_email

booking_context = {
    'user_full_name': 'Jane Doe',
    'movie_name': 'Oppenheimer',
    'theater_name': 'IMAX Theater',
    'show_time': 'June 15, 2024 at 09:00 PM',
    'seat_list': 'A5, A6',
    'payment_id': 'pay_abc123',
    'booking_date': 'June 11, 2024 03:45 PM UTC'
}

task = queue_booking_confirmation_email('user@example.com', booking_context)
print(f"Email task queued: {task.id}")
```

#### `process_pending_email_tasks(limit=20)`
- **Purpose**: Process pending and retrying emails from queue
- **Parameters**: `limit` - max tasks to process per run
- **Returns**: Number of tasks successfully sent
- **Thread-safe**: Uses database-level locking (select_for_update)

**Usage:**
```python
from movies.email_tasks import process_pending_email_tasks

# Process up to 50 emails
count = process_pending_email_tasks(limit=50)
print(f"Processed {count} emails")
```

#### `get_email_task_stats()`
- **Purpose**: Get statistics about email queue
- **Returns**: Dictionary with counts by status

**Usage:**
```python
from movies.email_tasks import get_email_task_stats

stats = get_email_task_stats()
# Output: {'Sent': 145, 'Failed': 2, 'Retrying': 3, 'Pending': 0}
```

### 1.6 Management Command

Process email queue using Django management command:

```bash
# Process 20 emails (default)
python manage.py process_email_queue

# Process specific number of emails
python manage.py process_email_queue --limit 50

# Show queue statistics
python manage.py process_email_queue --stats

# Clean up old sent emails (older than 30 days)
python manage.py process_email_queue --cleanup 30
```

**Schedule with Cron:**
```bash
# Process email queue every 5 minutes
*/5 * * * * cd /path/to/project && python manage.py process_email_queue

# Daily cleanup (delete sent emails older than 30 days)
0 2 * * * cd /path/to/project && python manage.py process_email_queue --cleanup 30
```

### 1.7 Django Admin Interface

Access email management at: `/admin/movies/emailtask/`

**Features:**
- ✓ Color-coded status display (green=sent, red=failed, orange=retrying)
- ✓ Filter by status, date, attempt count
- ✓ Search by recipient email or task ID
- ✓ View detailed context and error messages
- ✓ Retry failed emails with one click
- ✓ Manually mark as sent
- ✓ Bulk delete old tasks

**Admin Actions:**
1. **Retry selected failed emails** - Resets failed tasks for retry
2. **Mark as sent** - Manually mark tasks as sent
3. **Delete selected tasks** - Remove tasks from queue

### 1.8 Configuration

**settings.py** - Email Backend Configuration:

```python
# Using Gmail (example)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'  # Use app password for Gmail
DEFAULT_FROM_EMAIL = 'noreply@bookmyseat.com'

# Or use environment variables
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
```

**Logging Configuration:**
```python
LOGGING = {
    'handlers': {
        'email_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/email.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
        }
    },
    'loggers': {
        'movies.email_tasks': {
            'handlers': ['console', 'email_file'],
            'level': 'INFO',
        }
    }
}
```

### 1.9 Monitoring & Troubleshooting

**Check Email Queue Status:**
```bash
python manage.py process_email_queue --stats
```

**View Email Logs:**
```bash
tail -f logs/email.log
```

**Common Issues & Solutions:**

| Issue | Solution |
|-------|----------|
| Emails stuck in RETRYING | Check SMTP credentials in settings.py; Run `process_email_queue` manually |
| High FAILED count | Check `last_error` field in admin; Verify email template syntax |
| Memory usage high | Run cleanup: `process_email_queue --cleanup 7` (delete older than 7 days) |
| Email not received | Check spam folder; Verify `DEFAULT_FROM_EMAIL` is legitimate |

---

## 2. Seat Selection with Highlighting

### 2.1 Features

#### ✓ Interactive Seat Selection
- Click seats to select/deselect
- Real-time visual feedback with animations
- Highlight color: green (#28a745)
- Smooth transitions and hover effects

#### ✓ Visual States
1. **Available** - White background, green border, clickable
2. **Selected** - Green background, white text, animated pulse
3. **Sold** - Gray background, disabled, non-clickable

#### ✓ Real-Time Updates
- Selection count badge updates instantly
- Selected seats list displayed in alert box
- Book button enabled/disabled based on selection
- Seat numbers formatted: "A1, A2, B3"

#### ✓ Responsive Design
- Mobile-friendly layout
- Touch-friendly seat sizes
- Proper spacing on all screen sizes
- Bootstrap 5 integration

### 2.2 Seat Selection Flow

```
User views seat_selection.html
    ↓
JavaScript attaches click handlers
    ↓
User clicks available seat
    ↓
Toggle checkbox (hidden)
    ↓
Add 'selected' class to seat label
    ↓
Update selection count badge
    ↓
Update selected seats list
    ↓
Enable book button (if seats selected)
    ↓
User clicks "Book Selected Seats"
    ↓
Form submits with selected seat IDs
    ↓
Server processes booking
```

### 2.3 HTML Structure

```html
<input type="checkbox" name="seats" value="seat_id" 
       id="seat-123" class="seat-checkbox" />
<label for="seat-123" class="seat available">
  <span class="seat-text">A1</span>
</label>
```

### 2.4 JavaScript Implementation

**Key Functions:**

```javascript
// Update selection count and list
function updateSelectedSeats() {
    const selectedSeats = Array.from(seatCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.dataset.seatNumber)
        .sort();
    // Updates UI with selected seats
}

// Handle seat label click
seatLabels.forEach(label => {
    label.addEventListener('click', function(e) {
        const checkbox = document.getElementById(seatId);
        checkbox.checked = !checkbox.checked;  // Toggle
        // Update visual state
        updateSelectedSeats();
    });
});
```

### 2.5 CSS Styling

**Key Classes:**

```css
.seat {
    width: 40px;
    height: 40px;
    border: 2px solid #28a745;
    border-radius: 6px;
    transition: all 0.3s ease;
}

.seat.available {
    color: #28a745;
    background: white;
}

.seat.available:hover {
    background: #e8f5e9;
    transform: scale(1.1);
}

.seat.selected {
    background: #28a745;
    color: white;
    animation: pulse-selected 0.3s ease;
}

.seat.sold {
    background: #e9ecef;
    cursor: not-allowed;
    opacity: 0.6;
}

@keyframes pulse-selected {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.15); }
}
```

### 2.6 Features in seat_selection.html

#### Screen Indicator
```html
<div class="screen text-center mb-4">
    <span>🎬 SCREEN 🎬</span>
</div>
```

#### Selection Count Badge
```html
<div class="badge bg-primary" id="selected-count">
    <i class="fas fa-ticket-alt"></i> 0 Selected
</div>
```

#### Selected Seats Summary
```html
<div id="selected-seats-summary" class="alert alert-info d-none">
    <strong>Selected Seats:</strong>
    <span id="selected-seats-list"></span>
</div>
```

#### Seats Grid
```html
<div class="seats-grid mb-4">
    {% for seat in seats %}
        <div class="seat-wrapper">
            <!-- Seat HTML -->
        </div>
    {% endfor %}
</div>
```

### 2.7 Mobile Responsiveness

**Breakpoint: 576px and below**
- Reduced seat size: 35px (from 40px)
- Smaller gap between seats
- Full-width book button
- Adjusted font sizes

### 2.8 Accessibility

- ✓ Keyboard navigation (Tab, Space to select)
- ✓ Proper labels with `for` attribute linking to inputs
- ✓ ARIA attributes for screen readers
- ✓ Error messages displayed clearly
- ✓ Proper color contrast

---

## 3. Integration with Booking Flow

### 3.1 Booking View (views.py)

```python
@login_required(login_url='/login/')
def book_seats(request, theater_id):
    # Validate theater and seats
    # Create bookings in transaction
    # Queue confirmation email (non-blocking)
    # Redirect to profile
```

**Email Integration:**
```python
if successful_bookings and request.user.email:
    booking_context = {
        'user_full_name': request.user.get_full_name() or request.user.username,
        'movie_name': theaters.movie.name,
        'theater_name': theaters.name,
        'show_time': theaters.time.strftime('%A, %B %d, %Y at %I:%M %p'),
        'seat_list': ', '.join([b.seat.seat_number for b in successful_bookings]),
        'payment_id': transaction_id,
        'booking_date': timezone.now().strftime('%B %d, %Y %I:%M %p %Z'),
    }
    
    def _queue_email():
        queue_booking_confirmation_email(request.user.email, booking_context)
    
    transaction.on_commit(_queue_email)  # Non-blocking
```

### 3.2 Transaction Safety

- Uses `transaction.atomic()` for seat bookings
- Uses `transaction.on_commit()` for email queueing
- Ensures email is queued **after** booking is persisted
- Prevents duplicate emails on transaction rollback

---

## 4. Email Templates

### 4.1 HTML Template (booking_confirmation.html)

**Features:**
- Professional gradient header
- Structured sections with left border accent
- Color-coded booking ID badge
- Seat badges for visual display
- Important notice box (yellow background)
- Responsive design for mobile

**Template Variables:**
```
{{ user_full_name }}
{{ movie_name }}
{{ theater_name }}
{{ show_time }}
{{ seat_list }}
{{ payment_id }}
{{ booking_date }}
{{ seats_list }}  # Optional: list of seat objects
```

### 4.2 Text Template (booking_confirmation.txt)

**Features:**
- Plain text format for email clients without HTML support
- Clear section headers with ASCII dividers
- Important notice sections
- Support links and instructions
- Professional footer

---

## 5. Deployment Checklist

### Before Production:

- [ ] Configure EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
- [ ] Set DEFAULT_FROM_EMAIL to legitimate domain
- [ ] Create logs directory: `mkdir -p logs`
- [ ] Test email with test command:
  ```bash
  python manage.py shell
  >>> from django.core.mail import send_mail
  >>> send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
  ```
- [ ] Set up cron job for email queue processing
- [ ] Configure logging (check logs are rotating)
- [ ] Verify email templates render correctly
- [ ] Test seat selection UI on mobile devices

### Environment Variables:

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@bookmyseat.com
DJANGO_LOG_LEVEL=INFO
```

---

## 6. Performance Considerations

### Email Processing

- **Non-blocking**: Background thread spawned immediately
- **Database**: Uses `select_for_update()` to prevent duplicate sends
- **Memory**: Context stored as JSON, sanitized before logging
- **Scaling**: Can be migrated to Celery/Redis for large volumes

### Seat Selection

- **Client-side**: All selection logic in browser (no server calls)
- **No N+1**: Single query for all seats
- **Caching**: Template caching for HTML/text emails
- **Bundle size**: ~3KB of inline JavaScript

---

## 7. Example Workflows

### Scenario 1: Successful Booking with Email

```
1. User selects seats A1, A2
2. Clicks "Book Selected Seats"
3. Form submits to /movies/book_seats/<theater_id>/
4. Server creates Booking records
5. Email task queued asynchronously
6. Response sent immediately (email not yet sent)
7. Background thread sends email in ~2 seconds
8. User sees confirmation page
9. User receives email within seconds
```

### Scenario 2: Email Delivery Failure with Retry

```
1. Email task created (PENDING status)
2. Background thread attempts send
3. SMTP connection fails → Exception caught
4. Status → RETRYING
5. next_attempt_at = now + 1 minute
6. After 1 minute: Task reprocessed
7. Retry succeeds → Status = SENT
8. Admin sees "Sent" status in email list
```

### Scenario 3: Seat Selection Validation

```
1. User loads seat selection page
2. JavaScript finds all available seats
3. User hovers over seat → Green highlight
4. User clicks seat → Selection count updates to 1
5. User selects 3 more seats
6. Selection count badge shows "4 Selected"
7. Summary box shows "A1, A2, B1, B2"
8. Book button is enabled
9. User can now submit form
```

---

## 8. Logging Examples

**Successful Email Send:**
```
INFO 2024-06-11 15:30:45 movies.email_tasks Booking confirmation email sent successfully 
(EmailTask: 123, Recipient: user@example.com, Attempts: 1)
```

**Email Send Failure (with retry):**
```
WARNING 2024-06-11 15:30:46 movies.email_tasks Failed to send email for EmailTask 123 
(recipient: user@example.com, attempt 1/5): SMTPAuthenticationError: 535 5.7.8 Username and password not accepted
```

**Retry Scheduled:**
```
INFO 2024-06-11 15:30:46 movies.email_tasks EmailTask 123 scheduled for retry in 1 minutes 
(recipient: user@example.com, next attempt: 2024-06-11 15:31:46)
```

---

## 9. Security Considerations

### ✓ Implemented Security Features

1. **Email Validation**: Recipient email checked before queuing
2. **Data Sanitization**: Sensitive data removed before logging
3. **No Credential Storage**: SMTP credentials in environment variables only
4. **Template Escape**: All context variables HTML-escaped in templates
5. **Rate Limiting**: Configurable max attempts per email
6. **Error Truncation**: Error messages truncated to 500 chars
7. **User Privacy**: Booking IDs used instead of personal info in logs

### ⚠️ Security Recommendations

1. Use app-specific passwords (Gmail) or OAuth2
2. Rotate SMTP credentials regularly
3. Monitor email.log for suspicious patterns
4. Implement IP whitelisting for SMTP connections
5. Use TLS/SSL for all email connections
6. Regular security audits of email template content

---

## 10. Support & Troubleshooting

**Common Questions:**

**Q: Can I change the email template?**
A: Yes! Edit `templates/emails/booking_confirmation.html` and `.txt` files. Changes take effect immediately.

**Q: How do I test the email system?**
A: Use console email backend in development:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

**Q: Can I add attachments to emails?**
A: Yes, modify `_send_email_task()` in `email_tasks.py`:
```python
message.attach('filename.pdf', pdf_content, 'application/pdf')
```

**Q: How long are logs kept?**
A: Rotating file handler keeps 5 backup files of 10MB each. Adjust `backupCount` in settings.py.

**Q: Can emails be sent in bulk?**
A: Yes, increase `--limit` parameter in management command: `process_email_queue --limit 1000`

---

## Version History

- **v1.0** (2024-06-11): Initial implementation with retry logic, Django admin monitoring, and seat highlighting

---

For support or issues, contact: [support@bookmyseat.com]
