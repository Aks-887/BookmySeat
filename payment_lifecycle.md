# Payment lifecycle and security notes

## Overview
- The booking flow now creates a reservation for two minutes before payment completion.
- A reservation is released automatically when it expires, preventing stale holds from blocking seats indefinitely.
- Payment verification is intentionally server-side and relies on signatures and idempotency keys rather than only client-side callbacks.

## Lifecycle
1. User selects seats and submits the booking form.
2. The server places a temporary reservation using a database transaction and row-level locking.
3. The reservation expires after two minutes if checkout is not completed.
4. A payment webhook endpoint accepts signed provider events and can be extended to confirm or cancel the booking.
5. Idempotency keys prevent duplicate processing when the same payment event or callback arrives more than once.

## Security controls
- Trailer URLs are validated and only allow YouTube embeds; all other URLs are rejected to prevent unsafe script injection.
- The iframe uses the `loading="lazy"` attribute and `referrerpolicy="strict-origin-when-cross-origin"` to reduce network impact.
- Admin analytics access is restricted to staff users only.
- The system uses database transaction locking to avoid race conditions between simultaneous seat selections.
