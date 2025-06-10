# WorkOS Authentication Example

This project demonstrates authentication using WorkOS with both Flask and FastAPI backends.

## Prerequisites

- Node.js and npm
- Python 3.7+
- WorkOS account and API credentials

## Environment Variables

Create a `.env` file in the root with the following variables:

```
WORKOS_API_KEY=your_api_key
WORKOS_CLIENT_ID=your_client_id
WORKOS_REDIRECT_URI=http://localhost:5000/api/callback
WORKOS_COOKIE_PASSWORD=your_cookie_password

```

for a cookie password you can use `openssl rand -base64 32` to generate.

## Running the Application

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:5173

### Backend Options

#### Option 1: Flask Backend

```bash
cd server
pip install flask flask-cors python-dotenv workos
python app.py
```

The Flask backend will be available at http://localhost:5000

#### Option 2: FastAPI Backend

```bash
cd server
pip install fastapi uvicorn python-dotenv workos
python app_fastapi.py
```

The FastAPI backend will be available at http://localhost:5000

## Features

- User authentication with WorkOS
- Protected routes
- Session management
- Dashboard with user information
- Secure cookie handling



## Notes

- The FastAPI version includes automatic API documentation at http://localhost:5000/docs
- Both versions support the same frontend
- Choose either Flask or FastAPI based on your preference
