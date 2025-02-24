import os
import requests
import json
import re
import pandas as pd
import shutil
import fitz  # PyMuPDF to handle PDF files
from io import BytesIO
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_groq import ChatGroq
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from app.api.core.database.db import get_students,add_student_to_db  # Fetch student data
from langchain_huggingface import HuggingFaceEmbeddings  # Updated import
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter

UPLOAD_DIRECTORY = "uploads"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

# Load FAQ data
with open("faq.json", "r") as file:
    FAQ_DATA = json.load(file)

# Load API key from environment variables
GROQ_API_KEY=os.getenv("GROQ_API_KEY"),
# Initialize Groq model
llm = ChatGroq(model_name="llama3-8b-8192")

# Initialize HuggingFace embeddings with a specified model name
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Global in-memory storage for the session
vector_db = None
stored_content = ""

def store_text_in_faiss(text):
    """Splits and stores text in FAISS vector storage."""
    global vector_db
    try:
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        documents = text_splitter.create_documents([text])
        vector_db = FAISS.from_documents(documents, embeddings)
        print("Text stored in FAISS successfully.")
    except Exception as e:
        print(f"Error storing text in FAISS: {str(e)}")

def retrieve_relevant_info(query):
    """Retrieves relevant context from stored FAISS vectors."""
    global vector_db
    if vector_db:
        try:
            docs = vector_db.similarity_search(query, k=2)
            context = " ".join([doc.page_content for doc in docs])
            print(f"Retrieved context: {context}")
            return context
        except Exception as e:
            print(f"Error retrieving info from FAISS: {str(e)}")
    return ""

def get_student_info(name: str):
    """Fetch student details from the database."""
    students = get_students()
    print(f"Available students: {[student['name'] for student in students]}")  # Debugging line
    for student in students:
        if student["name"].strip().lower() == name.strip().lower():
            return student
    return None

def fetch_and_parse_url(url):
    """Fetches and extracts main content from a given URL."""
    global stored_content
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        content_div = soup.find('div', {'id': 'mw-content-text'}) or soup.find('article')
        if content_div:
            text_content = ' '.join(para.get_text() for para in content_div.find_all('p'))
            stored_content = text_content[:2000]
            store_text_in_faiss(stored_content)
            return {"message": "URL content stored successfully."}
    except Exception as e:
        print(f"Error fetching and parsing URL: {str(e)}")
        return {"error": str(e)}

def fetch_transcript(video_id):
    """Fetches transcript from a YouTube video."""
    global stored_content
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        video_transcript = "\n".join([part['text'] for part in transcript])
        stored_content = video_transcript
        store_text_in_faiss(stored_content)
        return {"message": "Video transcript stored successfully."}
    except Exception as e:
        print(f"Error fetching transcript: {str(e)}")
        return {"error": "Could not retrieve the transcript. Please ensure the video has subtitles enabled."}

async def upload_pdf(file: UploadFile = File(...)):
    """Handles PDF uploads and stores extracted text in FAISS."""
    global stored_content
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    try:
        file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())
        pdf_document = fitz.open(file_location)
        pdf_text = "".join(page.get_text("text") for page in pdf_document)
        stored_content = pdf_text
        store_text_in_faiss(stored_content)
        return JSONResponse(content={"message": "PDF uploaded!", "pdf_text": pdf_text})
    except Exception as e:
        print(f"Error uploading PDF: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    
async def upload_excel(file: UploadFile = File(...)):
    """Handles Excel uploads and stores student details in the database."""
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    try:
        file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
        with open(file_location, "wb") as f:
            f.write(await file.read())
        df = pd.read_excel(file_location)
        for index, row in df.iterrows():
            student_data = {
                "name": row["name"],
                "student_class": row["student_class"],
                "dob": row["dob"],
                "gender": row["gender"],
                "city": row["city"],
                "marks": row["marks"]
            }
            add_student_to_db(student_data)
        return JSONResponse(content={"message": "Student details added to the database successfully!"})
    except Exception as e:
        print(f"Error uploading Excel: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

def run_agent(query: str):
    """Handles user queries and generates responses."""
    query = query.strip().lower()

    try:
        # Handle URL queries
        if "http" in query:
            url = re.search(r"https?://[^\s]+", query).group().rstrip(".,!?")
            if "youtube.com" in url or "youtu.be" in url:
                video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
                if video_id:
                    return json.dumps(fetch_transcript(video_id.group(1)))
            return json.dumps(fetch_and_parse_url(url))

        # Handle student queries
        if "student" in query or "students" in query:
            students = get_students()
            student_data = "\n".join([f"{student['name']}: {student}" for student in students])
            messages = [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content=f"Context: {student_data}\nQuery: {query}")
            ]
            response = llm.invoke(messages)
            return response.content

        # Handle summarization queries
        if "summarize" in query:
            messages = [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content=f"Context: {stored_content}\nQuery: Summarize the content in 20 words.")
            ]
            response = llm.invoke(messages)
            return response.content

        # Handle general queries
        if not stored_content:
            messages = [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content=f"Query: {query}")
            ]
            response = llm.invoke(messages)
            return response.content

        # Retrieve relevant context from FAISS
        retrieved_context = retrieve_relevant_info(query)
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=f"Context: {retrieved_context}\nQuery: {query}")
        ]

        response = llm.invoke(messages)
        print(f"LLM Response: {response.content}")
        return response.content

    except Exception as e:
        print(f"Error processing query: {str(e)}")
        return json.dumps({"error": "An error occurred while processing the query."})

async def ask_question(query: str):
    """Processes user queries and returns responses."""
    query = query.strip().lower()

    try:
        # Check if query matches FAQ
        if query in FAQ_DATA:
            return JSONResponse(content={"response": FAQ_DATA[query]})

        # Check if query is about a student
        student_name = next((s["name"].strip().lower() for s in get_students() if s["name"].strip().lower() in query), None)
        if student_name:
            student_data = get_student_info(student_name)
            return JSONResponse(content={"response": student_data if student_data else "Student not found"})

        # Handle summarization queries
        if "summarize" in query:
            messages = [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content=f"Context: {stored_content}\nQuery: Summarize the content in 20 words.")
            ]
            response = llm.invoke(messages)
            return JSONResponse(content={"response": response.content})

        # Handle general queries
        if not stored_content:
            messages = [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content=f"Query: {query}")
            ]
            response = llm.invoke(messages)
            return JSONResponse(content={"response": response.content})

        # Retrieve relevant context from FAISS
        retrieved_context = retrieve_relevant_info(query)
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=f"Context: {retrieved_context}\nQuery: {query}")
        ]

        response = llm.invoke(messages)
        print(f"LLM Response: {response.content}")
        return JSONResponse(content={"response": response.content})

    except Exception as e:
        print(f"Error processing question: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "An error occurred while processing the question."})
