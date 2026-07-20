import requests
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction

# IMPORTANT: Adjust this import to match your actual app name!
from movies.models import Movie, Genre, Language 

class Command(BaseCommand):
    help = 'Seeds 80+ movies and FORCE DOWNLOADS their real posters using OMDb API'

    def add_arguments(self, parser):
        parser.add_argument('api_key', type=str, help='Your OMDb API Key')

    def handle(self, *args, **kwargs):
        api_key = kwargs['api_key']
        
        # 80+ curated popular movies
        movie_titles = [
            "The Shawshank Redemption", "The Godfather", "The Dark Knight", 
            "12 Angry Men", "Schindler's List", "The Lord of the Rings: The Return of the King", 
            "Pulp Fiction", "The Lord of the Rings: The Fellowship of the Ring", 
            "The Good, the Bad and the Ugly", "Forrest Gump", "Fight Club", 
            "Inception", "Star Wars: Episode V - The Empire Strikes Back", 
            "The Matrix", "Goodfellas", "One Flew Over the Cuckoo's Nest", "Se7en", 
            "Seven Samurai", "It's a Wonderful Life", "The Silence of the Lambs", 
            "City of God", "Saving Private Ryan", "Life Is Beautiful", "The Green Mile", 
            "Interstellar", "Star Wars: Episode IV - A New Hope", "Terminator 2: Judgment Day", 
            "Back to the Future", "Spirited Away", "Psycho", "The Pianist", 
            "Léon: The Professional", "Parasite", "The Lion King", "Gladiator", 
            "American History X", "The Departed", "Whiplash", "The Prestige", 
            "The Usual Suspects", "Casablanca", "Grave of the Fireflies", 
            "The Intouchables", "Modern Times", "Once Upon a Time in the West", 
            "Cinema Paradiso", "Rear Window", "Alien", "City Lights", "Apocalypse Now", 
            "Memento", "Django Unchained", "Indiana Jones and the Raiders of the Lost Ark", 
            "WALL·E", "The Lives of Others", "Sunset Blvd.", "Paths of Glory", 
            "The Shining", "The Great Dictator", "Avengers: Infinity War", 
            "Witness for the Prosecution", "Aliens", "Spider-Man: Into the Spider-Verse", 
            "American Beauty", "Dr. Strangelove", "The Dark Knight Rises", "Oldboy", 
            "Joker", "Amadeus", "Toy Story", "Coco", "Braveheart", "Wall Street", 
            "Avengers: Endgame", "Princess Mononoke", "Good Will Hunting", "Your Name.", 
            "3 Idiots", "High and Low", "Capernaum", "Toy Story 3", 
            "Star Wars: Episode VI - Return of the Jedi", "Oppenheimer", "Barbie"
        ]

        self.stdout.write(self.style.SUCCESS(f'Starting poster download for {len(movie_titles)} movies...'))

        for title in movie_titles:
            self.fetch_and_create_movie(title, api_key)

        self.stdout.write(self.style.SUCCESS('Successfully completed! Check your media folder.'))

    def fetch_and_create_movie(self, title, api_key):
        url = f"http://www.omdbapi.com/?t={title}&apikey={api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('Response') == 'False':
                self.stdout.write(self.style.ERROR(f"Not found on OMDb: {title}"))
                return

            with transaction.atomic():
                # Parse Date
                release_date = None
                date_str = data.get('Released', 'N/A')
                if date_str != 'N/A':
                    try:
                        release_date = datetime.strptime(date_str, "%d %b %Y").date()
                    except ValueError:
                        pass

                # Parse Rating
                rating = Decimal('0.0')
                imdb_rating = data.get('imdbRating', 'N/A')
                if imdb_rating != 'N/A':
                    rating = Decimal(imdb_rating)

                # Using update_or_create to force an update even if it already exists!
                movie, created = Movie.objects.update_or_create(
                    name=data.get('Title'),
                    defaults={
                        'rating': rating,
                        'cast': data.get('Actors', ''),
                        'description': data.get('Plot', ''),
                        'release_date': release_date,
                        'trailer_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' 
                    }
                )

                # Download and attach the real poster
                poster_url = data.get('Poster')
                if poster_url and poster_url != 'N/A':
                    img_response = requests.get(poster_url, timeout=10)
                    if img_response.status_code == 200:
                        file_name = f"{movie.name.replace(' ', '_').replace(':', '').lower()}_poster.jpg"
                        # Save the image content directly to the ImageField
                        movie.image.save(file_name, ContentFile(img_response.content), save=True)
                        action = "Created with poster" if created else "Updated with poster"
                        self.stdout.write(self.style.SUCCESS(f"{action}: {movie.name}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Failed to download poster for: {movie.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"No poster available for: {movie.name}"))

                # Handle Genres
                for g_name in [g.strip() for g in data.get('Genre', '').split(',') if g.strip() and g.strip() != 'N/A']:
                    genre_obj, _ = Genre.objects.get_or_create(name=g_name)
                    movie.genres.add(genre_obj)

                # Handle Languages
                for l_name in [l.strip() for l in data.get('Language', '').split(',') if l.strip() and l.strip() != 'N/A']:
                    code = l_name[:5].lower()
                    language_obj, _ = Language.objects.get_or_create(name=l_name, defaults={'code': code})
                    movie.languages.add(language_obj)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing {title}: {str(e)}"))