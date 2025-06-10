from dotenv import load_dotenv
import os
from flask import Flask, redirect, request, make_response, url_for
from flask_cors import CORS
from workos import WorkOSClient
from functools import wraps

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Update CORS settings to support credentials

workos = WorkOSClient(
    api_key=os.getenv("WORKOS_API_KEY"),
    client_id=os.getenv("WORKOS_CLIENT_ID")
)

cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")

def with_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session = workos.user_management.load_sealed_session(
            sealed_session=request.cookies.get("wos_session"),
            cookie_password=cookie_password,
        )
        auth_response = session.authenticate()
        
        if auth_response.authenticated:
            return f(*args, **kwargs)

        if auth_response.authenticated is False and auth_response.reason == "no_session_cookie_provided":
            return make_response(redirect("/api/login"))  # Redirect to login instead of returning JSON

        try:
            print("Refreshing session")
            result = session.refresh()
            if result.authenticated is False:
                return make_response(redirect("/api/login"))

            response = make_response(redirect(request.url))
            response.set_cookie(
                "wos_session",
                result.sealed_session,
                secure=True,
                httponly=True,
                samesite="lax",
            )
            return response
        except Exception as e:
            print("Error refreshing session", e)
            response = make_response(redirect("/api/login"))
            response.delete_cookie("wos_session")
            return response

    return decorated_function

@app.route("/api/login")
def login():
    try:
        print("Starting login process...")  # Debug log
        print("Redirect URI:", os.getenv("WORKOS_REDIRECT_URI"))  # Debug log
        print("Client ID:", os.getenv("WORKOS_CLIENT_ID"))  # Debug log
        
        authorization_url = workos.user_management.get_authorization_url(
            provider="authkit",
            redirect_uri=os.getenv("WORKOS_REDIRECT_URI"),
            state=os.urandom(16).hex()
        )
        print("Generated authorization URL:", authorization_url)  # Debug log
        
        # Return a redirect response with logging
        print("Redirecting to WorkOS auth page...")
        return redirect(authorization_url)
    except Exception as e:
        print("Error in login route:", str(e))  # Debug log
        return redirect("http://localhost:5173?error=login_failed")

@app.route("/api/callback")
def callback():
    code = request.args.get("code")
    print("Received callback with code:", code)  # Debug log

    try:
        print("Attempting to authenticate with code...")  # Debug log
        auth_response = workos.user_management.authenticate_with_code(
            code=code,
            session={"seal_session": True, "cookie_password": cookie_password},
        )
        print("Authentication successful, creating response...")  # Debug log

        response = make_response(redirect("http://localhost:5173"))  # Redirect to frontend
        print("Setting cookie with sealed session...")  # Debug log
        response.set_cookie(
            "wos_session",
            auth_response.sealed_session,
            secure=True,
            httponly=True,
            samesite="lax",
        )
        return response

    except Exception as e:
        print("Error authenticating with code:", str(e))  # More detailed error logging
        print("Cookie password length:", len(cookie_password) if cookie_password else "None")  # Debug cookie password
        print("Cookie password:", cookie_password)  # Debug cookie password value
        return redirect("http://localhost:5173?error=auth_failed")  # Redirect with error

@app.route("/api/logout")
def logout():
    print("\n=== LOGOUT ROUTE HIT ===")
    try:
        # Get the session cookie
        session_cookie = request.cookies.get("wos_session")
        if not session_cookie:
            print("No session cookie found")
            return make_response({"url": "http://localhost:5173"})

        # Try to get the logout URL before invalidating the session
        try:
            session = workos.user_management.load_sealed_session(
                sealed_session=session_cookie,
                cookie_password=cookie_password,
            )
            logout_url = session.get_logout_url()
            print("Got logout URL:", logout_url)
        except Exception as e:
            print("Error getting logout URL:", str(e))
            logout_url = "http://localhost:5173"

        # Create response with the URL
        response = make_response({
            "url": logout_url,
            "message": "Logging out"
        })
        
        # Clear the session cookie
        response.delete_cookie(
            "wos_session",
            secure=True,
            httponly=True,
            samesite="lax"
        )
        
        print("Cookie deleted, returning response")
        return response

    except Exception as e:
        print("ERROR in logout:", str(e))
        # Even if there's an error, try to delete the cookie
        response = make_response({"url": "http://localhost:5173"})
        response.delete_cookie("wos_session")
        return response

@app.route("/api/user")
@with_auth
def get_user():
    print("Getting user data...")  # Debug log
    session = workos.user_management.load_sealed_session(
        sealed_session=request.cookies.get("wos_session"),
        cookie_password=cookie_password,
    )
    print("Session cookie:", request.cookies.get("wos_session"))  # Debug log
    response = session.authenticate()
    print("Authentication response:", response)  # Debug log
    if response.authenticated:
        print("User data:", response.user)  # Debug log
        user_dict = {
            "id": response.user.id,
            "email": response.user.email,
            "first_name": response.user.first_name,
            "last_name": response.user.last_name
        }
        return {"user": user_dict}
    return {"error": "Not authenticated"}

if __name__ == "__main__":
    app.run(debug=True, port=5000) 