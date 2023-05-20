from datetime import timedelta
import secrets
import string
from dotenv import load_dotenv
from flask import Flask, abort, request, jsonify, render_template, session
import re
import random
import openai
import requests
import os
from db import MongoDB
from collections import defaultdict
load_dotenv()
app = Flask(__name__, template_folder='templates',static_url_path='/static')
openai.api_key = os.getenv('OPENAI_API_KEY')
app.secret_key = secrets.token_hex(16)
# Set the max age for cookies (session lifetime)
app.permanent_session_lifetime = timedelta(days=1)
# Load .env file
mongodb = MongoDB()

# Set a random secret key
app = Flask(__name__, template_folder='templates', static_url_path='/static')
openai.api_key = os.getenv('OPENAI_API_KEY')
app.secret_key = secrets.token_hex(16)
book_image_default = 'static/default.png'  # default placeholder image

# Add this at the top of your Flask app
user_history = defaultdict(list)


@app.route('/')
def index():
    session.permanent = True  # Make the session last until it's expired

    recommendations = []  # start with an empty list of recommendations

    # Check if 'user_id' is already set in the session
    if 'user_id' not in session:
        # Generate a unique user ID and store it in the session
        session['user_id'] = generate_user_id()
        # Save the user to MongoDB
        mongodb.save_user(session['user_id'])

    # Print user ID and history
    print("User ID:", session['user_id'])
    print("User History:", user_history[session['user_id']])

    return render_template('chat.html', recommendations=recommendations)

# Function to generate a unique user ID
def generate_user_id():
    # Generate a random alphanumeric user ID
    user_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return user_id

def get_book_details_open_library(title):
    url = f"https://openlibrary.org/search.json?q={title}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        works = data.get('docs', [])
        if works:
            work = works[0]
            categories = work.get('subject', [])
            if len(categories) > 5:
                categories = categories[:5]

            book_details = {
                'title': work.get('title', ''),
                'description': work.get('first_sentence', [''])[0] if work.get('first_sentence') else '',
                'authors': work.get('author_name', []),
                'categories': categories,
                'borrow_link': f"https://openlibrary.org{work.get('key', '')}/borrow" if work.get('key') else 'No borrow link available',
                'image': f"https://covers.openlibrary.org/b/id/{work.get('cover_i', '')}-M.jpg" if work.get('cover_i') else book_image_default,  # added default image
            }

            return book_details

    return {
        'title': title,
        'description': 'Book with this title not found.',
        'authors': [],
        'categories': [],
        'borrow_link': 'No borrow link available',
        'image': book_image_default , # added default image
    }

def get_book_details_google_books(title, author=None):
    query = f'intitle:{title}'
    if author:
        query += f' inauthor:{author}'
 
    response = requests.get(
        f'https://www.googleapis.com/books/v1/volumes?q={query}')
    if response.status_code == 200:
        data = response.json()
        if 'items' in data:
            books = random.sample(data['items'], min(5, len(data['items'])))
            book_details = []
            for book in books:
                volume_info = book['volumeInfo']
                sale_info = book['saleInfo']
                details = {
                    'title': volume_info.get('title', 'No title available'),
                    'description': volume_info.get('description', 'No description available'),
                    'authors': volume_info.get('authors', []),
                    'categories': volume_info.get('categories', []),
                    'isbn_10': volume_info.get('industryIdentifiers', [{}])[0].get('identifier'),  # added isbn
                    'buy_link': volume_info.get('previewLink', 'No buy link available'), # Modified this line
                    'maturity_rating': volume_info.get('maturityRating', 'Not specified'),
                    'image': volume_info.get('imageLinks', {}).get('thumbnail', book_image_default),
                    'google_books_id': book.get('id', ''),  # Add this line
                }
                book_details.append(details)
            return book_details
    return []

@app.route('/book_details', methods=['POST'])
def get_book_details():
    data = request.json
    if not data:
        abort(400, description="No data provided.")
    title = data.get('title', None)
    if not title:
        abort(400, description="Book title is required.")
    author = data.get('author', None)

    try:
        gb_book_details = get_book_details_google_books(title, author)
    except Exception as e:
        abort(500, description=f"Error while retrieving details from Google Books: {str(e)}")

    try:
        ol_book_detail = get_book_details_open_library(title)
    except Exception as e:
        abort(500, description=f"Error while retrieving details from Open Library: {str(e)}")

    combined_book_details = []

    # Use a set to track ISBNs and avoid duplicates
    seen_isbns = set()

    for gb_detail in gb_book_details:
        # If we've already seen this ISBN, skip this book
        if gb_detail['isbn_10'] in seen_isbns:
            continue

        if (gb_detail['title'].lower() == ol_book_detail['title'].lower() and
                set(gb_detail['authors']).intersection(set(ol_book_detail['authors']))):
            combined_detail = gb_detail.copy()
            combined_detail.update(ol_book_detail)
            combined_book_details.append(combined_detail)
            seen_isbns.add(gb_detail['isbn_10'])  # add this ISBN to our set
        else:
            combined_book_details.append(gb_detail)
            seen_isbns.add(gb_detail['isbn_10'])  # add this ISBN to our set

    if not combined_book_details:
        abort(404, description="No book details found for the given title or author.")

    return jsonify(combined_book_details)

