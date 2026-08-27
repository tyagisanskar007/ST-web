import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'shiv-traders-super-secure-key-2026-luxury-manufacturing')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
    
    # Firebase Cloud Settings
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'shiv-trader')
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY', 'AIzaSyB0PPldQrPlfUhdl--4cOF7FHHSrGhgGAk')
    FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN', 'shiv-trader.firebaseapp.com')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET', 'shiv-trader.firebasestorage.app')
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID', '12220782640')
    FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID', '1:12220782640:web:1cdd605df261eea9a1f5f5')
    FIREBASE_MEASUREMENT_ID = os.environ.get('FIREBASE_MEASUREMENT_ID', 'G-W227SZ8HZH')
    FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL', '')
    FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY', '')
    FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', '')
    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json')
    
    # Admin Credentials (Initial setup / fallback)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@shivtraders.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@ShivTraders2026')
    ADMIN_NAME = os.environ.get('ADMIN_NAME', 'Shiv Traders Administrator')
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URI = "memory://"
