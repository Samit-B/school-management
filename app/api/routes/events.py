from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
import logging
from app.api.core.database.db import events_collection

logger = logging.getLogger(__name__)


router = APIRouter()


# ✅ Event Model
class Event(BaseModel):
    title: str
    date: str
    description: str

# ✅ Route to Add an Event
@router.post("/events/")
async def add_event(event: Event):
    event_dict = event.dict()
    result = events_collection.insert_one(event_dict)
    return {"message": "Event added successfully", "id": str(result.inserted_id)}



@router.post("/events/{event_id}")
async def delete_event(event_id: str):
    event = events_collection.find({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="event not found")

    events_collection.delete_one({"_id": ObjectId(event_id)})
    return {"message": "event deleted successfully"}
