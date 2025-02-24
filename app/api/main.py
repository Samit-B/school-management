from fastapi import FastAPI, Request, Form, Depends, HTTPException, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
import os,re
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
import requests
from bs4 import BeautifulSoup
from fastapi.middleware.cors import CORSMiddleware
from app.api.agent import run_agent, upload_pdf, ask_question, fetch_transcript,upload_excel # Ensure these functions are correctly defined

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Securely load session secret key
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "your_super_secret_key")

# Middleware for session-based authentication
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your UI's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jinja2 template setup for rendering HTML pages
templates = Jinja2Templates(directory="templates")

# Import routes
from app.api.routes.routes import router
from app.api.core.database.db import get_students
from app.api.routes.events import router as event_router
from app.api.core.database.db import events_collection
from app.api.auth.google_auth import router as google_auth_router
from fastapi.responses import FileResponse

# Include authentication routes
app.include_router(google_auth_router, prefix="/auth", tags=["auth"])

# Serve static files (CSS, JS, images, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Chatbot API Route
class ChatRequest(BaseModel):
    message: str

@app.post("/chatbot")
async def chatbot_endpoint(request: ChatRequest):
    user_message = request.message.strip()

    try:
        bot_response = run_agent(user_message)

        if not bot_response or not isinstance(bot_response, str):
            return JSONResponse(content={"reply": "Sorry, I couldn't generate a response."})

        return JSONResponse(content={"reply": bot_response})

    except Exception as e:
        print("Error in chatbot:", str(e))
        print(traceback.format_exc())
        return JSONResponse(content={"reply": "An error occurred."}, status_code=500)

# Home Route
@app.post("/upload-pdf")
async def upload_pdf_endpoint(file: UploadFile = File(...)):
    return await upload_pdf(file)

@app.post("/upload-excel")
async def upload_excel_endpoint(file: UploadFile = File(...)):
    return await upload_excel(file)

@app.get("/ask")
async def ask_question_endpoint(query: str):
    """Handles queries related to students, FAQs, URL content, and PDF summarization."""
    response = await ask_question(query)  # Ensure ask_question returns JSONResponse
    return response

# Login Page Route
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Normal Login (Username/Password)
@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "password":
        request.session["user"] = {"username": username}  # Store user in session
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

# Middleware to get the current user
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

# Dashboard Page (Session Protected)
@app.get("/dashboard")
async def dashboard_page(request: Request, user: dict = Depends(get_current_user)):
    print(f"[DEBUG] Session Data: {request.session.items()}")  # Debug session storage
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

# Student Page (Session Protected)
@app.get("/students")
async def student_page(request: Request, user: dict = Depends(get_current_user)):
    students = get_students()
    return templates.TemplateResponse("student.html", {"request": request, "students": students})

# Analytics Page (Session Protected)
@app.get("/analytics")
async def analytics_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("analytics.html", {"request": request})

# Logout Route (Clears session and redirects to login)
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()  # Clears session data
    return RedirectResponse(url="/login", status_code=303)

# Include Additional API Routes
app.include_router(router)
app.include_router(event_router)

# Events API (CRUD Operations)
from bson import ObjectId

class Event(BaseModel):
    title: str
    date: str  # Format: "YYYY-MM-DD"

@app.post("/events")
async def add_event(event: Event):
    events_collection.insert_one(event.dict())
    return {"message": "Event added successfully"}

@app.get("/eventss")
async def get_events():
    events = list(events_collection.find({}))  # Fetch all events
    for event in events:
        event["_id"] = str(event["_id"])  # Convert ObjectId to string
    return events


# New Route for URL Analysis
class URLRequest(BaseModel):
    url: str

@app.post("/analyze-url")
async def analyze_url_endpoint(request: URLRequest):
    url = request.url.strip().rstrip(".")  # Remove any trailing period

    try:
        # Fetch the content of the URL
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx and 5xx)

        # Parse the content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract text or specific data from the content
        text_content = soup.get_text()

        # Store the content for later use
        global url_content
        url_content = text_content
        return JSONResponse(content={"message": "URL content stored successfully."})

    except Exception as e:
        print("Error analyzing URL:", str(e))
        print(traceback.format_exc())
        return JSONResponse(content={"error": "An error occurred while analyzing the URL."}, status_code=500)
    
class YouTubeRequest(BaseModel):
    video_link: str

@app.post("/process-video")
async def process_video_endpoint(request: YouTubeRequest):
    video_link = request.video_link.strip()

    try:
        # Extract the video ID from the URL
        video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", video_link)
        if not video_id_match:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL.")

        video_id = video_id_match.group(1)

        # Fetch the transcript using the video ID
        transcript = fetch_transcript(video_id)
        if transcript:
            return JSONResponse(content={"transcript": transcript})
        else:
            raise HTTPException(status_code=500, detail="Unable to fetch the video transcript.")

    except Exception as e:
        print("Error processing video:", str(e))
        raise HTTPException(status_code=500, detail="An error occurred while processing the video.")