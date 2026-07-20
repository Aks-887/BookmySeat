# Payment lifecycle and security

## Lifecycle

1. Seat selection creates a two-minute `SeatReservation` and a `Booking` in `pending` state. Each booking group receives a random internal `payment_id` / idempotency key.
2. Checkout creates one Razorpay Order from the server using the configured secret. The order amount is calculated from database values, in paise; browser-supplied totals are never used. Its ID is saved against every booking in the group.
3. Razorpay Checkout receives only `RAZORPAY_KEY_ID` and the order ID. It never receives the secret or an application SMTP/payment credential.
4. A Checkout callback posts its order ID, payment ID, and Razorpay signature to `/movies/payments/confirm/`. The server verifies that signature and then retrieves the payment from Razorpay. Only a matching, captured payment for the expected order and amount can confirm seats.
5. Razorpay's `payment.captured` webhook repeats the confirmation path independently. `payment.failed` and cancellation events release the still-reserved seats. Reservation expiry also closes pending or processing bookings as `expired`.
6. Confirmation writes the booking state and reservation state atomically. After commit, it places exactly one confirmation-email job in the database queue. A worker (`python manage.py process_email_queue`) renders the HTML/text templates and retries transient failures with backoff.

## Idempotency, replay, and fraud controls

- Every reservation group uses a random server-generated idempotency key. Completion takes row locks, so duplicate Checkout callbacks or concurrent webhooks cannot double-book seats.
- Each verified webhook is inserted into `PaymentWebhookEvent` under a unique `(provider, event_id)` constraint. Razorpay's event ID is used when supplied; otherwise the SHA-256 payload digest is the idempotency identity. Duplicate events are acknowledged without applying state again.
- Webhook HMAC is computed over the exact raw request body with `RAZORPAY_KEY_SECRET` and checked using constant-time comparison. Invalid signatures are rejected before JSON is trusted or persisted.
- A browser callback is not payment proof. The server checks Razorpay's callback signature *and* fetches the payment over authenticated HTTPS, validating payment ID, order ID, captured state, and amount.
- Webhook records contain only event identifiers, hashes, status, and gateway identifiers—not the complete provider payload, card data, or secrets. Email queue contexts recursively redact credential-like fields.
- Gateway/network timeouts leave the booking pending until a signed webhook, server recheck, or reservation expiry resolves it. No optimistic success state is returned.

## Operational setup

Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `DJANGO_SECRET_KEY`, and SMTP or SendGrid/SES environment variables in the deployment secret store. Configure Razorpay to POST events to `/movies/payments/webhook/` and subscribe at least to `payment.captured` and `payment.failed`. Run the email worker continuously (the provided service definition is suitable) and alert on `EmailTask.status=failed` and `PaymentWebhookEvent.status=failed`.
