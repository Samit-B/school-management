from fastapi import APIRouter, Request, Response
from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse
import os
from dotenv import load_dotenv
import traceback
import jwt  # Import PyJWT
from authlib.jose import jwt as authlib_jwt  # Alternative JWT parser
from fastapi import Depends, HTTPException
import jwt  # PyJWT for decoding
import requests  # For fetching Google public keys
# Load environment variables
load_dotenv()

router = APIRouter()

# OAuth Configuration
oauth = OAuth()
oauth.register(
    name="google",
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID"),
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET"),
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    authorize_params=None,
    access_token_url="https://oauth2.googleapis.com/token",
    access_token_params=None,
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",  # ✅ Ensure this is correct
    client_kwargs={"scope": "openid email profile"},
    

)

@router.get("/login/google")
async def google_login(request: Request):
    """ Redirects user to Google OAuth login page """
    redirect_uri = "http://127.0.0.1:8000/auth/google/"  # Callback URL
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/")
async def google_auth(request: Request):
    try:
        print("[DEBUG] Google OAuth callback triggered")
        token = await oauth.google.authorize_access_token(request)
        print(f"[DEBUG] OAuth Token: {token}")

        id_token = token.get("id_token")
        if not id_token:
            raise ValueError("Missing id_token in OAuth response")

        # Decode JWT manually
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        print(f"[DEBUG] Decoded Token: {decoded_token}")

        # Store user in session
        request.session["user"] = decoded_token  
        print("[DEBUG] User stored in session:", request.session["user"])

        return RedirectResponse(url="/dashboard")

    except Exception as e:
        import traceback
        print(f"[ERROR] Google authentication failed:\n{traceback.format_exc()}")
        return RedirectResponse(url="/login?error=AuthFailed")

