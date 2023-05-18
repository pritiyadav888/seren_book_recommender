# db.py
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

class MongoDB:
    # db.py
    def __init__(self):
            client = MongoClient(os.getenv('MONGODB_URI'))
            self.db = client[os.getenv('DB_NAME')]
            self.collection = self.db.users  # New line: now you have a collection
            # Rest of the code...

    def save_user(self, user_id):
            user_data = {"user_id": user_id, "recommendations": []}
            self.collection.insert_one(user_data)

    def get_user(self, user_id):
        user_data = self.collection.find_one({"user_id": user_id})
        if user_data is None:
            user_data = {}
        return user_data

    def add_recommendation(self, user_id, recommendation):
        print(f"Adding recommendation for user_id: {user_id}")
        timestamp = datetime.now()
        recommendation_data = {"timestamp": timestamp, "recommendation": recommendation}
        result = self.collection.update_one({"user_id": user_id}, {"$push": {"recommendations": recommendation_data}})
        print(f"Update result: {result.matched_count} matched, {result.modified_count} modified.")

mongodb = MongoDB()