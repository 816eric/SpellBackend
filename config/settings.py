import os

# Database configuration - read from environment or use default
DB_PATH = os.getenv('DATABASE_PATH', '/database/db.sqlite3')

# Templates directory - read from environment or use default
templates = os.getenv('TEMPLATES_PATH', './templates')

# API Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')

# Server Configuration
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', '8000'))
SERVER_RELOAD = os.getenv('SERVER_RELOAD', 'true').lower() == 'true'