def generate_detailed_description(book_details):
    # Create a prompt for the GPT-3 model
    prompt = f"Generate a Max 6 sentence description for the book '{book_details['title']}' by '{book_details['authors']}', which falls under the categories: {', '.join(book_details['categories'])}. The book's description is as follows: {book_details['description']} ."

    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=150,
        temperature=0.7
    )

    # Return the generated description
    return response.choices[0].text.strip()

def chat_with_gpt(message):
    try:
        prompt_type = 'surprise_me' if 'surprise' in message.lower() else 'chatbot'
        system_message, user_message = "", ""

        if prompt_type == 'chatbot':
            system_message = (f"You are Seren, a helpful assistant who provides book recommendations. Your goal "
                              f"is to recommend books based on the user's recent reading, '{message}'. Consider "
                              "cross-genre recommendations, similar writing styles, unconventional recommendations, "
                              "author connections, emerging trends, and culturally diverse recommendations. "
                              "You are capable of learning about books using Google Books and OpenLibrary APIs.")
            user_message = (f"I just finished reading {message}. I'm interested in cross-genre recommendations, "
                            "books with similar writing styles, unconventional but well-rated books, authors connected "
                            "to the one I've read, emerging trends in the literary world, and culturally diverse literature. "
                            "Can you recommend a few books that I might enjoy?")
        elif prompt_type == 'surprise_me':
            system_message = (f"You are Seren, a helpful assistant who provides serendipitous book recommendations. "
                              f"Your goal is to recommend unexpected but interesting books to the user based on their recent "
                              f"reading, '{message}'. Consider cross-genre recommendations, similar writing styles, "
                              "unconventional recommendations, author connections, emerging trends, and culturally diverse "
                              "recommendations. You are capable of learning about books using Google Books and OpenLibrary APIs.")
            user_message = (f"I just finished reading {message}. I'm looking for a surprise. I'm open to any genre, "
                            "and I love discovering new authors and trends. Recommend something unique, diverse, "
                            "and unexpected that I might enjoy!")

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            max_tokens=300
        )

        # Extract the response from the chat model
        response_str = response.choices[0].message['content']

        # Return the response
        return response_str

    except openai.OpenAIError as e:
        print(f"Error encountered while trying to chat with GPT-3.5 Turbo: {e}")
        abort(500, description=f"Error encountered while trying to chat with GPT-3.5 Turbo: {str(e)}")

def quirky_description():
    keywords = ["whimsical", "enchanting", "delightful", "captivating",
                "imaginative", "wild", "joyful", "surprising", "breathless", "curious"]
    description = "a " + random.choice(keywords) + " adventure that will " + random.choice(keywords) + " you with its " + random.choice(
        keywords) + " characters and " + random.choice(keywords) + " storyline. It's a book that will " + random.choice(keywords) + " you from start to finish."
    return description

# Chatbot API endpoint
@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    if not data:
        abort(400, description="No data provided.")

    book_title = data.get('book_title', None)
    author_name = data.get('author_name', None)
    print(f"{book_title} and {author_name} :Details by user")
    if not book_title or not author_name:
        abort(400, description="Both book title and author name are required.")

    try:
        book_details = get_book_details_open_library(book_title)
    except Exception as e:
        abort(500, description=f"Error while retrieving book details: {str(e)}")

    user_id = session.get('user_id', None)
    if user_id is None:
        abort(400, description="No user ID found in the session.")

    user_recommendations = user_history.get(user_id, None)
    if user_recommendations is None:
        abort(400, description="No user history found for the provided user ID.")

    try:
        book_recommendations = chat_with_gpt(f"Recently read: {book_title} by {author_name}")
    except Exception as e:
        abort(500, description=f"Error while generating book recommendations: {str(e)}")

    if book_recommendations is None:
        abort(500, description="There was a problem generating book recommendations. Please try again later.")
    
    recommendations_list = book_recommendations.split('\n')
    recommendations = []

    valid_recommendations = 0

    for i, recommendation in enumerate(recommendations_list):
        # Skip the introduction and any blank lines
        if not recommendation or recommendation.startswith("Based on"):
            continue

        # Remove the initial '1. ', '2. ', etc.
        recommendation = re.sub(r'^\d+\.\s*', '', recommendation)

        # Determine the separator for the book title and author
        separator = " by " if " by " in recommendation else " - " if " - " in recommendation else None

        # Skip any recommendation that doesn't have a recognized separator in it
        if separator is None:
            continue

        parts = recommendation.split(separator)
        book_title_recommended = parts[0]
        author_name_recommended = parts[1]

        # Check if the recommended book has already been recommended to the user
        if book_title_recommended.lower() in user_recommendations:
            continue

        # We have a valid recommendation, so increment the count
        valid_recommendations += 1

        # If we've processed 3 valid recommendations, break the loop
        if valid_recommendations == 3:
            break

        recommended_book_details = get_book_details_open_library(book_title_recommended)
        detailed_description = generate_detailed_description(recommended_book_details)
        recommendations.append({
            'book_title': book_title_recommended,
            'author_name': author_name_recommended,
            'description': detailed_description,
            'image': recommended_book_details['image'],
            'canonicalVolumeLink': recommended_book_details.get('buy_link'),
            'book_link': recommended_book_details.get('buy_link')
        })

         # Add the recommended book to the user's history
        user_history[user_id].append(book_title_recommended.lower())
        # Update the user's recommendations in MongoDB
        mongodb.add_recommendation(user_id, book_title_recommended)

    # Filter out the book the user just read
    recommendations = [rec for rec in recommendations if rec['book_title'].lower() != book_title.lower()]

    # Print user ID and history
    print("User ID:", user_id)
    print("User History:", user_history[user_id])

    return jsonify({
        'message': f"{book_title} by {author_name} is truly a marvelous piece of work. The way {author_name} has woven the story is both {quirky_description()}. It's a perfect blend of {', '.join(book_details['categories'])} that takes the reader on an unforgettable journey.",
        'recommendations': recommendations
    })

