from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

try:
    client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ Successfully connected to MongoDB!")
    
    db = client["privacy_policy_db"]
    
    # Test questions
    questions_count = db["questions"].count_documents({})
    print(f"✅ Found {questions_count} questions")
    
    # Test templates
    templates_count = db["templates"].count_documents({})
    print(f"✅ Found {templates_count} templates")
    
    if questions_count >= 10 and templates_count >= 2:
        print("✅ MongoDB setup is complete and correct!")
    else:
        print("⚠️  Warning: Expected at least 10 questions and 2 templates")
    
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")