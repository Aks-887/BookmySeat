from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import random

from movies.models import Genre, Language, Movie, MovieImage, Theater, Seat


GENRES = [
    'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary',
    'Drama', 'Family', 'Fantasy', 'Film-Noir', 'History', 'Horror',
    'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Short', 'Sport',
    'Thriller', 'War', 'Western', 'Indie', 'Superhero', 'Psychological',
]

LANGUAGES = [
    ('English', 'en'),
    ('Hindi', 'hi'),
    ('Tamil', 'ta'),
    ('Telugu', 'te'),
    ('Kannada', 'kn'),
    ('Malayalam', 'ml'),
    ('Marathi', 'mr'),
    ('Spanish', 'es'),
    ('French', 'fr'),
    ('German', 'de'),
]

MOVIE_NAMES = [
    'Quantum Nexus', 'The Last Guardian', 'Crimson Sky', 'Eternal Echoes',
    'Iron Heart', 'Mystic Realm', 'Neon Nights', 'The Lost Kingdom',
    'Silent Shadows', 'Burning Horizons', 'Crystal Waters', 'The Final Hour',
    'Midnight Echoes', 'Starlight Chronicles', 'The Forgotten Path', 'Urban Legends',
    'Whispered Secrets', 'The Ancient Curse', 'Fractured Reality', 'Beyond Time',
    'Rising Tide', 'The Last Stand', 'Infinite Loop', 'Dark Matter',
    'The Golden Gate', 'Silver Lining', 'Red Alert', 'Blue Horizon',
    'Green Valley', 'Purple Dreams', 'Yellow Fever', 'Black Mirror',
    'White Noise', 'Grey Skies', 'Orange Crush', 'Pink Sunset',
    'Cosmic Dance', 'Lunar Eclipse', 'Solar Flare', 'Stellar Wind',
    'Neptune Rising', 'Mars Attack', 'Venus Protocol', 'Mercury Rising',
    'Asteroid Belt', 'Black Hole Theory', 'Supernova', 'Comet Impact',
    'Galaxy Quest', 'Space Oddity', 'Zero Gravity', 'Velocity Max',
]

CAST_NAMES = [
    'John Smith', 'Emma Johnson', 'Michael Chen', 'Priya Sharma', 'Carlos Rodriguez',
    'Sofia Martinez', 'James Wilson', 'Aisha Patel', 'David Lee', 'Maria Garcia',
    'Robert Brown', 'Lisa Anderson', 'Christopher Taylor', 'Jennifer White',
]

DESCRIPTIONS = [
    'An epic adventure that will change everything.',
    'A thrilling journey into the unknown depths of human nature.',
    'A mysterious tale of love, loss, and redemption.',
    'An action-packed blockbuster with stunning visuals.',
    "A heartwarming story of friendship and perseverance.",
    'A psychological thriller that will keep you guessing.',
    "A romantic comedy that celebrates life's surprises.",
    'A dark drama exploring the consequences of power.',
    'An animated masterpiece for the whole family.',
    'A thought-provoking documentary about society.',
]

MOVIE_IMAGE_FILES = [
    'movies/635217f73e372771013edb4c-the-avengers-poster-marvel-movie-canvas1.jpg',
    'movies/download.jpeg',
    'movies/f5VK0h2bprRhR6iRrixcuEfRxSUF4l14F66vQYrsJGmKZ5nTA1.jpg',
    'movies/feUv2SYumXlT8E2RhzlYbZxfEGLG5AVrCPxP1gmAaCusxyPnA1.jpg',
    'movies/IQsBhg9t747dLhjXfsChIGZy4XfugER8BF0Gw5MDhIcnY5nTA1.jpg',
]


