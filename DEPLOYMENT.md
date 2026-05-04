# Production Deployment Guide - Flask Chat App

## Pre-Deployment Checklist

### 1. Cloudinary Setup (for image storage)
Since Render uses ephemeral storage, images uploaded locally will be lost on redeployment.

1. Create account at [Cloudinary](https://cloudinary.com/)
2. Get your credentials from the dashboard
3. Note: `Cloud Name`, `API Key`, `API Secret`

### 2. Render Deployment Steps

#### Option A: Deploy via Render Dashboard

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure the service:

```
Name: flask-chat-app
Runtime: Python 3
Build Command: pip install -r requirements.txt && flask db upgrade
Start Command: gunicorn app:app
```

6. Add Environment Variables in Render dashboard:

```
SECRET_KEY = (click "Generate" button)
FLASK_ENV = production
CLOUDINARY_CLOUD_NAME = your_cloud_name
CLOUDINARY_API_KEY = your_api_key
CLOUDINARY_API_SECRET = your_api_secret
```

7. Add PostgreSQL Database:
   - Click "New +" → "PostgreSQL"
   - Name: chat-db
   - Create and link to your web service

#### Option B: Deploy via render.yaml (Automatic)

The `render.yaml` file is already configured. Just push to GitHub and connect your repo to Render.

### 3. Initialize Database Migrations

Before first deployment, run locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize migrations
python -c "from app import app; from flask_migrate import Migrate; from models import db; migrate = Migrate(app, db); import flask_migrate; flask_migrate.init()"

# Create initial migration
python -c "from app import app; from models import db; from flask_migrate import Migrate; migrate = Migrate(app, db); import flask_migrate; flask_migrate.migrate(message='Initial migration')"

# Apply migration locally (optional)
python -c "from app import app; from models import db; from flask_migrate import Migrate; migrate = Migrate(app, db); import flask_migrate; flask_migrate.upgrade()"
```

### 4. Production Security Features Added

| Feature | Status |
|---------|--------|
| PostgreSQL Database | ✓ Configured |
| Cloudinary Image Storage | ✓ Configured |
| Flask-Migrate (DB Migrations) | ✓ Added |
| Secure Cookies (HTTPS) | ✓ Enabled in production |
| CORS Protection | ✓ Configurable via env |
| Environment Variables | ✓ Via Render dashboard |
| Gunicorn WSGI Server | ✓ In requirements.txt |

### 5. Local Development vs Production

**Local Development:**
```bash
# .env file
FLASK_ENV=development
DATABASE_URL=sqlite:///chat.db
# Cloudinary vars are optional for local dev
```

**Production (Render):**
```bash
FLASK_ENV=production
DATABASE_URL=<automatically set by Render PostgreSQL>
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

### 6. Post-Deployment Steps

1. Visit your Render URL
2. Create a test account
3. Test image upload (should go to Cloudinary)
4. Test real-time messaging
5. Check that profile pictures persist after redeployment

### 7. Troubleshooting

**Database connection issues:**
- Ensure `DATABASE_URL` is set correctly
- Check Render logs for connection errors

**Image uploads not working:**
- Verify Cloudinary credentials
- Check Render logs for Cloudinary errors

**SocketIO not connecting:**
- Ensure WebSocket support is enabled (Render supports it)
- Check browser console for connection errors

### 8. Monitoring

- View logs: Render Dashboard → Your Service → Logs
- Monitor database: Render Dashboard → Your Database → Metrics
- Check Cloudinary usage: Cloudinary Dashboard

## Support

For issues with:
- **Render**: https://render.com/docs
- **Cloudinary**: https://cloudinary.com/documentation
- **Flask**: https://flask.palletsprojects.com/
