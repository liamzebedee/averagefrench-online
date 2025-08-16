#!/usr/bin/env python3
"""
Run script for the Clanker Flask application
"""

import os
from app import app

if __name__ == '__main__':
    # Get environment from FLASK_ENV, default to development
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        print("Starting Clanker in PRODUCTION mode")
        print("Server: http://localhost:8080")
        print("Hot reload: DISABLED")
    else:
        print("Starting Clanker in DEVELOPMENT mode")
        print("Server: http://localhost:8080")
        print("Hot reload: ENABLED")
    
    print("Press Ctrl+C to stop the server")
    
    # Use configuration from app
    app.run(
        host='0.0.0.0', 
        port=8080, 
        debug=app.config['DEBUG'],
        use_reloader=app.config.get('USE_RELOADER', False)
    )
