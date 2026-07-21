import hashlib
import hmac
import json
import logging
import uuid
from decimal import Decimal
import datetime

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q, Count, Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

from .models import Movie, Theater, Seat, Booking, Genre, Language, SeatReservation, EmailEvent, EmailTask, PaymentWebhookEvent
from .email_tasks import queue_booking_confirmation_email
from .payments import (
    PaymentGatewayError,
    amount_to_subunits,
    create_order,
    get_payment,
    verify_checkout_signature,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)


def _enqueue_confirmation_safely(recipient, context):
    """A queue failure must never roll back or delay a confirmed ticket."""
    try:
        queue_booking_confirmation_email(recipient, context)
    except Exception:
        logger.exception('Unable to enqueue confirmation email', extra={'booking_reference': context.get('booking_reference')})


def movie_list(request):
    """
    Optimized movie listing with advanced filtering, pagination, and sorting.
    
    Query Optimization Strategy:
    - Use select_related() for ForeignKey relationships (Theater -> Movie)
    - Use prefetch_related() for ManyToMany (genres, languages, images)
    - Use annotate(Count) for dynamic filter counts without extra queries
    - Use only() to limit fields fetched from DB
    - Use values() for filter count aggregations instead of full object queries
    - Single queryset per request to avoid redundant DB calls
    
    Performance Justification:
    - For catalogs 5000+ movies: indexes on genres, languages, and release_date 
      allow efficient filtering without full-table scans
    - Prefetch_related uses separate queries but caches results, avoiding N+1
    - Annotation counts in one query per filter to show availability dynamically
    - Pagination limits result set size
    """
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    genre_ids = request.GET.getlist('genres')
    language_ids = request.GET.getlist('languages')
    sort_by = request.GET.get('sort', '-release_date')  # default: newest first

    # Start with base queryset and prefetch related objects for efficient rendering
    movies = Movie.objects.only(
        'id', 'name', 'image', 'rating', 'description', 'release_date', 'cast'
    ).prefetch_related(
        'genres', 'languages', 'images', Prefetch('theaters')
    ).distinct()

    # Apply search filter using indexed title/name and full-text-like lookups for other text fields
    if search_query:
        movies = movies.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(cast__icontains=search_query)
        )

    # Apply multi-select filters: any selected genre OR, any selected language OR, combined together.
    if genre_ids:
        movies = movies.filter(genres__id__in=genre_ids)
    if language_ids:
        movies = movies.filter(languages__id__in=language_ids)

    # Apply sorting with indexed fields
    valid_sorts = {
        'release_date': '-release_date',
        '-release_date': '-release_date',
        'rating': '-rating',
        '-rating': '-rating',
        'name': 'name',
        '-name': '-name',
        '?': '?',
    }
    
    # Use random sorting by default if no sort is specified
    sort_by = request.GET.get('sort', '?')
    sort_field = valid_sorts.get(sort_by, '?')
    
    movies = movies.order_by(sort_field)
    
    # Calculate dynamic filter counts (all genres/languages available after current filters)
    # Use separate queries to get counts - more efficient than GROUP BY
    all_genres = Genre.objects.annotate(
        movie_count=Count('movies', filter=Q(movies__in=movies))
    ).filter(movie_count__gt=0).values('id', 'name', 'movie_count').order_by('name')

    all_languages = Language.objects.annotate(
        movie_count=Count('movies', filter=Q(movies__in=movies))
    ).filter(movie_count__gt=0).values('id', 'name', 'movie_count').order_by('name')

    # Get selected filters for display and client state propagation
    selected_genres = Genre.objects.filter(id__in=genre_ids).values_list('id', 'name')
    selected_languages = Language.objects.filter(id__in=language_ids).values_list('id', 'name')
    selected_genre_ids = [str(gid) for gid in genre_ids]
    selected_language_ids = [str(lid) for lid in language_ids]
    
    # Pagination (25 movies per page for optimal loading)
    page = request.GET.get('page', 1)
    paginator = Paginator(movies, 25)
    
    try:
        movies_page = paginator.page(page)
    except PageNotAnInteger:
        movies_page = paginator.page(1)
    except EmptyPage:
        movies_page = paginator.page(paginator.num_pages)
    
    fallback_posters = [
        'https://images.unsplash.com/photo-1517602302552-471fe67acf66?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1542204165-73f2bd057448?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1517602967131-07e25e9ec964?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1499084732479-de2c02d45fcc?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1518972559570-5bdc6e44313b?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1497032628192-86f99bcd76bc?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1491199629863-83c5388e8328?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1497032205916-ac775f0649ae?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=600&q=80',
        'https://images.unsplash.com/photo-1524985069026-dd778a71c7b4?auto=format&fit=crop&w=600&q=80'
    ]
    offset = (movies_page.number - 1) * paginator.per_page
    movie_items = []
    for idx, movie in enumerate(movies_page):
        if movie.image:
            poster_url = movie.image.url
        else:
            poster_url = fallback_posters[(offset + idx) % len(fallback_posters)]
        movie_items.append({'movie': movie, 'poster': poster_url})

    context = {
        'movies': movies_page,
        'movie_items': movie_items,
        'paginator': paginator,
        'all_genres': all_genres,
        'all_languages': all_languages,
        'selected_genres': dict(selected_genres),
        'selected_languages': dict(selected_languages),
        'selected_genre_ids': selected_genre_ids,
        'selected_language_ids': selected_language_ids,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_count': paginator.count,
    }
    
    return render(request, 'movies/movie_list.html', context)


