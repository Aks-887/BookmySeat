from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from movies.models import Genre, Language, Movie, MovieImage, Theater, Seat, Booking

GENRES = [
    'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary',
    'Drama', 'Family', 'Fantasy', 'Film-Noir', 'History', 'Horror',
    'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Short', 'Sport',
    'Thriller', 'War', 'Western', 'Indie', 'Superhero', 'Psychological',
    'Romantic Comedy', 'Dark Comedy', 'Post-Apocalyptic', 'Steampunk',
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
    'The Midnight Club', 'The Dawn Patrol', 'The Twilight Zone', 'The Eternal Night',
    'The Day After', 'The Week Before', 'The Month Beyond', 'The Year Forgotten',
    'Time Warp', 'Dimensional Shift', 'Parallel Universe', 'Alternate Reality',
    'The Prime Timeline', 'Loop Holes', 'Paradox', 'Singularity',
    'The Edge of Reason', 'Beyond Logic', 'Into the Abyss', 'Out of the Darkness',
    'The Void', 'The Nexus', 'The Portal', 'The Gateway',
    'Threshold', 'Crossing Over', 'The Bridge', 'The Tunnel',
    'Into the Deep', 'Surface Level', 'Middle Ground', 'High Stakes',
    'The Climb', 'The Fall', 'Rising Up', 'Going Down',
    'The Journey', 'The Destination', 'The Road', 'The Path',
    'The Quest', 'The Mission', 'The Operation', 'The Expedition',
    'The Crusade', 'The Campaign', 'The Battle', 'The War',
    'The Conflict', 'The Struggle', 'The Fight', 'The Challenge',
    'Victory', 'Defeat', 'Triumph', 'Tragedy',
    'The Hero\'s Return', 'The Villain\'s Rise', 'The Redemption', 'The Fall from Grace',
    'The Dark Side', 'The Light Side', 'The Grey Area', 'The Moral Compass',
    'The Ethical Dilemma', 'The Choice', 'The Crossroads', 'The Decision',
    'The Reckoning', 'The Judgment', 'The Trial', 'The Verdict',
    'The Sentence', 'The Prison', 'The Escape', 'The Freedom',
    'The Chains', 'The Shackles', 'The Bonds', 'The Liberation',
    'The Uprising', 'The Revolution', 'The Rebellion', 'The Restoration',
    'The Revival', 'The Resurrection', 'The Rebirth', 'The Beginning',
    'The End', 'The Conclusion', 'The Finale', 'The Epilogue',
]

CAST_NAMES = [
    'John Smith', 'Emma Johnson', 'Michael Chen', 'Priya Sharma', 'Carlos Rodriguez',
    'Sofia Martinez', 'James Wilson', 'Aisha Patel', 'David Lee', 'Maria Garcia',
    'Robert Brown', 'Lisa Anderson', 'Christopher Taylor', 'Jennifer White', 'Daniel Harris',
    'Jessica Martin', 'Matthew Thomas', 'Amanda Jackson', 'Anthony Davis', 'Sarah Miller',
]

