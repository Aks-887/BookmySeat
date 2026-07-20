from django.test import TransactionTestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.test import override_settings
import uuid

from movies import views
from movies.models import (
    EmailTask, Movie, Theater, Seat, Booking, SeatReservation
)
from movies.email_tasks import queue_booking_confirmation_email
from movies.payments import verify_checkout_signature, verify_webhook_signature


class EmailQueueTestCase(TransactionTestCase):
    reset_sequences = True

    def test_post_payment_enqueues_email_task(self):
        # Create minimal objects required
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass')
        movie = Movie.objects.create(name='Test Movie', image='movies/dummy.jpg', rating=5.0, cast='cast', release_date=timezone.now().date())
        theater = Theater.objects.create(name='Hall 1', movie=movie, time=timezone.now() + timezone.timedelta(days=1))
        seat = Seat.objects.create(theater=theater, seat_number='A1')

        idempotency_key = str(uuid.uuid4())
        payment_id = str(uuid.uuid4())

        # Create reservation and booking
        reservation = SeatReservation.objects.create(
            user=user,
            seat=seat,
            theater=theater,
            movie=movie,
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
            idempotency_key=idempotency_key,
        )

        booking = Booking.objects.create(
            user=user,
            seat=seat,
            movie=movie,
            theater=theater,
            payment_id=payment_id,
            payment_status='pending',
            idempotency_key=idempotency_key,
            amount=10.00,
        )

        # Apply payment status -> should commit and schedule an EmailTask
        result = views._apply_payment_status(payment_id, idempotency_key, 'completed', amount=10.00)
        self.assertIsNotNone(result)

        # After the transaction, an EmailTask should be queued for the user's email
        exists = EmailTask.objects.filter(recipient=user.email, template_name='emails/booking_confirmation.html').exists()
        self.assertTrue(exists, 'EmailTask was not queued after payment completion')

    def test_confirmation_queue_deduplicates_provider_retries(self):
        context = {'booking_reference': 'booking-123', 'payment_id': 'pay_123'}
        first = queue_booking_confirmation_email('test@example.com', context)
        second = queue_booking_confirmation_email('test@example.com', context)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(EmailTask.objects.filter(deduplication_key='booking-confirmation:booking-123').count(), 1)


@override_settings(RAZORPAY_KEY_ID='rzp_test_key', RAZORPAY_KEY_SECRET='test-secret')
class RazorpaySignatureTests(TransactionTestCase):
    def test_checkout_and_webhook_signatures_are_constant_time_checked(self):
        import hashlib
        import hmac

        checkout = hmac.new(b'test-secret', b'order_123|pay_123', hashlib.sha256).hexdigest()
        body = b'{"event":"payment.captured"}'
        webhook = hmac.new(b'test-secret', body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_checkout_signature('order_123', 'pay_123', checkout))
        self.assertTrue(verify_webhook_signature(body, webhook))
        self.assertFalse(verify_checkout_signature('order_123', 'pay_123', 'incorrect'))
        self.assertFalse(verify_webhook_signature(body, 'incorrect'))
