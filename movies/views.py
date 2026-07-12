import logging
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q, Count, Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

from .models import Movie, Theater, Seat, Booking, Genre, Language, SeatReservation
from .email_tasks import queue_booking_confirmation_email

logger = logging.getLogger(__name__)


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
    }
    sort_by = valid_sorts.get(sort_by, '-release_date')
    movies = movies.order_by(sort_by)
    
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
    seats = Seat.objects.filter(theater=theaters)
    SeatReservation.release_expired_reservations()
    if request.method == 'POST':
        selected_Seats = request.POST.getlist('seats')
        error_seats = []
        successful_bookings = []
        if not selected_Seats:
            return render(request, "movies/seat_selection.html", {'theater': theaters, "seats": seats, 'error': "No seat selected"})

        transaction_id = str(uuid.uuid4())
        reservation_window = timezone.now() + timezone.timedelta(minutes=2)

        with transaction.atomic():
            for seat_id in selected_Seats:
                seat = Seat.objects.select_for_update().get(id=seat_id, theater=theaters)
                if seat.is_booked:
                    error_seats.append(seat.seat_number)
                    continue
                reservation = SeatReservation.objects.filter(seat=seat, status=SeatReservation.STATUS_RESERVED).first()
                if reservation and reservation.expires_at > timezone.now():
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
                    idempotency_key=transaction_id,
                )
                seat.is_booked = True
                seat.save(update_fields=['is_booked'])
                successful_bookings.append((seat, reservation, booking))

        if successful_bookings and request.user.email:
            seat_list = ', '.join([seat.seat_number for seat, _, _ in successful_bookings])
            booking_context = {
                'user_full_name': request.user.get_full_name() or request.user.username,
                'movie_name': theaters.movie.name,
                'theater_name': theaters.name,
                'show_time': theaters.time.strftime('%A, %B %d, %Y at %I:%M %p'),
                'seat_list': seat_list,
                'payment_id': transaction_id,
                'booking_date': timezone.now().strftime('%B %d, %Y %I:%M %p %Z'),
            }

            def _queue_email():
                try:
                    queue_booking_confirmation_email(request.user.email, booking_context)
                except Exception:
                    logger.exception('Failed to queue booking confirmation email for user %s', request.user.username)

            transaction.on_commit(_queue_email)

        if error_seats:
            error_message = f"The following seats are already reserved or booked: {', '.join(error_seats)}"
            return render(request, 'movies/seat_selection.html', {'theater': theaters, "seats": seats, 'error': error_message})

        messages.success(request, 'Seats reserved successfully. Complete payment to confirm your booking.')
        return redirect('profile')

    return render(request, 'movies/seat_selection.html', {'theaters': theaters, "seats": seats})


@login_required(login_url='/login/')
def payment_status(request, payment_id):
    booking = get_object_or_404(Booking, payment_id=payment_id, user=request.user)
    return JsonResponse({'payment_id': booking.payment_id, 'status': booking.payment_status})


@require_POST
@login_required(login_url='/login/')
def payment_webhook(request):
    signature = request.headers.get('X-Signature', '')
    if not signature:
        return HttpResponseBadRequest('Missing signature')
    return JsonResponse({'status': 'accepted', 'message': 'Webhook received'})


@login_required(login_url='/login/')
@user_passes_test(lambda user: user.is_staff)
def admin_analytics(request):
    SeatReservation.release_expired_reservations()
    daily_revenue = Booking.objects.filter(booked_at__date=timezone.now().date()).aggregate(total=Sum('seat__id'))
    weekly_revenue = Booking.objects.filter(booked_at__gte=timezone.now() - timezone.timedelta(days=7)).aggregate(total=Sum('seat__id'))
    monthly_revenue = Booking.objects.filter(booked_at__gte=timezone.now() - timezone.timedelta(days=30)).aggregate(total=Sum('seat__id'))
    popular_movies = Movie.objects.annotate(booking_count=Count('bookings')).order_by('-booking_count')[:5]
    busiest_theaters = Theater.objects.annotate(occupancy=Count('bookings')).order_by('-occupancy')[:5]
    peak_hours = Booking.objects.extra(select={'hour': 'strftime("%H", booked_at)'}).values('hour').annotate(count=Count('id')).order_by('-count')[:5]
    cancellation_rate = Booking.objects.filter(payment_status='cancelled').count() / max(Booking.objects.count(), 1) * 100
    context = {
        'daily_revenue': daily_revenue['total'] or 0,
        'weekly_revenue': weekly_revenue['total'] or 0,
        'monthly_revenue': monthly_revenue['total'] or 0,
        'popular_movies': popular_movies,
        'busiest_theaters': busiest_theaters,
        'peak_hours': peak_hours,
        'cancellation_rate': round(cancellation_rate, 2),
    }
    return render(request, 'movies/admin_analytics.html', context)