def theater_list(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    # Optimize: use select_related for single movie fetch
    theater = Theater.objects.select_related('movie').filter(movie=movie)
    return render(request, 'movies/theater_list.html', {'movie': movie, 'theaters': theater})


@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theaters = get_object_or_404(Theater, id=theater_id)
    seats = list(Seat.objects.filter(theater=theaters))
    
    # Sort seats properly: A1, A2, ..., A10 instead of A1, A10, A2
    def seat_sort_key(s):
        row = s.seat_number[0]
        try:
            num = int(s.seat_number[1:])
        except ValueError:
            num = 0
        return (row, num)
        
    seats.sort(key=seat_sort_key)
    
    # Group by row
    seat_rows = {}
    for seat in seats:
        row = seat.seat_number[0]
        if row not in seat_rows:
            seat_rows[row] = []
        seat_rows[row].append(seat)

    SeatReservation.release_expired_reservations()
    if request.method == 'POST':
        selected_Seats = request.POST.getlist('seats')
        error_seats = []
        successful_bookings = []
        if not selected_Seats:
            return render(request, "movies/seat_selection.html", {'theater': theaters, "seat_rows": seat_rows, "seats": seats, 'error': "No seat selected"})

        transaction_id = str(uuid.uuid4())
        reservation_window = timezone.now() + timezone.timedelta(minutes=2)

        with transaction.atomic():
            for seat_id in selected_Seats:
                seat = Seat.objects.select_for_update().get(id=seat_id, theater=theaters)
                if seat.is_booked:
                    error_seats.append(seat.seat_number)
                    continue
                reservation = SeatReservation.objects.filter(
                    seat=seat,
                    status=SeatReservation.STATUS_RESERVED,
                    expires_at__gt=timezone.now(),
                ).first()
                if reservation:
                    error_seats.append(seat.seat_number)
                    continue
                if reservation:
                    reservation.status = SeatReservation.STATUS_CANCELLED
                    reservation.save(update_fields=['status'])
                reservation = SeatReservation.objects.create(
                    user=request.user,
                    seat=seat,
                    theater=theaters,
                    movie=theaters.movie,
                    expires_at=reservation_window,
                    idempotency_key=transaction_id,
                )
                booking = Booking.objects.create(
                    user=request.user,
                    seat=seat,
                    movie=theaters.movie,
                    theater=theaters,
                    payment_id=transaction_id,
                    payment_status='pending',
                    amount=Decimal(str(settings.TICKET_PRICE)),
                    idempotency_key=transaction_id,
                )
                seat.is_booked = True
                seat.save(update_fields=['is_booked'])
                successful_bookings.append((seat, reservation, booking))

        if error_seats:
            error_message = f"The following seats are already reserved or booked: {', '.join(error_seats)}"
            return render(request, 'movies/seat_selection.html', {'theater': theaters, "seat_rows": seat_rows, "seats": seats, 'error': error_message})

        messages.success(request, 'Seats reserved successfully. Please complete payment to confirm your booking.')
        return redirect('payment_checkout', payment_id=transaction_id)

    return render(request, 'movies/seat_selection.html', {'theaters': theaters, "seat_rows": seat_rows, "seats": seats})


def _apply_payment_status(payment_id, idempotency_key, status, gateway_payment_id='', verified_amount=None, amount=None):
    """Apply a provider-verified terminal state exactly once.

    This is deliberately the only function that confirms seats. It takes the
    server's booking reference, never a client-provided amount or status.
    """
    with transaction.atomic():
        bookings = list(Booking.objects.select_for_update().select_related('user', 'movie', 'theater', 'seat').filter(
            payment_id=payment_id, idempotency_key=idempotency_key
        ))
        if not bookings:
            logger.warning('Payment update for unknown booking', extra={'booking_reference': payment_id})
            return None

        # ``amount`` remains an internal-test compatibility alias; web views
        # pass only an amount retrieved from Razorpay.
        verified_amount = verified_amount if verified_amount is not None else amount
        if status == 'completed' and verified_amount is not None:
            expected = sum((item.amount for item in bookings), Decimal('0.00'))
            if Decimal(str(verified_amount)) != expected:
                logger.error('Gateway payment amount mismatch', extra={'booking_reference': payment_id})
                return None

        current_status = bookings[0].payment_status
        if current_status in {'completed', 'confirmed'}:
            return bookings[0]
        if status == 'completed' and current_status not in {'pending', 'processing'}:
            # A seat released after cancellation/expiry must never be reclaimed
            # by a late provider event.
            logger.warning('Ignored late captured payment', extra={'booking_reference': payment_id, 'current_status': current_status})
            return bookings[0]

        if status == 'completed':
            Booking.objects.filter(pk__in=[item.pk for item in bookings]).update(
                payment_status='completed', gateway_payment_id=gateway_payment_id, payment_verified_at=timezone.now()
            )
            SeatReservation.objects.filter(idempotency_key=idempotency_key, status=SeatReservation.STATUS_RESERVED).update(
                status=SeatReservation.STATUS_CONFIRMED
            )
            user_email = bookings[0].user.email
            if user_email:
                context = {
                    'user_full_name': bookings[0].user.get_full_name() or bookings[0].user.username,
                    'movie_name': bookings[0].movie.name,
                    'theater_name': bookings[0].theater.name,
                    'show_time': bookings[0].theater.time.strftime('%A, %B %d, %Y at %I:%M %p'),
                    'seats_list': [item.seat.seat_number for item in bookings],
                    'seat_list': ', '.join(item.seat.seat_number for item in bookings),
                    'payment_id': gateway_payment_id or payment_id,
                    'booking_reference': payment_id,
                    'amount': str(sum((item.amount for item in bookings), Decimal('0.00'))),
                    'booking_date': timezone.now().strftime('%B %d, %Y %I:%M %p %Z'),
                }
                transaction.on_commit(lambda: _enqueue_confirmation_safely(user_email, context))
            logger.info('Payment confirmed', extra={'booking_reference': payment_id, 'gateway_payment_id': gateway_payment_id})
            return bookings[0]

        if status in {'failed', 'cancelled', 'timeout'}:
            Booking.objects.filter(pk__in=[item.pk for item in bookings]).update(payment_status=status)
            SeatReservation.objects.filter(idempotency_key=idempotency_key, status=SeatReservation.STATUS_RESERVED).update(
                status=SeatReservation.STATUS_CANCELLED
            )
            Seat.objects.filter(pk__in=[item.seat_id for item in bookings]).update(is_booked=False)
            logger.info('Payment closed without confirmation', extra={'booking_reference': payment_id, 'status': status})
            return bookings[0]
    return None


def _get_or_create_gateway_order(payment_id, total_amount):
    """Serialize order creation so duplicate checkout requests share one order."""
    with transaction.atomic():
        bookings = Booking.objects.select_for_update().filter(payment_id=payment_id)
        booking = bookings.first()
        if not booking:
            raise PaymentGatewayError('Invalid payment session.')
        if booking.gateway_order_id:
            return booking.gateway_order_id
        order = create_order(payment_id, total_amount, settings.PAYMENT_CURRENCY)
        order_id = order.get('id')
        if not order_id:
            raise PaymentGatewayError('The payment provider returned an invalid order.')
        bookings.update(gateway_order_id=order_id, payment_provider='razorpay', payment_status='processing')
        return order_id


@login_required(login_url='/login/')
def payment_status(request, payment_id):
    booking = get_object_or_404(Booking, payment_id=payment_id, user=request.user)
    return JsonResponse({
        'payment_id': booking.payment_id,
        'status': booking.payment_status,
        'amount': str(booking.amount),
    })


@login_required(login_url='/login/')
def payment_checkout(request, payment_id):
    bookings = Booking.objects.filter(payment_id=payment_id, user=request.user).select_related('movie', 'theater', 'seat')
    if not bookings.exists():
        return HttpResponseBadRequest('Invalid payment session')

    total_amount = bookings.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    booking = bookings.first()

    gateway_error = None
    if booking.payment_status in {'pending', 'processing'} and not booking.gateway_order_id:
        try:
            booking.gateway_order_id = _get_or_create_gateway_order(payment_id, total_amount)
            booking.payment_status = 'processing'
        except PaymentGatewayError as exc:
            logger.warning('Unable to create payment order: %s', exc, exc_info=True, extra={'booking_reference': payment_id})
            gateway_error = 'Unable to start payment right now. Your seats remain reserved; please try again.'

    return render(request, 'movies/payment_checkout.html', {
        'booking': booking,
        'bookings': bookings,
        'total_amount': total_amount,
        'gateway_error': gateway_error,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'payment_amount_subunits': amount_to_subunits(total_amount),
        'payment_currency': settings.PAYMENT_CURRENCY,
    })


@login_required(login_url='/login/')
@require_POST
def confirm_payment(request):
    """Verify a Checkout callback, then fetch the payment from Razorpay.

    The callback is only a prompt to verify: it is never accepted as proof of
    payment. Webhooks remain the independent source of eventual confirmation.
    """
    try:
        data = json.loads(request.body.decode('utf-8')) if request.content_type == 'application/json' else request.POST
        booking_reference = data.get('booking_reference', '')
        order_id = data.get('razorpay_order_id', '')
        gateway_payment_id = data.get('razorpay_payment_id', '')
        signature = data.get('razorpay_signature', '')
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid confirmation payload')

    booking = Booking.objects.filter(payment_id=booking_reference, user=request.user, gateway_order_id=order_id).first()
    if not booking or not verify_checkout_signature(order_id, gateway_payment_id, signature):
        logger.warning('Rejected client payment confirmation', extra={'booking_reference': booking_reference})
        return HttpResponseBadRequest('Payment verification failed')
    try:
        gateway_payment = get_payment(gateway_payment_id)
    except PaymentGatewayError:
        return JsonResponse({'status': 'pending', 'message': 'Verification is pending; we will confirm from the provider webhook.'}, status=202)

    expected_amount = amount_to_subunits(Booking.objects.filter(payment_id=booking_reference).aggregate(total=Sum('amount'))['total'])
    if (
        gateway_payment.get('id') != gateway_payment_id
        or gateway_payment.get('order_id') != order_id
        or gateway_payment.get('status') != 'captured'
        or gateway_payment.get('amount') != expected_amount
    ):
        return JsonResponse({'status': 'pending', 'message': 'Payment has not been captured yet.'}, status=202)

    _apply_payment_status(
        booking_reference, booking.idempotency_key, 'completed', gateway_payment_id,
        Decimal(gateway_payment['amount']) / Decimal('100'),
    )
    return JsonResponse({'status': 'completed'})


@csrf_exempt
def payment_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    raw_body = request.body
    try:
        if not verify_webhook_signature(raw_body, request.headers.get('X-Razorpay-Signature', '')):
            logger.warning('Rejected payment webhook with invalid signature')
            return HttpResponseBadRequest('Invalid signature')
        payload = json.loads(raw_body.decode('utf-8'))
    except (PaymentGatewayError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid webhook')

    event_type = payload.get('event', '')
    payment = payload.get('payload', {}).get('payment', {}).get('entity', {})
    order_id = payment.get('order_id', '')
    gateway_payment_id = payment.get('id', '')
    event_id = request.headers.get('X-Razorpay-Event-Id') or hashlib.sha256(raw_body).hexdigest()
    try:
        event, created = PaymentWebhookEvent.objects.get_or_create(
            provider='razorpay', event_id=event_id,
            defaults={
                'event_type': event_type, 'payload_hash': hashlib.sha256(raw_body).hexdigest(),
                'gateway_order_id': order_id, 'gateway_payment_id': gateway_payment_id,
            },
        )
    except IntegrityError:
        return JsonResponse({'status': 'duplicate'})
    if not created:
        return JsonResponse({'status': 'duplicate'})

    booking = Booking.objects.filter(gateway_order_id=order_id).first()
    if not booking:
        event.status = PaymentWebhookEvent.STATUS_IGNORED
        event.failure_reason = 'Unknown order'
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'failure_reason', 'processed_at'])
        return JsonResponse({'status': 'ignored'})

    status = 'completed' if event_type == 'payment.captured' and payment.get('status') == 'captured' else None
    if event_type in {'payment.failed', 'payment.cancelled'}:
        status = 'failed' if event_type == 'payment.failed' else 'cancelled'
    if not status:
        event.status = PaymentWebhookEvent.STATUS_IGNORED
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'processed_at'])
        return JsonResponse({'status': 'ignored'})

    verified_amount = Decimal(payment.get('amount', 0)) / Decimal('100') if status == 'completed' else None
    result = _apply_payment_status(booking.payment_id, booking.idempotency_key, status, gateway_payment_id, verified_amount)
    event.status = PaymentWebhookEvent.STATUS_PROCESSED if result else PaymentWebhookEvent.STATUS_FAILED
    event.failure_reason = '' if result else 'Payment could not be applied'
    event.processed_at = timezone.now()
    event.save(update_fields=['status', 'failure_reason', 'processed_at'])
    return JsonResponse({'status': event.status})


