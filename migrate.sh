#!/bin/bash
# Initialize Flask-Migrate for production database migrations

echo "Setting up database migrations..."

# Initialize migrations folder
python -c "from app import app; from flask_migrate import Migrate; from models import db; migrate = Migrate(app, db); import flask_migrate; flask_migrate.init()"

# Create initial migration
python -c "from app import app; from models import db; from flask_migrate import Migrate; migrate = Migrate(app, db); import flask_migrate; flask_migrate.migrate(message='Initial migration')"

# Apply migration
python -c "from app import app; from models import db; from flask_migrate import Migrate; migrate = Migrate(app, db); import flask_migrate; flask_migrate.upgrade()"

echo "Migration setup complete!"
echo ""
echo "For production on Render:"
echo "1. Push code to GitHub"
echo "2. Connect repo to Render"
echo "3. Add environment variables in Render dashboard"
echo "4. Render will auto-run 'flask db upgrade' from render.yaml"
