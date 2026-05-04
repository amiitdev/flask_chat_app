# Flask Private Chat App

A production-ready private chat application built with Flask, SQLite, and SocketIO, styled with Bootstrap 5.

## Features
- User Authentication (Signup/Login/Logout)
- Real-time Private Messaging
- Message History Persistence
- Responsive Design with Bootstrap 5

## Local Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```
4. Open `http://127.0.0.1:5000` in your browser.

## Deployment on Render
1. Create a new **Web Service** on Render.
2. Connect your GitHub repository.
3. Use the following settings:
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 app:app`
4. Add **Environment Variables**:
   - `SECRET_KEY`: A random secret string.
   - `DATABASE_URL`: `sqlite:///chat.db` (Note: SQLite on Render is ephemeral unless using a Persistent Disk).

## Note on SQLite
On Render's free tier, the disk is ephemeral, meaning the SQLite database will reset whenever the service restarts. For persistent storage, consider using Render's PostgreSQL or attaching a Persistent Disk.
