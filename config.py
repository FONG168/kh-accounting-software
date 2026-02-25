import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Auto-load .env file so localhost uses the same database as production
_env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())


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
    # Render provides DATABASE_URL with postgres:// but SQLAlchemy requires postgresql://
    _db_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "accounting.db")}')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Company Defaults ──────────────────────────────────────
    COMPANY_NAME = os.environ.get('COMPANY_NAME', 'My Company')
    CURRENCY_SYMBOL = os.environ.get('CURRENCY_SYMBOL', '$')
    FISCAL_YEAR_START_MONTH = int(os.environ.get('FISCAL_YEAR_START_MONTH', 1))  # January

    # ── File Uploads ──────────────────────────────────────────
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max upload size

    # ── Firebase Cloud Sync ─────────────────────────────────
    # Check multiple locations: env var, Render secret file, local file
    FIREBASE_CREDENTIALS_PATH = os.environ.get(
        'FIREBASE_CREDENTIALS_PATH',
        '/etc/secrets/firebase-credentials.json'
        if os.path.exists('/etc/secrets/firebase-credentials.json')
        else os.path.join(BASE_DIR, 'firebase-credentials.json')
    )
