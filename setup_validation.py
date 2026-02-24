import os
from pymongo import MongoClient
from dotenv import load_dotenv
import datetime

load_dotenv()
uri = os.getenv("MONGO_URI")

def setup_user_validation():
    client = MongoClient(uri, tlsAllowInvalidCertificates=True)
    db = client.SocialMediaDB
    
    # Define the JSON Schema Validation
    # Equivalent to SQL: 
    # CREATE TABLE users (
    #   name_first VARCHAR(255) NOT NULL,
    #   email VARCHAR(255) UNIQUE NOT NULL,
    #   dob DATE CHECK (age >= 16)
    # )
    user_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "name", "email", "password", "dob", "gender", "category", "date_of_creation"],
            "properties": {
                "user_id": {
                    "bsonType": "string",
                    "description": "must be a string and is required"
                },
                "name": {
                    "bsonType": "object",
                    "required": ["first", "last"],
                    "properties": {
                        "first": { "bsonType": "string" },
                        "last": { "bsonType": "string" }
                    }
                },
                "email": {
                    "bsonType": "string",
                    "pattern": "^.+@.+$",
                    "description": "must be a string and match the regular expression pattern"
                },
                "password": {
                    "bsonType": "string",
                    "description": "must be a string and is required"
                },
                "dob": {
                    "bsonType": "string",
                    "description": "must be a string (YYYY-MM-DD)"
                },
                "gender": {
                    "enum": ["Male", "Female", "Other"],
                    "description": "can only be one of the enum values"
                },
                "category": {
                    "bsonType": "string"
                },
                "date_of_creation": {
                    "bsonType": "date"
                }
            }
        }
    }

    try:
        # Apply validation to existing collection
        db.command({
            "collMod": "users",
            "validator": user_schema,
            "validationLevel": "strict",
            "validationAction": "error"
        })
        print("✅ Schema validation successfully applied to 'users' collection.")
        
        # Also create a UNIQUE index for email (SQL UNIQUE constraint)
        db.users.create_index("email", unique=True)
        print("✅ Unique index created for 'email'.")
        
    except Exception as e:
        print(f"❌ Error applying validation: {e}")

if __name__ == "__main__":
    setup_user_validation()