@app.route('/set_favorites', methods=['POST'])
def set_favorites():
    data = request.get_json()
    favorite_author = data.get('favorite_author')
    favorite_genre = data.get('favorite_genre')

    user_id = session.get('user_id', None)
    if user_id is None:
        abort(400, description="No user ID found in the session.")

    # Save the favorite author and genre to MongoDB
    mongodb.save_user_favorites(user_id, favorite_author, favorite_genre)

    return jsonify({'message': 'Favorites saved successfully.'})


@app.route('/surprise_me', methods=['POST'])
def surprise_me():
    data = request.get_json()
    book_title = data.get('book_title', None)
    author_name = data.get('author_name', None)
    print(f"{book_title} and {author_name} :Details by user")
    if not book_title or not author_name:
        return jsonify({'error': 'Both book title and author name are required.'}), 400

    book_details = get_book_details_open_library(book_title)

    if not book_details:
        return jsonify({'error': 'The book you entered does not exist.'}), 400
    
    if 'user_id' in session:
        user_id = session['user_id']
        user_recommendations = user_history[user_id]

    else:
        abort(400, description="No user ID found in the session.")
       
    favorite_author = session.get('favorite_author', None)
    favorite_genre = session.get('favorite_genre', None)

    message = f"Recently read: {book_title} by {author_name}"
    if favorite_author:
        message += f". Favorite author: {favorite_author}"
    if favorite_genre:
        message += f". Favorite genre: {favorite_genre}"

    try:
        book_recommendations = chat_with_gpt(message)
    except Exception as e:
        return jsonify({'error': f'Could not generate book recommendations. Error: {str(e)}'}), 500

    recommendations_list = book_recommendations.split('\n')

    recommendations_list = [rec for rec in recommendations_list if rec and not rec.startswith("Based on") and rec.lower() != book_title.lower() and rec.lower() not in (history.lower() for history in user_history[user_id]) and rec not in user_recommendations]

    if not recommendations_list:
        return jsonify({'error': 'No new recommendations available.'}), 400

    random_recommendation = random.choice(recommendations_list)
    user_recommendations.append(random_recommendation)
    random_recommendation = re.sub(r'^\d+\.\s*', '', random_recommendation)
    separator = " by " if " by " in random_recommendation else " - " if " - " in random_recommendation else None

    if separator is None:
        return jsonify({'error': 'Could not parse recommendation.'}), 500

    parts = random_recommendation.split(separator)
    book_title_recommended = parts[0]
    author_name_recommended = parts[1]
    recommended_book_details = get_book_details_open_library(book_title_recommended)
    detailed_description = generate_detailed_description(recommended_book_details)

    surprise_book = {
        'book_title': book_title_recommended,
        'author_name': author_name_recommended,
        'description': detailed_description,
        'image': recommended_book_details['image'],
        'canonicalVolumeLink': recommended_book_details.get('buy_link'),
        'book_link': recommended_book_details.get('buy_link')
    }
    # Update user recommendations in MongoDB
    mongodb.add_recommendation(user_id, book_title_recommended)

    print("======surprise function========")
    print("title for the book generated:--", surprise_book['book_title'])
    print("User ID:", user_id)
    print("Favorite genre: ", favorite_genre)
    print("Favorite author: ", favorite_author)
    print("User History:", user_history[user_id])
    print("======surprise function ends========")

    return jsonify({
        'message': f"Surprise! Here is a book recommendation for you: {book_title_recommended} by {author_name_recommended}. This book is {quirky_description()}. Enjoy!",
        'recommendation': surprise_book
    })

if __name__ == "__main__":
    app.run(debug=True)
