from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
import os

load_dotenv()

class MongoDB:
    def __init__(self):
        client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = client[os.getenv('DB_NAME')]
        self.collection = self.db.users

        # Print connection status
        if client.server_info():
            print("MongoDB connected successfully.")
        else:
            print("Failed to connect to MongoDB.")

        # Create TTL index on the 'timestamp' field with the desired expiration time
        self.collection.create_index("timestamp", expireAfterSeconds=timedelta(days=1).total_seconds())

    def save_user(self, user_id):
        user_data = {"user_id": user_id, "recommendations": [], "timestamp": datetime.now()}
        self.collection.insert_one(user_data)

    def get_user(self, user_id):
        user_data = self.collection.find_one({"user_id": user_id})
        if user_data is None:
            user_data = {}
        return user_data
    
    def save_user_favorites(self, user_id, favorite_author, favorite_genre):
        self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"favorite_author": favorite_author, "favorite_genre": favorite_genre}}
        )    

    def add_recommendation(self, user_id, recommendation):
        print(f"Adding recommendation for user_id: {user_id}")
        timestamp = datetime.now()
        recommendation_data = {"timestamp": timestamp, "recommendation": recommendation}
        result = self.collection.update_one(
            {"user_id": user_id},
            {"$push": {"recommendations": recommendation_data}}
        )
        print(f"Update result: {result.matched_count} matched, {result.modified_count} modified.")

mongodb = MongoDB()
