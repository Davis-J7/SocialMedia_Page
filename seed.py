import os
from pymongo import MongoClient
from datetime import datetime, timedelta

# 1. Configuration
# Replace <password> with your actual MongoDB Atlas password
# Replace <cluster-url> with your cluster address (e.g., cluster0.abcde.mongodb.net)
MONGO_URI = "mongodb+srv://dbAdmin:mongo123!@socialmediacluster.bkc3u7c.mongodb.net/?appName=SocialMediaCluster"

def seed_database():
    try:
        # 2. Connect to Atlas
        client = MongoClient(MONGO_URI)
        db = client.SocialMediaDB
        
        print("Connected to MongoDB Atlas. Starting seed...")

        # 3. Clear existing data (Optional - use with caution!)
        db.users.delete_many({})
        db.posts.delete_many({})
        db.messages.delete_many({})
        db.stories.delete_many({})

        # 4. Seed USERS
        users_data = [
            {
                "user_id": "U2460355",
                "name": {"first": "Davis", "last": "Joby"},
                "email": "davis@example.com",
                "dob": "1998-05-20",
                "gender": "Male",
                "category": "Content Producer",
                "date_of_creation": datetime.utcnow()
            },
            {
                "user_id": "U2460352",
                "name": {"first": "Cyriac", "last": "Sebastian"},
                "email": "cyriac@example.com",
                "dob": "1997-11-12",
                "gender": "Male",
                "category": "Regular User",
                "date_of_creation": datetime.utcnow()
            }
        ]
        user_results = db.users.insert_many(users_data)
        davis_id = user_results.inserted_ids[0]
        cyriac_id = user_results.inserted_ids[1]
        print(f"Inserted {len(user_results.inserted_ids)} users.")

        # 5. Seed POSTS (Linked to Davis)
        posts_data = [
            {
                "post_id": "P101",
                "user_id": davis_id,
                "content": {
                    "media_type": "Image",
                    "text": "Check out this new E-R diagram I made!",
                    "audio": "None"
                },
                "permissions": {
                    "permission_name": "Public",
                    "accessibility": "Everyone"
                },
                "date_of_posting": datetime.utcnow()
            }
        ]
        db.posts.insert_many(posts_data)
        print("Inserted sample posts.")

        # 6. Seed MESSAGES (From Cyriac to Davis)
        messages_data = [
            {
                "message_id": "M500",
                "sender_id": cyriac_id,
                "receiver_id": davis_id,
                "content": "Hey Davis, great work on the MongoDB schema!",
                "type": "Text",
                "status": "Delivered",
                "time": datetime.utcnow()
            }
        ]
        db.messages.insert_many(messages_data)
        print("Inserted sample messages.")

        # 7. Seed STORIES (Short-lived content)
        stories_data = [
            {
                "story_id": "S99",
                "user_id": cyriac_id,
                "media": {
                    "type": "Video",
                    "audio_type": "Stereo",
                    "length": 15
                },
                "expires_at": datetime.utcnow() + timedelta(hours=24)
            }
        ]
        db.stories.insert_many(stories_data)
        print("Inserted sample stories.")

        print("\nDatabase seeding completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    seed_database()