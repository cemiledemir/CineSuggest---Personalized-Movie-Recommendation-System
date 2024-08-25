import streamlit as st
from openai import OpenAI
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
from tmdbv3api import TMDb, Movie
import requests
from io import BytesIO
import re
import json
import os

# Load environment variables
load_dotenv()

# TMDb API setup
tmdb = TMDb()
tmdb.api_key = os.getenv('TMDB_API_KEY')
movie = Movie()

client = OpenAI()

# Streamlit page config
st.set_page_config(layout="wide", page_title="Movie Recommendations")

# Custom CSS
st.markdown("""
<style>
    body {
        color: #FFFFFF;
        background-color: #0E1117;
    }
    .stApp {
        background-color: #0E1117;
    }
    .movie-card {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .movie-title {
        color: #FFFFFF;
        font-size: 24px;
        font-weight: bold;
    }
    .movie-info {
        color: #CCCCCC;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title('Personalized Movie Recommendation System')

# Collect the Genres and Favourite Movies
st.sidebar.title("Your Preferences")
selected_genres = st.sidebar.multiselect('Select your favorite genres:', ['Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'History', 'Horror', 'Music', 'Mystery', 'Romance', 'Science Fiction', 'War', 'Western'])
favorite_movies = st.sidebar.text_input('Enter your favorite movies (comma separated):')
favorite_movies = [movie.strip().lower().replace(" ", "") for movie in favorite_movies.split(',') if movie.strip()]

# TMDB Dataset
movies_df = pd.read_csv('movies_dataset.csv', quotechar='"')
movies_df['Genre'] = movies_df['Genre'].fillna('').astype(str)
movies_df['Overview'] = movies_df['Overview'].fillna('').astype(str)


if not selected_genres or not favorite_movies:
    st.warning("Please enter at least one genre and one favorite movie to get recommendations.")
else:
    filtered_df = movies_df[movies_df['Genre'].apply(lambda x: any(genre in x for genre in selected_genres))]
    if filtered_df.empty:
        st.warning("No movies found with the selected genres. Please try different genres.")
    else:
        if filtered_df['Overview'].dropna().empty:
            st.warning(
                "The selected genres don't contain enough information for recommendations. Please try different genres.")
        else:
            # Proceed with TF-IDF and recommendation logic
            tfidf = TfidfVectorizer(stop_words='english')
            try:
                tfidf_matrix = tfidf.fit_transform(filtered_df['Overview'].dropna())
                favorite_movie_overviews = movies_df[movies_df['Title'].str.lower().replace(" ", "").isin([movie.lower().replace(" ", "") for movie in favorite_movies])]['Overview'].dropna()

                if favorite_movie_overviews.empty:
                    st.warning("None of your favorite movies have overviews in the dataset.")
                else:
                    favorite_tfidf = tfidf.transform(favorite_movie_overviews)

                    cosine_sim = cosine_similarity(favorite_tfidf, tfidf_matrix)
                    mean_cosine_sim = cosine_sim.mean(axis=0)

                    # Normalize both cosine similarity and score
                    scaler = MinMaxScaler()
                    normalized_cosine_sim = scaler.fit_transform(mean_cosine_sim.reshape(-1, 1)).flatten()
                    normalized_scores = scaler.fit_transform(filtered_df['Score'].values.reshape(-1, 1)).flatten()
                    normalized_vote_count = scaler.fit_transform(filtered_df['Vote Count'].values.reshape(-1, 1)).flatten()

                    combined_score = (0.6 * normalized_cosine_sim + 0.2 * normalized_scores + 0.2 * normalized_vote_count)

                    # Sort based on the combined score
                    sorted_indices = combined_score.argsort()[::-1]
                    top_10_indices = sorted_indices[:10]
                    recommendations = filtered_df.iloc[top_10_indices][['Title', 'Genre', 'Overview', 'Score', 'Vote Count']]

                    # Initialize messages in session state if not present
                    if "messages" not in st.session_state:
                        st.session_state.messages = [
                            {"role": "system",
                             "content": "You are a helpful and enthusiastic movie nerd, and know everything about movies. Provide personalized film recommendations across various genres and even identifies films that blend multiple genres for a unique viewing experience based on user's genres input and favourite movies. First excitedly tell the user that you have just the thing they are looking for.Return 5 movie suggestions as a list of dictionaries with double quotes. This dictionary should have the keys ‘Movie Title’, ‘Genre(s)’, ‘Rating’, ‘Overview’, ‘Tailored For You Because’, ‘Fun Fact’. In ‘Tailored For You Because’ column, explain in a short sentence how you made this suggestion by establishing a relationship with the user."}
                        ]

                    if st.button("Get Movie Recommendations"):
                        if not favorite_movies:
                            st.warning("Please enter at least one favorite movie.")
                        else:
                            user_message = f"The user likes the movies {', '.join(favorite_movies)} and interested in {', '.join(selected_genres)} genres. Here are the top genres and summaries of similar movies:\n"

                            for _, row in recommendations.iterrows():
                                user_message += f"\nTitle: {row['Title']}\nGenres: {row['Genre']}\nSummary: {row['Overview']}\n"

                            user_message += "\nBased on the above data, suggest some movies that the user might like. Excitedly tell the user that you have just the thing they are looking for. Return 5 movie suggestions as a list of dictionaries with double quotes. This dictionary should have the keys ‘Movie Title’, ‘Genre(s)’, ‘Rating’, ‘Overview’, ‘Tailored For You Because’, ‘Fun Fact’. In ‘Tailored For You Because’ column, explain in a short sentence how you made this suggestion by establishing a relationship with the user."

                            # Add user message to chat history
                            st.session_state.messages.append({"role": "user", "content": user_message})

                            try:
                                # Generate recommendations using OpenAI
                                completion = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=st.session_state.messages,
                                )

                                refined_recommendation = completion.choices[0].message.content
                                st.session_state.messages.append({"role": "assistant", "content": refined_recommendation})

                                match = re.search(r'\[\s*{.*?}\s*\]', refined_recommendation, re.DOTALL)

                                if match:
                                    json_part = match.group(0)
                                    # Convert the extracted JSON string to a list of dictionaries
                                    refined_recommendation_list = json.loads(json_part)
                                else:
                                    print("No match found.")
                                json_start = refined_recommendation.find("```json")
                                intro_text = refined_recommendation[:json_start].strip()

                                st.markdown(intro_text)
                                for movie_data in refined_recommendation_list:
                                    with st.container():
                                        col1, col2 = st.columns([1, 3])

                                        # Search for movie poster
                                        search = movie.search(movie_data['Movie Title'])
                                        if search:
                                            poster_path = search[0].poster_path
                                            if poster_path:
                                                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                                                response = requests.get(poster_url)
                                                img = BytesIO(response.content)
                                                col1.image(img, width=200)
                                            else:
                                                col1.write("Poster not found.")
                                        else:
                                            col1.write("Movie not found.")

                                        with col2:
                                            st.markdown(f"<h2 class='movie-title'>{movie_data['Movie Title']}</h2>",
                                                        unsafe_allow_html=True)
                                            st.markdown(
                                                f"<p class='movie-info'>Genre(s): {movie_data['Genre(s)']} | Rating: {movie_data['Rating']}</p>",
                                                unsafe_allow_html=True)
                                            # Create three columns
                                            col1, col2, col3 = st.columns(3)

                                            # Add Overview to the first column
                                            with col1:
                                                st.markdown("<h6 class='movie-subtitle'>Overview</h6>",
                                                            unsafe_allow_html=True)
                                                st.markdown(f"<p class='movie-info'>{movie_data['Overview']}</p>",
                                                            unsafe_allow_html=True)

                                            # Add Tailored For You Because to the second column
                                            with col2:
                                                st.markdown("<h6 class='movie-subtitle'>Tailored For You Because</h6>",
                                                            unsafe_allow_html=True)
                                                st.markdown(
                                                    f"<p class='movie-info'>{movie_data['Tailored For You Because']}</p>",
                                                    unsafe_allow_html=True)

                                            # Add Fun Fact to the third column
                                            with col3:
                                                st.markdown("<h6 class='movie-subtitle'>Fun Fact</h6>",
                                                            unsafe_allow_html=True)
                                                st.markdown(f"<p class='movie-info'>{movie_data['Fun Fact']}</p>",
                                                            unsafe_allow_html=True)

                                    st.markdown("<hr>", unsafe_allow_html=True)

                                # Save recommendations to file
                                with open('movie_recommendations.md', 'w') as f:
                                    f.write(refined_recommendation)
                            except Exception as e:
                                st.error(f"An error occurred: {str(e)}")

            except ValueError as e:
                st.error(f"An error occurred: {e}")