@csrf_exempt
def sendgrid_events_webhook(request):
    """Receive SendGrid event webhooks and persist EmailEvent records.

    This endpoint will accept the SendGrid event array, create `EmailEvent`
    records, and heuristically associate them with `EmailTask` entries.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    # Delivery events can alter queue status, so do not accept unauthenticated
    # requests. A provider proxy may supply this HMAC header if native event
    # signing is not enabled in the transactional-email account.
    webhook_secret = getattr(settings, 'EMAIL_EVENTS_WEBHOOK_SECRET', '')
    received_signature = request.headers.get('X-Email-Events-Signature', '')
    if not webhook_secret or not received_signature:
        logger.warning('Rejected unauthenticated email event webhook')
        return HttpResponse(status=403)
    expected_signature = hmac.new(webhook_secret.encode('utf-8'), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, received_signature):
        logger.warning('Rejected email event webhook with invalid signature')
        return HttpResponse(status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        logger.exception('Invalid JSON in sendgrid webhook')
        return HttpResponse(status=400)

    events = payload if isinstance(payload, list) else [payload]
    created = 0
    for ev in events:
        recipient = ev.get('email') or ev.get('recipient') or ''
        event_type = ev.get('event') or ev.get('type') or 'unknown'
        ts = ev.get('timestamp')
        timestamp = None
        if ts:
            try:
                timestamp = datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc)
            except Exception:
                try:
                    timestamp = parse_datetime(ts)
                    if timestamp and timestamp.tzinfo is None:
                        timestamp = make_aware(timestamp)
                except Exception:
                    timestamp = None

        # Heuristic association: most recent EmailTask for recipient
        email_task = None
        if recipient:
            email_task = EmailTask.objects.filter(recipient=recipient).order_by('-created_at').first()

        ev_obj = EmailEvent.objects.create(
            email_task=email_task,
            recipient=recipient,
            event_type=event_type,
            timestamp=timestamp,
            reason=ev.get('reason', '') or ev.get('response', '') or '',
            # Keep a non-sensitive correlation identifier, not the whole
            # provider event (which may contain tracking and customer data).
            raw={'event_id': ev.get('sg_event_id', '')},
        )
        created += 1

        # Update EmailTask status based on event
        if email_task:
            if event_type in {'bounce', 'blocked', 'dropped', 'deferred'}:
                email_task.status = EmailTask.STATUS_FAILED
                email_task.last_error = ev.get('reason', '') or str(ev)
                email_task.save(update_fields=['status', 'last_error', 'updated_at'])
            elif event_type in {'delivered', 'processed'}:
                email_task.status = EmailTask.STATUS_SENT
                email_task.last_error = ''
                email_task.save(update_fields=['status', 'last_error', 'updated_at'])

    return HttpResponse(f'OK: {created}')


@login_required(login_url='/login/')
@user_passes_test(lambda user: user.is_staff)
def admin_analytics(request):
    SeatReservation.release_expired_reservations()
    
    # Try to fetch cached analytics data to satisfy aggregation/performance caching spec
    cache_key = 'admin_analytics_data'
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        daily_revenue = Booking.objects.filter(payment_status='completed', booked_at__date=timezone.now().date()).aggregate(total=Sum('amount'))
        weekly_revenue = Booking.objects.filter(payment_status='completed', booked_at__gte=timezone.now() - timezone.timedelta(days=7)).aggregate(total=Sum('amount'))
        monthly_revenue = Booking.objects.filter(payment_status='completed', booked_at__gte=timezone.now() - timezone.timedelta(days=30)).aggregate(total=Sum('amount'))
        popular_movies = list(Movie.objects.annotate(booking_count=Count('bookings', filter=Q(bookings__payment_status='completed'))).order_by('-booking_count')[:5])
        busiest_theaters = list(Theater.objects.annotate(occupancy=Count('bookings', filter=Q(bookings__payment_status='completed'))).order_by('-occupancy')[:5])
        from django.db.models.functions import ExtractHour
        peak_hours = list(Booking.objects.filter(payment_status='completed').annotate(hour=ExtractHour('booked_at')).values('hour').annotate(count=Count('id')).order_by('-count')[:5])
        unbooked_movies = list(Movie.objects.annotate(booking_count=Count('bookings', filter=Q(bookings__payment_status='completed'))).filter(booking_count=0)[:10])
        
        total_bookings = Booking.objects.count()
        cancelled_bookings = Booking.objects.filter(payment_status='cancelled').count()
        cancellation_rate = (cancelled_bookings / max(total_bookings, 1)) * 100
        
        cached_data = {
            'daily_revenue': daily_revenue['total'] or 0.00,
            'weekly_revenue': weekly_revenue['total'] or 0.00,
            'monthly_revenue': monthly_revenue['total'] or 0.00,
            'popular_movies': popular_movies,
            'busiest_theaters': busiest_theaters,
            'peak_hours': peak_hours,
            'unbooked_movies': unbooked_movies,
            'cancellation_rate': round(cancellation_rate, 2),
        }
        # Cache for 60 seconds (1 minute) to optimize queries on frequent admin reloads
        cache.set(cache_key, cached_data, 60)
        
    return render(request, 'movies/admin_analytics.html', cached_data)

def movies_autocomplete(request):
    from django.http import JsonResponse
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'movies': []})
    movies = Movie.objects.filter(name__icontains=query).only('id', 'name', 'image')[:6]
    results = []
    for m in movies:
        results.append({
            'id': m.id,
            'name': m.name,
            'image': m.image.url if m.image else ''
        })
    return JsonResponse({'movies': results})

def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def error_500(request):
    return render(request, 'errors/500.html', status=500)

@login_required
def cancel_booking(request, booking_id):
    from django.contrib import messages
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.payment_status in ['completed', 'pending']:
        seat = booking.seat
        seat.is_booked = False
        seat.save(update_fields=['is_booked'])
        
        from .models import SeatReservation
        SeatReservation.objects.filter(seat=seat, status='reserved').update(status='expired')
        
        booking.payment_status = 'cancelled'
        booking.save(update_fields=['payment_status'])
        messages.success(request, f"Booking for {booking.movie.name} has been successfully cancelled.")
    else:
        messages.error(request, "This booking cannot be cancelled.")
        
    return redirect('profile')
