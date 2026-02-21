import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("MONGO_URI")

try:
    client = MongoClient(uri)
    # The 'admin' command is a standard way to check if a connection is alive
    client.admin.command('ping')
    print("✅ Success! Your URI and Atlas settings are perfect.")
    
    # List databases to see if yours is there
    print(f"Databases found: {client.list_database_names()}")
    
except Exception as e:
    print(f"❌ Connection Failed: {e}")

# Select the database
db = client.SocialMediaDB

# List the collections inside SocialMediaDB
collections = db.list_collection_names()
print(f"Collections inside SocialMediaDB: {collections}")

# Count documents in the users collection
user_count = db.users.count_documents({})
print(f"Number of users found: {user_count}")