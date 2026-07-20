import re
import uuid

from django.db import models
from django.contrib.auth.models import User 
from django.utils import timezone


class SeatReservation(models.Model):
    STATUS_RESERVED = 'reserved'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_RESERVED, 'Reserved'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seat_reservations')
    seat = models.ForeignKey(
    'Seat',
    on_delete=models.CASCADE,
    related_name='reservations'
)
    theater = models.ForeignKey('Theater', on_delete=models.CASCADE, related_name='seat_reservations')
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE, related_name='seat_reservations')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_RESERVED)
    reserved_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    payment_reference = models.CharField(max_length=100, blank=True, default='')
    idempotency_key = models.CharField(max_length=100, blank=True, db_index=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['seat', 'status']),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    @classmethod
    def release_expired_reservations(cls):
        expired = cls.objects.filter(status=cls.STATUS_RESERVED, expires_at__lt=timezone.now())
        updated = 0
        for reservation in expired.select_related('seat'):
            reservation.status = cls.STATUS_EXPIRED
            reservation.save(update_fields=['status'])
            seat = reservation.seat
            booking = Booking.objects.filter(seat=seat, payment_status__in=['pending', 'processing', 'reserved']).first()
            if booking:
                booking.payment_status = 'expired'
                booking.save(update_fields=['payment_status'])
            if seat.is_booked and not booking:
                continue
            seat.is_booked = False
            seat.save(update_fields=['is_booked'])
            updated += 1
        return updated

    def __str__(self):
        return f'{self.user.username} reserved {self.seat.seat_number}'


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]


class Language(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    code = models.CharField(max_length=5, unique=True)  # e.g., 'en', 'hi', 'ta'

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
        ]


class Movie(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    image = models.ImageField(upload_to="movies/")
    rating = models.DecimalField(max_digits=3,decimal_places=1)
    cast = models.TextField()
    description = models.TextField(blank=True,null=True) # optional
    genres = models.ManyToManyField(Genre, related_name='movies')
    languages = models.ManyToManyField(Language, related_name='movies')
    release_date = models.DateField(blank=True, null=True, db_index=True)
    trailer_url = models.URLField(blank=True, default='')
    trailer_embed_url = models.URLField(blank=True, default='')

    def save(self, *args, **kwargs):
        self.trailer_embed_url = self._sanitize_trailer_url(self.trailer_url)
        super().save(*args, **kwargs)

    @staticmethod
    def _sanitize_trailer_url(url):
        if not url:
            return ''
        if not re.match(r'^https?://', url):
            return ''
        youtube_patterns = [
            r'https?://(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]{11})',
            r'https?://(?:www\.)?youtu\.be/([A-Za-z0-9_-]{11})',
            r'https?://(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})',
        ]
        for pattern in youtube_patterns:
            match = re.match(pattern, url)
            if match:
                return f'https://www.youtube-nocookie.com/embed/{match.group(1)}'
        return ''

    @property
    def safe_trailer_embed_url(self):
        return self.trailer_embed_url or ''

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-release_date', '-rating']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['release_date']),
            models.Index(fields=['rating']),
            models.Index(fields=['-release_date']),
        ]


class MovieImage(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='movies/gallery/')
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'Image for {self.movie.name}'

class Theater(models.Model):
    name = models.CharField(max_length=255)
    movie = models.ForeignKey(Movie,on_delete=models.CASCADE,related_name='theaters')
    time= models.DateTimeField()

    def __str__(self):
        return f'{self.name} - {self.movie.name} at {self.time}'

class Seat(models.Model):
    theater = models.ForeignKey(Theater,on_delete=models.CASCADE,related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked=models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['theater', 'is_booked']),
            models.Index(fields=['seat_number']),
        ]

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='bookings')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='bookings')
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='bookings')
    payment_id = models.CharField(max_length=36, db_index=True, default=uuid.uuid4, editable=False)
    booked_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, default='completed', db_index=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text='Booking amount in currency units')
    idempotency_key = models.CharField(max_length=100, blank=True, default='', db_index=True)
    payment_provider = models.CharField(max_length=32, default='razorpay')
    gateway_order_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    gateway_payment_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    payment_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['movie', 'booked_at']),
            models.Index(fields=['theater', 'booked_at']),
        ]

    def __str__(self):
        return f'Booking by {self.user.username} for {self.seat.seat_number} at {self.theater.name}'


class EmailTask(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SENDING = 'sending'
    STATUS_SENT = 'sent'
    STATUS_RETRYING = 'retrying'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENDING, 'Sending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_RETRYING, 'Retrying'),
        (STATUS_FAILED, 'Failed'),
    ]

    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    template_name = models.CharField(max_length=255)
    context = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_error = models.TextField(blank=True, null=True)
    # A confirmation is an at-least-once queue operation. This key makes it
    # effectively-once for a booking even if a payment provider retries.
    deduplication_key = models.CharField(max_length=128, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_attempt_at', 'created_at']
        indexes = [
            models.Index(fields=['status', 'next_attempt_at']),
            models.Index(fields=['recipient']),
        ]

    def __str__(self):
        return f'EmailTask to {self.recipient} [{self.status}]'


class EmailEvent(models.Model):
    """Records SendGrid (or other provider) webhook events related to email tasks."""
    email_task = models.ForeignKey(EmailTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    recipient = models.EmailField(db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True, default='')
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} for {self.recipient} at {self.created_at}'


class PaymentWebhookEvent(models.Model):
    """Minimal, replay-safe audit record for a verified gateway webhook."""
    STATUS_PROCESSED = 'processed'
    STATUS_IGNORED = 'ignored'
    STATUS_FAILED = 'failed'

    provider = models.CharField(max_length=32, default='razorpay')
    event_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=64)
    payload_hash = models.CharField(max_length=64)
    gateway_order_id = models.CharField(max_length=100, blank=True, default='')
    gateway_payment_id = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=16, default=STATUS_PROCESSED)
    failure_reason = models.CharField(max_length=255, blank=True, default='')
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['provider', 'event_id'], name='unique_payment_gateway_event'),
        ]
        indexes = [
            models.Index(fields=['gateway_order_id', 'event_type']),
            models.Index(fields=['gateway_payment_id']),
        ]

    def __str__(self):
        return f'{self.provider}:{self.event_type}:{self.event_id}'
