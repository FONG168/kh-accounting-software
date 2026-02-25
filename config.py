import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Vercel serverless: writable dir is /tmp
IS_VERCEL = os.environ.get('VERCEL', '') == '1'
DB_DIR = '/tmp' if IS_VERCEL else BASE_DIR


class Config:
    # ── Security ──────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # CSRF token validity: 1 hour

    # ── Session ───────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour session timeout
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'

    # ── Database ──────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(DB_DIR, "accounting.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Company Defaults ──────────────────────────────────────
    COMPANY_NAME = os.environ.get('COMPANY_NAME', 'My Company')
    CURRENCY_SYMBOL = os.environ.get('CURRENCY_SYMBOL', '$')
    FISCAL_YEAR_START_MONTH = int(os.environ.get('FISCAL_YEAR_START_MONTH', 1))  # January

    # ── File Uploads ──────────────────────────────────────────
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max upload size

    # ── Firebase Cloud Sync ─────────────────────────────────
    FIREBASE_CREDENTIALS_PATH = os.environ.get(
        'FIREBASE_CREDENTIALS_PATH',
        os.path.join(BASE_DIR, 'firebase-credentials.json')
    )
