
import os
import requests
import time

API_KEY = "38d447d3"

movies = [
    "Avatar",
    "Avatar: The Way of Water",
    "Avengers: Endgame",
    "Avengers: Infinity War",
    "Iron Man",
    "Iron Man 2",
    "Iron Man 3",
    "Captain America: The First Avenger",
    "Captain America: Civil War",
    "Captain Marvel",
    "Thor",
    "Thor: Ragnarok",
    "Doctor Strange",
    "Black Panther",
    "Black Widow",
    "Spider-Man: Homecoming",
    "Spider-Man: Far From Home",
    "Spider-Man: No Way Home",
    "The Batman",
    "Joker",
    "The Dark Knight",
    "Batman Begins",
    "The Dark Knight Rises",
    "Man of Steel",
    "Aquaman",
    "Wonder Woman",
    "Justice League",
    "Shazam!",
    "The Flash",
    "Oppenheimer",
    "Interstellar",
    "Inception",
    "Tenet",
    "Dunkirk",
    "Dune",
    "Titanic",
    "Gladiator",
    "The Shawshank Redemption",
    "Fight Club",
    "Forrest Gump",
    "The Godfather",
    "Pulp Fiction",
    "The Matrix",
    "The Matrix Reloaded",
    "The Matrix Revolutions",
    "John Wick",
    "John Wick: Chapter 2",
    "John Wick: Chapter 3 – Parabellum",
    "John Wick: Chapter 4",
    "Top Gun: Maverick",
    "Mission: Impossible – Fallout",
    "Mission: Impossible – Dead Reckoning Part One",
    "3 Idiots",
    "PK",
    "Dangal",
    "Bajrangi Bhaijaan",
    "Sultan",
    "Chennai Express",
    "Dilwale",
    "Raees",
    "Don",
    "Don 2",
    "War",
    "Pathaan",
    "Jawan",
    "Dunki",
    "Animal",
    "Kabir Singh",
    "Drishyam",
    "Drishyam 2",
    "Bhool Bhulaiyaa",
    "Bhool Bhulaiyaa 2",
    "Chhichhore",
    "Brahmastra Part One: Shiva",
    "Stree",
    "Stree 2",
    "Gully Boy",
    "Rockstar",
    "Andhadhun",
    "Uri: The Surgical Strike",
    "Baahubali: The Beginning",
    "Baahubali 2: The Conclusion",
    "KGF: Chapter 1",
    "KGF: Chapter 2",
    "RRR",
    "Pushpa: The Rise",
    "Pushpa 2: The Rule",
    "Salaar",
    "Kalki 2898 AD",
    "Leo",
    "Vikram",
    "Master",
    "Jailer",
    "Beast",
    "Kantara",
    "Sita Ramam",
    "Hi Nanna",
    "Lucky Baskhar",
    "Hanu-Man"
]

SAVE_DIR = "posters"
os.makedirs(SAVE_DIR, exist_ok=True)

for movie in movies:
    try:
        url = f"https://www.omdbapi.com/?apikey={API_KEY}&t={movie}"
        data = requests.get(url, timeout=10).json()

        if data.get("Response") == "True" and data.get("Poster") != "N/A":
            img = requests.get(data["Poster"], timeout=20).content

            filename = "".join(
                c for c in movie if c.isalnum() or c in (" ", "-", "_")
            ).rstrip() + ".jpg"

            with open(os.path.join(SAVE_DIR, filename), "wb") as f:
                f.write(img)

            print(f"✅ {movie}")
        else:
            print(f"❌ {movie} -> {data.get('Error')}")

        time.sleep(0.3)  # avoid sending requests too quickly

    except Exception as e:
        print(f"⚠️ {movie}: {e}")

print("\nFinished!")