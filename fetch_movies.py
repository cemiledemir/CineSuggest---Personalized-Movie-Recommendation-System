import requests
import pandas as pd
import time
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv('TMDB_API_KEY')

def get_genres(api_key):
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={api_key}&language=en-US"
    response = requests.get(url)
    genres = response.json()['genres']
    return {genre['id']: genre['name'] for genre in genres}


def fetch_movies(api_key, genre_id=None, page=1):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}&language=en-US&sort_by=popularity.desc&page={page}"
    if genre_id:
        url += f"&with_genres={genre_id}"

    response = requests.get(url)
    data = response.json()
    return data['results'], data['total_pages']


genre_ids = get_genres(API_KEY)

movies = []

for genre_id, genre in genre_ids.items():
    page = 1
    print(genre)
    while True:
        movies_data, total_pages = fetch_movies(API_KEY, genre_id, page)
        for movie in movies_data:
            genres = [genre_ids[genre_id] for genre_id in movie['genre_ids']]
            movie_info = {
                'ID': movie['id'],
                'Title': movie['title'],
                'Release Year': movie['release_date'].split('-')[0] if movie['release_date'] else 'N/A',
                'Genre': ', '.join(genres),
                'Overview': movie['overview'],
                'Score': movie['vote_average'],
                'Vote Count': movie['vote_count']
            }
            movies.append(movie_info)
        page += 1
        print(page)
        if page > 200:
            break
        time.sleep(0.2)


movies_df = pd.DataFrame(movies)
print(f'numrowbefore duplicat {len(movies_df)}')
movies_df.drop_duplicates(subset=['ID'], keep='first', inplace=True)
print(f'numrowafter duplicat {len(movies_df)}')
movies_df.to_csv('movies_dataset.csv', index=False)

print(movies_df)