DESCRIPTIONS = [
    'An epic adventure that will change everything.',
    'A thrilling journey into the unknown depths of human nature.',
    'A mysterious tale of love, loss, and redemption.',
    'An action-packed blockbuster with stunning visuals.',
    'A heartwarming story of friendship and perseverance.',
    'A psychological thriller that will keep you guessing.',
    'A romantic comedy that celebrates life\'s surprises.',
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
    help = 'Generate test data with 100+ movies, genres, languages, theaters, and seats'

    def add_arguments(self, parser):
        parser.add_argument(
            '--movies',
            type=int,
            default=120,
            help='Number of movies to create (default: 120)',
        )
        parser.add_argument(
            '--images-per-movie',
            type=int,
            default=2,
            help='Number of gallery images per movie (default: 2)',
        )

    def handle(self, *args, **options):
        num_movies = options['movies']
        images_per_movie = options['images_per_movie']

        self.stdout.write(self.style.SUCCESS('Starting data generation...'))

        # Clear existing data
        self.stdout.write('Clearing existing data...')
        Booking.objects.all().delete()
        Seat.objects.all().delete()
        Theater.objects.all().delete()
        MovieImage.objects.all().delete()
        Movie.objects.all().delete()
        Genre.objects.all().delete()
        Language.objects.all().delete()

        # Create Genres
        self.stdout.write('Creating genres...')
        genres = []
        for genre_name in GENRES:
            genre, created = Genre.objects.get_or_create(
                name=genre_name,
                defaults={'description': f'{genre_name} movies and shows'}
            )
            genres.append(genre)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(genres)} genres'))

        # Create Languages
        self.stdout.write('Creating languages...')
        languages = []
        for lang_name, lang_code in LANGUAGES:
            lang, created = Language.objects.get_or_create(
                name=lang_name,
                code=lang_code,
            )
            languages.append(lang)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(languages)} languages'))

        # Create Movies
        self.stdout.write(f'Creating {num_movies} movies...')
        movies_created = 0
        
        for i in range(num_movies):
            movie_name = f"{random.choice(MOVIE_NAMES)} {i+1}"
            
            # Random release date (within last 5 years)
            days_back = random.randint(0, 365 * 5)
            release_date = timezone.now().date() - timedelta(days=days_back)
            
            # Random rating between 5.5 and 9.5
            rating = round(random.uniform(5.5, 9.5), 1)
            
            # Random cast (2-3 actors)
            num_cast = random.randint(2, 3)
            cast = ', '.join(random.sample(CAST_NAMES, num_cast))
            
            # Random description
            description = random.choice(DESCRIPTIONS)
            
            # Create movie
            movie = Movie.objects.create(
                name=movie_name,
                rating=rating,
                cast=cast,
                description=description,
                release_date=release_date,
                image=random.choice(MOVIE_IMAGE_FILES),
            )
            
            # Assign 2-4 random genres
            num_genres = random.randint(2, 4)
            movie_genres = random.sample(genres, num_genres)
            movie.genres.set(movie_genres)
            
            # Assign 1-3 random languages
            num_langs = random.randint(1, 3)
            movie_langs = random.sample(languages, num_langs)
            movie.languages.set(movie_langs)
            
            # Add gallery images (optional, using placeholder URLs)
            for j in range(images_per_movie):
                MovieImage.objects.create(
                    movie=movie,
                    image=random.choice(MOVIE_IMAGE_FILES),
                    alt_text=f'{movie.name} - Gallery Image {j+1}'
                )

            # Create theater showtimes and seats for booking
            theater_names = [
                'Grand Arena', 'Silver Screen', 'Studio One', 'Studio Two',
                'Galaxy Hall', 'Crystal Cinema', 'Cityplex', 'Metro Screen'
            ]
            show_hours = [10, 13, 16, 19, 22]
            for t_index in range(random.randint(1, 2)):
                theater_name = f"{random.choice(theater_names)} {random.randint(1, 6)}"
                theater_time = timezone.now() + timedelta(days=random.randint(1, 14), hours=random.choice(show_hours))
                theater = Theater.objects.create(
                    movie=movie,
                    name=theater_name,
                    time=theater_time,
                )
                for row in ['A', 'B', 'C', 'D', 'E']:
                    for seat_number in range(1, 7):
                        Seat.objects.create(
                            theater=theater,
                            seat_number=f'{row}{seat_number}'
                        )

            movies_created += 1
            if (i + 1) % 20 == 0:
                self.stdout.write(f'  {i+1}/{num_movies} movies created...')
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created {movies_created} movies'))
        
        # Summary statistics
        total_genres = Genre.objects.count()
        total_languages = Language.objects.count()
        total_movies = Movie.objects.count()
        total_images = MovieImage.objects.count()
        total_theaters = Theater.objects.count()
        total_seats = Seat.objects.count()
        
        self.stdout.write(self.style.SUCCESS('\n========== SUMMARY =========='))
        self.stdout.write(f'Genres: {total_genres}')
        self.stdout.write(f'Languages: {total_languages}')
        self.stdout.write(f'Movies: {total_movies}')
        self.stdout.write(f'Gallery Images: {total_images}')
        self.stdout.write(f'Theaters: {total_theaters}')
        self.stdout.write(f'Seats: {total_seats}')
        self.stdout.write(f'Avg Genres/Movie: {total_movies and total_genres * total_movies // total_movies or 0}')
        self.stdout.write(f'Avg Languages/Movie: {total_movies and total_languages * total_movies // total_movies or 0}')
        self.stdout.write(self.style.SUCCESS('========== COMPLETE ==========\n'))
        self.stdout.write(self.style.SUCCESS('Test data generated successfully! Visit http://127.0.0.1:8000/'))
