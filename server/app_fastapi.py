from typing import Optional, Callable, Any, cast
from fastapi import FastAPI, Response, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from workos import WorkOSClient
from dotenv import load_dotenv
import os
from functools import wraps

load_dotenv()

app = FastAPI()

# Configure CORS with specific origin and credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workos = WorkOSClient(
    api_key=os.getenv("WORKOS_API_KEY"),
    client_id=os.getenv("WORKOS_CLIENT_ID")
)

cookie_password = os.getenv("WORKOS_COOKIE_PASSWORD")

# Pydantic models for responses
class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserData(BaseModel):
    user: UserResponse

class LogoutResponse(BaseModel):
    url: str
    message: Optional[str] = None

def with_auth(f: Callable[..., Any]):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Find the request parameter either in args or kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        if request is None and 'request' in kwargs:
            request = kwargs['request']
            
        if request is None:
            raise ValueError("No Request object found in function arguments")
            
        session = workos.user_management.load_sealed_session(
            sealed_session=request.cookies.get("wos_session") or "",
            cookie_password=cookie_password,
        )
        auth_response = session.authenticate()
        
        if auth_response.authenticated:
            return await f(*args, **kwargs)

        if auth_response.authenticated is False and auth_response.reason == "no_session_cookie_provided":
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated", "redirect": "/api/login"}
            )

        try:
            result = session.refresh()
            if result.authenticated is False:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Session expired", "redirect": "/api/login"}
                )

            response = JSONResponse(content={"message": "Session refreshed"})
            response.set_cookie(
                "wos_session",
                result.sealed_session,
                secure=True,
                httponly=True,
                samesite="lax",
            )
            return response
        except Exception as e:
            return JSONResponse(
                status_code=401,
                content={"error": "Session refresh failed", "redirect": "/api/login"}
            )

    return decorated_function

@app.get("/api/login")
async def login():
    try:
        authorization_url = workos.user_management.get_authorization_url(
            provider="authkit",
            redirect_uri=os.getenv("WORKOS_REDIRECT_URI"),
            state=os.urandom(16).hex()
        )
        # Return a redirect response that the frontend can handle
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Login failed", "redirect": "http://localhost:5173?error=login_failed"}
        )

@app.get("/api/callback")
async def callback(request: Request):
    code = request.query_params.get("code") or ""
    try:
        session_config = {
            "seal_session": True,
            "cookie_password": cookie_password
        }
        
        auth_response = workos.user_management.authenticate_with_code(
            code=code,
            session=cast(Any, session_config),
        )

        # Create a redirect response
        response = RedirectResponse(url="http://localhost:5173")
        if auth_response.sealed_session is not None:
            response.set_cookie(
                "wos_session",
                auth_response.sealed_session,
                secure=True,
                httponly=True,
                samesite="lax",
            )
        return response

    except Exception as e:
        print("Error authenticating with code", e)
        return RedirectResponse(url="http://localhost:5173?error=auth_failed")

@app.get("/api/logout", response_model=LogoutResponse)
@with_auth
async def logout(request: Request):
    try:
        session_cookie = request.cookies.get("wos_session")
        logout_url = "http://localhost:5173"
        
        if session_cookie:
            try:
                session = workos.user_management.load_sealed_session(
                    sealed_session=session_cookie,
                    cookie_password=cookie_password,
                )
                logout_url = session.get_logout_url()
            except Exception:
                pass

        response = JSONResponse(content=LogoutResponse(url=logout_url, message="Logging out").dict())
        response.delete_cookie(
            "wos_session",
            secure=True,
            httponly=True,
            samesite="lax"
        )
        return response
    except Exception as e:
        response = JSONResponse(content=LogoutResponse(url="http://localhost:5173").dict())
        response.delete_cookie("wos_session")
        return response

@app.get("/api/user", response_model=UserData)
@with_auth
async def get_user(request: Request):
    try:
        session = workos.user_management.load_sealed_session(
            sealed_session=request.cookies.get("wos_session") or "",
            cookie_password=cookie_password,
        )
        response = session.authenticate()
        if response.authenticated:
            user_dict = {
                "id": response.user.id,
                "email": response.user.email,
                "first_name": response.user.first_name,
                "last_name": response.user.last_name
            }
            return {"user": user_dict}
        raise HTTPException(status_code=401, detail="Not authenticated")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/api/dashboard")
@with_auth
async def dashboard(request: Request):
    try:
        session = workos.user_management.load_sealed_session(
            sealed_session=request.cookies.get("wos_session") or "",
            cookie_password=cookie_password,
        )
        response = session.authenticate()
        if response.authenticated:
            # Log the user data to help debug
            print("User data:", response.user)
            print("FULL RESPONSE:", response)
            print("USER ROLE:", response.user.role)
            print("USER PERMISSIONS:", response.user.permissions)   
            
            return {
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                    "first_name": response.user.first_name,
                    "last_name": response.user.last_name,
                    "role": response.user.role,
                    "permissions": response.user.permissions
                }
            }
        print("Authentication failed:", response.reason if hasattr(response, 'reason') else "Unknown reason")
        raise HTTPException(status_code=401, detail="Not authenticated")
    except Exception as e:
        print("Dashboard error:", str(e))
        raise HTTPException(status_code=401, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000) 