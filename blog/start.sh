#!/bin/bash

echo "Starting Clanker..."
echo "Installing dependencies..."
uv pip install -r requirements.txt

echo "Initializing database..."
python -c "import app; app.init_db(); print('Database ready')"

echo "Starting Flask application on http://localhost:8080"
echo "Environment: Development (Hot Reload Enabled)"
echo ""
echo "To run in production mode:"
echo "  FLASK_ENV=production python run.py"
echo ""
echo "Press Ctrl+C to stop the server"
python run.py