class Command(BaseCommand):
    help = (
        'Create fresh seed data for all sections. Generates genres/languages/movies/theaters/seats '
        'and forces 10 movies to be the “best” by giving them the highest ratings.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--movies', type=int, default=40, help='Total movies to create')
        parser.add_argument('--best', type=int, default=10, help='How many movies should be best (top by rating)')
        parser.add_argument('--theaters-per-movie', type=int, default=2, help='Theaters to create per movie')
        parser.add_argument('--seats-per-theater', type=int, default=15, help='Seats to create per theater (approx)')
        parser.add_argument('--clear', action='store_true', help='If set, clears existing Movies/Genres/Languages/Theaters/Seats first')

    def handle(self, *args, **options):
        num_movies = options['movies']
        best_count = options['best']
        theaters_per_movie = options['theaters_per_movie']
        seats_per_theater = options['seats_per_theater']
        clear = options['clear']

        if best_count > num_movies:
            raise ValueError('--best cannot be greater than --movies')

        self.stdout.write(self.style.SUCCESS('Starting seed_best_data...'))

        if clear:
            self.stdout.write('Clearing existing data...')
            # No Booking/EmailTask cleanup here; those are transactional data.
            Theater.objects.all().delete()
            MovieImage.objects.all().delete()
            Seat.objects.all().delete()
            Movie.objects.all().delete()
            Genre.objects.all().delete()
            Language.objects.all().delete()

        # Genres
        genres = []
        self.stdout.write('Creating genres...')
        for g in GENRES:
            genre, _ = Genre.objects.get_or_create(
                name=g, defaults={'description': f'{g} movies and shows'}
            )
            genres.append(genre)

        # Languages
        languages = []
        self.stdout.write('Creating languages...')
        for name, code in LANGUAGES:
            lang, _ = Language.objects.get_or_create(name=name, code=code)
            languages.append(lang)

        # Create movies. We will explicitly assign ratings so that exactly `best_count` movies are the best.
        self.stdout.write(f'Creating {num_movies} movies (best={best_count})...')

        base_show_names = [
            'Grand Arena', 'Silver Screen', 'Studio One', 'Studio Two',
            'Galaxy Hall', 'Crystal Cinema', 'Cityplex', 'Metro Screen'
        ]
        show_hours = [10, 13, 16, 19, 22]

        all_movie_names = MOVIE_NAMES[:]
        random.shuffle(all_movie_names)

        created_movies = []

        now = timezone.now()
        for i in range(num_movies):
            movie_name = f"{all_movie_names[i % len(all_movie_names)]} {i+1}"

            days_back = random.randint(0, 365 * 5)
            release_date = (now - timedelta(days=days_back)).date()

            # Force top/best ratings
            if i < best_count:
                # High ratings for best movies
                rating = round(random.uniform(9.0, 9.8), 1)
            else:
                # Lower ratings for the rest
                rating = round(random.uniform(5.5, 8.9), 1)

            cast = ', '.join(random.sample(CAST_NAMES, random.randint(2, 3)))
            description = random.choice(DESCRIPTIONS)

            image_path = random.choice(MOVIE_IMAGE_FILES)

            movie = Movie.objects.create(
                name=movie_name,
                rating=rating,
                cast=cast,
                description=description,
                release_date=release_date,
                image=image_path,
            )
            movie.genres.set(random.sample(genres, random.randint(2, 4)))
            movie.languages.set(random.sample(languages, random.randint(1, 3)))

            # gallery images
            for j in range(2):
                MovieImage.objects.create(
                    movie=movie,
                    image=random.choice(MOVIE_IMAGE_FILES),
                    alt_text=f'{movie.name} - Gallery Image {j+1}',
                )

            # theaters + seats
            for t_index in range(theaters_per_movie):
                theater_name = f"{random.choice(base_show_names)} {random.randint(1, 6)}"
                theater_time = now + timedelta(days=random.randint(1, 14), hours=random.choice(show_hours))
                theater = Theater.objects.create(
                    movie=movie,
                    name=theater_name,
                    time=theater_time,
                )

                # Seats: e.g. rows A..E, seats 1..6 -> 30. We'll generate approx `seats_per_theater`.
                row_letters = ['A', 'B', 'C', 'D', 'E', 'F']
                count = 0
                for row in row_letters:
                    for seat_number in range(1, 11):
                        if count >= seats_per_theater:
                            break
                        Seat.objects.create(theater=theater, seat_number=f'{row}{seat_number}')
                        count += 1
                    if count >= seats_per_theater:
                        break

            created_movies.append(movie)

        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(created_movies)} movies'))
        self.stdout.write(
            self.style.SUCCESS(
                '✓ “Best” movies are guaranteed by rating: top 10 by rating will appear in Recommended.'
            )
        )

        # Quick sanity output
        best_sample = list(
            Movie.objects.all().order_by('-rating', '-release_date', 'name').values_list('name', 'rating')[:best_count]
        )
        self.stdout.write(self.style.SUCCESS('Top best movies (name, rating):'))
        for name, rating in best_sample:
            self.stdout.write(f' - {name}: {rating}')

