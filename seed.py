import os
import random
from pymongo import MongoClient
from datetime import datetime, timedelta

import app

# 1. Configuration
# Note: In a production environment, use environment variables for the URI
MONGO_URI = "mongodb+srv://dbAdmin:mongo123!@socialmediacluster.bkc3u7c.mongodb.net/?appName=SocialMediaDB"

def seed_database():
    try:
        # 2. Connect to Atlas
        client = MongoClient(MONGO_URI)
        db = client.SocialMediaDB
        
        print("Connected to MongoDB Atlas. Starting seed...")

        # 3. Clear existing data
        db.users.delete_many({})
        db.posts.delete_many({})
        db.messages.delete_many({})
        db.stories.delete_many({})

        # --- DATA GENERATION HELPER ---
        first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa", "Davis", "Cyriac"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Joby", "Sebastian"]
        categories = ["Regular User", "Content Producer", "Business Owner", "Influencer", "Artist"]
        genders = ["Male", "Female", "Other"]

        users_to_create = []
        
        # 4. Generate 25 Users
        for i in range(25):
            fname = first_names[i % len(first_names)]
            lname = last_names[i % len(last_names)]
            email = f"{fname.lower()}.{lname.lower()}{i}@example.com"
            
            user = {
                "user_id": f"U{random.randint(1000000, 9999999)}",
                "name": {"first": fname, "last": lname},
                "email": email,
                "password": "password123", # Default password for all seeded users
                "dob": (datetime(1980, 1, 1) + timedelta(days=random.randint(0, 10000))).strftime('%Y-%m-%d'),
                "gender": random.choice(genders),
                "category": random.choice(categories),
                "date_of_creation": datetime.utcnow() - timedelta(days=random.randint(1, 365))
            }
            users_to_create.append(user)

        user_results = db.users.insert_many(users_to_create)
        user_ids = user_results.inserted_ids
        print(f"✅ Inserted {len(user_ids)} users.")

        # 5. Generate POSTS for each user
        posts_to_create = []
        post_contents = [
            "Just finished a great workout!", "Learning MongoDB is fun.", "Check out this amazing sunset.", 
            "Coding late at night...", "Coffee is my best friend.", "New project coming soon!",
            "Had an awesome weekend!", "Exploring new technologies.", "Does anyone have any book recommendations?",
            "What a beautiful day to be alive!", "Success is a journey, not a destination.", "Consistency is key."
        ]

        for user_id in user_ids:
            # Each user gets 1-3 posts
            for p in range(random.randint(1, 3)):
                post = {
                    "post_id": f"P{random.randint(100, 9999)}",
                    "user_id": user_id,
                    "content": {
                        "media_type": random.choice(["Image", "Video", "Text"]),
                        "text": random.choice(post_contents),
                        "audio": "None"
                    },
                    "permissions": {
                        "permission_name": "Public",
                        "accessibility": random.choice(["Everyone", "Friends"])
                    },
                    "date_of_posting": datetime.utcnow() - timedelta(days=random.randint(0, 30))
                }
                posts_to_create.append(post)
        
        db.posts.insert_many(posts_to_create)
        print(f"✅ Inserted {len(posts_to_create)} posts.")

        # 6. Generate MESSAGES for each user
        messages_to_create = []
        msg_texts = ["Hey, how are you?", "Did you see my last post?", "Great job!", "Let's catch up soon.", "Thanks for the help!"]

        for sender_id in user_ids:
            # Each user sends a message to 2 random people
            recipients = random.sample([uid for uid in user_ids if uid != sender_id], 2)
            for receiver_id in recipients:
                msg = {
                    "message_id": f"M{random.randint(1000, 9999)}",
                    "sender_id": sender_id,
                    "receiver_id": receiver_id,
                    "content": random.choice(msg_texts),
                    "type": "Text",
                    "status": random.choice(["Delivered", "Read", "Unread"]),
                    "time": datetime.utcnow() - timedelta(minutes=random.randint(1, 10000))
                }
                messages_to_create.append(msg)

        db.messages.insert_many(messages_to_create)
        print(f"✅ Inserted {len(messages_to_create)} messages.")

        # 7. Generate STORIES for each user
        stories_to_create = []
        for user_id in user_ids:
            # Each user gets 1 story
            created_at = datetime.utcnow() - timedelta(hours=random.randint(0, 48))
            story = {
                "story_id": f"S{random.randint(100, 999)}",
                "user_id": user_id,
                "media": {
                    "type": random.choice(["Image", "Video"]),
                    "audio_type": "Stereo",
                    "length": random.randint(5, 30)
                },
                "created_at": created_at,
                "expires_at": created_at + timedelta(hours=24)
            }
            stories_to_create.append(story)

        db.stories.insert_many(stories_to_create)
        print(f"✅ Inserted {len(stories_to_create)} stories.")

        print("\n🚀 Database seeding completed successfully with 25 interconnected users!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    seed_database()
