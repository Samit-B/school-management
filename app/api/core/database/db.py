from pymongo import MongoClient 
import os
from bson import ObjectId
from fastapi import FastAPI, Query


# Initialize FastAPI instance
app = FastAPI()

 


MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")  
client = MongoClient(MONGO_URL)
db = client["student_db"]
collection = db["students"]

# Database & Collection
db = client["student_management"]
events_collection = db["events"]

def get_students():
    students = list(collection.find({}))  # Fetch all students including `_id`
    
    # Convert `_id` from ObjectId to string
    for student in students:
        student["_id"] = str(student["_id"])
    
    return students


async def get_events():
    events = list(events_collection.find({}))  # Fetch all events
    for event in events:
        event["_id"] = str(event["_id"])  # Convert ObjectId to string
    return events

def add_student_to_db(student_data):
    collection.insert_one(student_data)