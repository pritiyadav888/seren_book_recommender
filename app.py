from flask import Flask, request, jsonify, render_template
import re
import random
import openai
import requests
import os

app = Flask(__name__, template_folder='templates',static_url_path='/static')
openai.api_key = os.getenv('OPENAI_API_KEY')


@app.route('/')
def index():
    recommendations = []  # start with an empty list of recommendations
    return render_template('chat.html', recommendations=recommendations)

book_image_default = 'static/default.png'  # default placeholder image


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
                    'buy_link': volume_info.get('selfLink', 'No buy link available'),
                    'maturity_rating': volume_info.get('maturityRating', 'Not specified'),
                    'image': volume_info.get('imageLinks', {}).get('thumbnail', book_image_default),
                    'google_books_id': book.get('id', ''),  # Add this line
                }
                book_details.append(details)
            return book_details
    return []

@app.route('/book_details', methods=['POST'])
def get_book_details():
    title = request.json['title']
    author = request.json.get('author')

    gb_book_details = get_book_details_google_books(title, author)
    ol_book_detail = get_book_details_open_library(title)

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

    for book in combined_book_details:
        print(book['title'])

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

# Function to chat with GPT-3 model
def chat_with_gpt(message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are Seren, a helpful assistant who provides very serendipitous book recommendations not random. Your goal is to recommend unexpected but interesting books to the user based on their recent reading. Do not reply to any other topic than books. You are capable of learning about books using Google Books and OpenLibrary APIs. ANSWER RECOMMENDATION IN A LIST 1- 3"},
            {"role": "user", "content": message},
        ],
        max_tokens=300  # Increase the number of tokens
    )
    # Extract the response from the chat model
    response_str = response.choices[0].message['content']

    # Return the response
    return response_str



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
    book_title = data.get('book_title', None)
    author_name = data.get('author_name', None)

    if not book_title or not author_name:
        return jsonify({'error': 'Both book title and author name are required.'}), 400

    book_details = get_book_details_open_library(book_title)

    # Modify the chat_with_gpt function call to include the user's recent reading
    book_recommendations = chat_with_gpt(f"Recently read: {book_title} by {author_name}")

    recommendations_list = book_recommendations.split('\n')
    recommendations = []
    print(f"Full recommendations list: {recommendations_list}")

    valid_recommendations = 0

    for i, recommendation in enumerate(recommendations_list):
        # Skip the introduction and any blank lines
        print(f"Processing recommendation: {recommendation}")
        if not recommendation or recommendation.startswith("Based on"):
            continue

        # Remove the initial '1. ', '2. ', etc.
        recommendation = re.sub(r'^\d+\.\s*', '', recommendation)

        # Determine the separator for the book title and author
        separator = " by " if " by " in recommendation else " - " if " - " in recommendation else None

        # Skip any recommendation that doesn't have a recognized separator in it
        if separator is None:
            print(f"Could not parse recommendation: {recommendation}")
            continue

        parts = recommendation.split(separator)
        book_title_recommended = parts[0]
        author_name_recommended = parts[1]
        
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
            'canonicalVolumeLink': recommended_book_details.get('buy_link'),  # add this line
        })

        print(f"Recommendation {i}: {book_title_recommended} by {author_name_recommended}")

    # Filter out the book the user just read
    recommendations = [rec for rec in recommendations if rec['book_title'].lower() != book_title.lower()]

    return jsonify({
        'message': f"{book_title} by {author_name} is truly a marvelous piece of work. The way {author_name} has woven the story is both {quirky_description()}. It's a perfect blend of {', '.join(book_details['categories'])} that takes the reader on an unforgettable journey.",
        'recommendations': recommendations
    })



if __name__ == "__main__":
    app.run(debug=True)

