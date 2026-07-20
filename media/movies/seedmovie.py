import os
import requests
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE","bookmyseat.settings")
import django
django.setup()

from movies.models import Movie
from django.core.files import File

API_KEY="38d447d3"

movies=[
"Avatar","Avatar: The Way of Water","Avengers: Endgame","Avengers: Infinity War","Iron Man","Iron Man 2","Iron Man 3","Captain America: The First Avenger","Captain America: Civil War","Captain Marvel","Thor","Thor: Ragnarok","Doctor Strange","Black Panther","Black Widow","Spider-Man: Homecoming","Spider-Man: Far From Home","Spider-Man: No Way Home","The Batman","Joker","The Dark Knight","Batman Begins","The Dark Knight Rises","Man of Steel","Aquaman","Wonder Woman","Justice League","Shazam!","The Flash","Oppenheimer","Interstellar","Inception","Tenet","Dunkirk","Dune","Dune: Part Two","Titanic","Gladiator","The Shawshank Redemption","Fight Club","Forrest Gump","The Godfather","Pulp Fiction","The Matrix","The Matrix Reloaded","The Matrix Revolutions","John Wick","John Wick: Chapter 2","John Wick: Chapter 3 - Parabellum","John Wick: Chapter 4","Top Gun: Maverick","Mission: Impossible - Fallout","Mission: Impossible - Dead Reckoning Part One","3 Idiots","PK","Dangal","Bajrangi Bhaijaan","Sultan","Chennai Express","Dilwale","Raees","Don","Don 2","War","Pathaan","Jawan","Dunki","Animal","Kabir Singh","Drishyam","Drishyam 2","Bhool Bhulaiyaa","Bhool Bhulaiyaa 2","Chhichhore","Brahmastra Part One: Shiva","Stree","Stree 2","Gully Boy","Rockstar","Andhadhun","Uri: The Surgical Strike","Baahubali: The Beginning","Baahubali 2: The Conclusion","KGF: Chapter 1","KGF: Chapter 2","RRR","Pushpa: The Rise","Pushpa 2: The Rule","Salaar","Kalki 2898 AD","Leo","Vikram","Master","Jailer","Beast","Kantara","Sita Ramam","Hi Nanna","Lucky Baskhar","Hanu-Man"]

os.makedirs("media/posters",exist_ok=True)

for title in movies:
    print("Processing:",title)
    try:
        r=requests.get(f"https://www.omdbapi.com/?apikey={API_KEY}&t={title}",timeout=15).json()
        if r.get("Response")!="True":
            print(" Not found")
            continue
        if Movie.objects.filter(title=r["Title"]).exists():
            print(" Already exists")
            continue
        m=Movie()
        m.title=r["Title"]
        if hasattr(m,"description"): m.description=r.get("Plot","")
        if hasattr(m,"genre"): m.genre=r.get("Genre","").split(",")[0]
        if hasattr(m,"language"): m.language=r.get("Language","").split(",")[0]
        if hasattr(m,"duration"):
            try:m.duration=int(r["Runtime"].split()[0])
            except:m.duration=120
        if hasattr(m,"rating"):
            try:m.rating=float(r["imdbRating"])
            except:m.rating=0
        if hasattr(m,"release_date"):
            try:m.release_date=datetime.strptime(r["Released"],"%d %b %Y").date()
            except:pass
        if r.get("Poster") and r["Poster"]!="N/A" and hasattr(m,"image"):
            img=requests.get(r["Poster"]).content
            fname="".join(c for c in r["Title"] if c.isalnum() or c in " -_")+".jpg"
            path=os.path.join("media","posters",fname)
            open(path,"wb").write(img)
            with open(path,"rb") as f:
                m.image.save(fname,File(f),save=False)
        m.save()
        print(" Added")
    except Exception as e:
        print(" Error:",e)
print("Done")
