import urllib.request
import urllib.parse
import re
import time
from django.core.management.base import BaseCommand
from movies.models import Movie

class Command(BaseCommand):
    help = 'Automatically fetch missing YouTube trailer URLs using YouTube search scraping'

    def handle(self, *args, **options):
        self.stdout.write('Scanning database for movies missing trailers...')
        
        # Get movies with empty trailer_url
        movies = Movie.objects.filter(trailer_url='')
        total = movies.count()
        self.stdout.write(f'Found {total} movies without trailers.')
        
        success_count = 0
        for index, movie in enumerate(movies, 1):
            name = movie.name.strip()
            
            # Check for junk titles to skip
            is_junk = (
                (len(name) > 30 and name.isalnum()) or
                name.lower() in ('oip', 'download', 'img 5878 scaled', 'hd hollywood') or
                re.search(r'^[a-fA-F0-9]{32,}', name) or
                ('poster' in name.lower() and len(name) > 25)
            )
            
            if is_junk:
                self.stdout.write(self.style.WARNING(f"[{index}/{total}] Skipping junk movie title: '{name}'"))
                continue
            
            self.stdout.write(f"[{index}/{total}] Fetching trailer for '{name}'...")
            
            query = urllib.parse.quote(f"{name} official trailer")
            url = f"https://www.youtube.com/results?search_query={query}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            )
            
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8')
                    matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                    if matches:
                        video_id = matches[0]
                        movie.trailer_url = f"https://www.youtube.com/watch?v={video_id}"
                        movie.save()
                        self.stdout.write(self.style.SUCCESS(f"  [OK] Found video ID: {video_id}"))
                        success_count += 1
                    else:
                        self.stdout.write(self.style.WARNING("  No matching video found."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error: {e}"))
            
            # Polite rate-limiting delay
            time.sleep(1.2)
            
        self.stdout.write(self.style.SUCCESS(f"Finished! Successfully fetched and updated {success_count} trailers."))
