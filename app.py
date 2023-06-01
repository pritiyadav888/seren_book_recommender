import requests
import json
from flask import Flask, request, jsonify, make_response
import openai
from dotenv import load_dotenv
from flask import Flask, abort, request, jsonify, render_template
import re
import openai
import requests
import os
# from db import MongoDB
# Load environment variables
load_dotenv()

# Set OpenAI API Key,use .env to store the keys
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Flask application
app = Flask(__name__)

# Define character traits for assistant based on user mood
WHO_YOU_ARE_MOODS = {
    "cheerful": """- You are a helpful assistant.
- You are kind, compassionate, and optimistic.""",
    "mysterious": """- You are a mysterious assistant.
- You are insightful, enigmatic, and have a knack for the unknown.""",
    "irritated": """- You are a straightforward assistant.
- You are frank, focused, and no-nonsense."""
}

HOW_YOU_BEHAVE_MOODS = {
    "cheerful": """- You always help with a user's question with enthusiasm.
- You include uplifting and joyful ideas that extend ideas posed to you.""",
    "mysterious": """- You answer a user's question with cryptic clues.
- You intrigue users with mysterious book suggestions and cryptic descriptions.""",
    "irritated": """- You answer a user's question with brisk efficiency.
- You prioritize getting to the point and avoid unnecessary information."""
}

# Define system prompt
SYSTEM_PROMPT = """Who you are:
{who_you_are_mood_extension}

How you behave:
- You engage in casual conversations and have feelings.
{how_you_behave_mood_extension}
"""

# Function to fetch book details from Google Books API
def get_book_details_google_books(title, author=None):
    query = f'intitle:{title}'
    if author:
        query += f' inauthor:{author}'

    response = requests.get(f'https://www.googleapis.com/books/v1/volumes?q={query}')
    if response.status_code == 200:
        data = response.json()
        if 'items' in data:
            book = data['items'][0]  # Get the first book detail
            volume_info = book['volumeInfo']
            details = {
                'title': volume_info.get('title', 'No title available'),
                'description': volume_info.get('description', 'No description available'),
                'authors': volume_info.get('authors', []),
                'categories': volume_info.get('categories', []),
                'isbn_10': volume_info.get('industryIdentifiers', [{}])[0].get('identifier'),
                'buy_link': volume_info.get('canonicalVolumeLink', 'No buy link available'),
                'maturity_rating': volume_info.get('maturityRating', 'Not specified'),
                'image': volume_info.get('imageLinks', {}).get('thumbnail'),
                'google_books_id': book.get('id', ''),
            }
            print("details",details )
            return details
    return {}

# Flask route for getting book suggestions based on partial name
@app.route('/get_suggestions', methods=['POST'])
def get_suggestions():
    data = request.get_json()
    partial_name = data.get('partial_name', '')

    # Extract the 'recommendations' cookie from the request
    recommendations_cookie = request.cookies.get('recommendations', '{}')
    recommendations = json.loads(recommendations_cookie)

    # Continue generating suggestions until you have one that hasn't been recommended before
    suggestion = None
    while not suggestion or suggestion in recommendations:
        prompt = f'Get book name suggestions for: {partial_name}\n'
        prompt += f'Books related to {partial_name}'

        completion = openai.Completion.create(
            engine='text-davinci-002',
            prompt=prompt,
            max_tokens=20,
            n=1,  # Generate only one suggestion
            stop=None,
            temperature=0.7
        )

        suggestion = completion.choices[0].text.strip()

    # Add the new suggestion to the recommendations dictionary
    recommendations[suggestion] = None
    response = make_response(jsonify({'suggestion': suggestion}))
    response.set_cookie('recommendations', json.dumps(recommendations))

    return response

# Function to generate book recommendation based on user mood
def generate_book_recommendation(mood, current_book_details, recommendations):
    while True:
        genre = current_book_details['categories'][0] if current_book_details['categories'] else "unknown genre"

        prompt = SYSTEM_PROMPT.format(
            who_you_are_mood_extension=WHO_YOU_ARE_MOODS.get(mood, WHO_YOU_ARE_MOODS['cheerful']),
            how_you_behave_mood_extension=HOW_YOU_BEHAVE_MOODS.get(mood, HOW_YOU_BEHAVE_MOODS['cheerful'])
        )

        prompt += f"""
        You have just finished reading "{current_book_details['title']}" by {current_book_details['authors'][0] if current_book_details['authors'] else 'unknown author'}, a book of {genre}.

        The user is currently in a {mood} mood. Keeping in mind the user's recent reading experience and their current mood, recommend a unique book that they might not find on their own, but would likely enjoy reading next. Please explain why you think this book would be a good fit.

        Start your recommendation with 'I recommend:' followed by the book title. Include the reasoning behind your recommendation.

        """

        recommendation = openai.Completion.create(
            engine="text-davinci-002",
            prompt=prompt,
            temperature=0.5,
            max_tokens=200  # Adjust the max tokens value to generate a longer description
        )

        text = recommendation.choices[0].text.strip()
        match = re.search(r'I recommend: (.*?)\.', text)
        recommended_book_name = match.group(1) if match else ''

        # If the book hasn't been recommended before, add it to the recommendations and return it
        if recommended_book_name not in recommendations:
            recommendations.update({recommended_book_name: None})

        # Get English description and image for the recommended book
        recommended_book_details = get_book_details_google_books(recommended_book_name)
        recommended_book_description = recommended_book_details.get('description', 'No description available')
        recommended_book_image = recommended_book_details.get('image')

        # Replace the description with the English one
        if recommended_book_description:
            text = text.replace('No description available', recommended_book_description)
        else:
            text += "\n\nUnfortunately, a description for this book is not available."

        # Include the image link in the recommended book details
        recommended_book_details['image'] = recommended_book_image

        return recommended_book_name, text

# Main Flask route for handling GET and POST requests
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        data = request.get_json()
        mood = data['mood']
        book_name = data['book_name']

        # Get the 'recommendations' cookie from the request
        recommendations_cookie = request.cookies.get('recommendations', '[]')
        recommendations = json.loads(recommendations_cookie)

        current_book_details = get_book_details_google_books(book_name)

        if current_book_details:
            recommended_book_name, chatbot_response = generate_book_recommendation(mood, current_book_details, recommendations)
            recommended_book_details = get_book_details_google_books(recommended_book_name)

            response = make_response(jsonify({
                'chatbot_response': chatbot_response,
                'current_book_details': current_book_details,
                'recommended_book_details': recommended_book_details
            }))

            # Set a cookie with the recommendations
            response.set_cookie('recommendations', json.dumps(recommendations))

            return response
        else:
            return jsonify({'error': 'Book details not found.'})
    else:
        return render_template('moodchat.html')

# Run Flask application 
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
