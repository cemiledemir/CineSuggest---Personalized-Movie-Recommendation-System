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


def fetch_popular_movies(api_key, page=1):
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={api_key}&language=en-US&page={page}"
    response = requests.get(url)
    data = response.json()
    return data['results']


genre_dict = get_genres(API_KEY)

movies = []

page = 1
while True:
    movies_data = fetch_popular_movies(API_KEY, page)
    for movie in movies_data:
        genres = [genre_dict[genre_id] for genre_id in movie['genre_ids']]
        movie_info = {
            'Title': movie['title'],
            'Release Year': movie['release_date'].split('-')[0] if movie['release_date'] else 'N/A',
            'Genres': '| '.join(genres),
            'Overview': movie['overview'],
            'Vote Average': movie['vote_average'],
            'Vote Count': movie['vote_count']
        }
        movies.append(movie_info)
    page += 1
    if page > 500:
        break
    time.sleep(0.2)

movies_df = pd.DataFrame(movies)

movies_df.to_csv('popular_movies_with_genres_dataset.csv', index=False)

print(movies_df)

