from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Booking, Movie, Seat, SeatReservation, Theater


class TrailerValidationTests(TestCase):
    def test_valid_youtube_trailer_url_is_converted_to_embed_url(self):
        movie = Movie.objects.create(
            name='Sample Movie',
            image='movies/default.jpg',
            rating=8.5,
            cast='Actor',
            description='Demo',
            trailer_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        )

        self.assertEqual(movie.trailer_embed_url, 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ')

    def test_invalid_trailer_url_returns_none(self):
        movie = Movie.objects.create(
            name='Bad Movie',
            image='movies/default.jpg',
            rating=6.0,
            cast='Actor',
            description='Demo',
            trailer_url='https://example.com/video',
        )

        self.assertEqual(movie.trailer_embed_url, '')


class ReservationExpiryTests(TestCase):
    def test_expired_reservations_are_released(self):
        User = get_user_model()
        user = User.objects.create_user(username='tester', password='secret123')
        movie = Movie.objects.create(
            name='Movie',
            image='movies/default.jpg',
            rating=7.0,
            cast='Actor',
            description='Demo',
        )
        theater = Theater.objects.create(name='Hall A', movie=movie, time='2026-07-01T19:00:00Z')
        seat = Seat.objects.create(theater=theater, seat_number='A1')
        SeatReservation.objects.create(
            user=user,
            seat=seat,
            theater=theater,
            movie=movie,
            expires_at='2020-01-01T00:00:00Z',
            status='reserved',
        )

        released = SeatReservation.release_expired_reservations()

        self.assertEqual(released, 1)
        seat.refresh_from_db()
        self.assertFalse(seat.is_booked)

    def test_booking_view_creates_reservation_for_selected_seat(self):
        User = get_user_model()
        user = User.objects.create_user(username='booker', password='secret123')
        movie = Movie.objects.create(
            name='Booking Movie',
            image='movies/default.jpg',
            rating=7.5,
            cast='Actor',
            description='Demo',
        )
        theater = Theater.objects.create(name='Hall B', movie=movie, time='2026-07-01T19:30:00Z')
        seat = Seat.objects.create(theater=theater, seat_number='B1')

        self.client.force_login(user)
        response = self.client.post(
            reverse('book_seats', kwargs={'theater_id': theater.id}),
            {'seats': [str(seat.id)]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SeatReservation.objects.filter(seat=seat, user=user).exists())
        self.assertTrue(seat.refresh_from_db().is_booked)
        self.assertTrue(Booking.objects.filter(seat=seat).exists())
