"""
Firebase Cloud Sync Module
─────────────────────────────────────────────────────────
Auto-syncs every SQLite write to Firebase Firestore.
Works silently — if Firebase is not configured, the app
runs normally with just SQLite.

Setup:
1. Create a Firebase project at https://console.firebase.google.com
2. Go to Project Settings → Service Accounts → Generate New Private Key
3. Save the JSON file as  firebase-credentials.json  in the project root
4. Restart the server — you'll see "☁ Firebase Cloud Sync enabled"
"""

import os
import logging
import threading
from datetime import date, datetime

logger = logging.getLogger('firebase_sync')

# ── Module-level state ────────────────────────────────────────────────
_firestore_client = None
_sync_enabled = False
_pending_changes = []  # collected during before_commit
_lock = threading.Lock()


# ─── PUBLIC API ───────────────────────────────────────────────────────
def is_enabled():
    return _sync_enabled


def init_firebase(app):
    """
    Call once at startup.  Reads the credentials file path from
    app.config['FIREBASE_CREDENTIALS_PATH'] and connects to Firestore.
    """
    global _firestore_client, _sync_enabled

    cred_path = app.config.get('FIREBASE_CREDENTIALS_PATH', '')
    if not cred_path or not os.path.exists(cred_path):
        logger.info('Firebase credentials not found — cloud sync disabled. '
                     'Place firebase-credentials.json in project root to enable.')
        print('ℹ  Firebase Cloud Sync: DISABLED  (no credentials file)')
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as fs

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _firestore_client = fs.client()
        _sync_enabled = True
        logger.info('Firebase Cloud Sync connected.')
        print('☁  Firebase Cloud Sync: ENABLED')
    except ImportError:
        logger.warning('firebase-admin package not installed. Run: pip install firebase-admin')
        print('⚠  Firebase Cloud Sync: DISABLED  (pip install firebase-admin)')
    except Exception as exc:
        logger.error(f'Firebase init failed: {exc}')
        print(f'⚠  Firebase Cloud Sync: DISABLED  ({exc})')


def register_sync_events(db):
    """
    Hook into SQLAlchemy session events to auto-capture changes
    and push them to Firestore after every successful commit.
    """
    from sqlalchemy import event

    @event.listens_for(db.session, 'before_commit')
    def _capture_changes(session):
        """Snapshot new / dirty / deleted objects before the commit flushes them."""
        if not _sync_enabled:
            return

        changes = []
        for obj in list(session.new) + list(session.dirty):
            data = _serialize(obj)
            if data:
                changes.append(('upsert', data))

        for obj in list(session.deleted):
            data = _serialize(obj, deleted=True)
            if data:
                changes.append(('delete', data))

        with _lock:
            _pending_changes.clear()
            _pending_changes.extend(changes)

    @event.listens_for(db.session, 'after_commit')
    def _push_to_firebase(session):
        """Send the captured changes to Firestore in a background thread."""
        if not _sync_enabled:
            return

        with _lock:
            if not _pending_changes:
                return
            batch = list(_pending_changes)
            _pending_changes.clear()

        # Run in background so the user never waits for Firebase
        t = threading.Thread(target=_sync_batch, args=(batch,), daemon=True)
        t.start()


# ─── SERIALIZATION ────────────────────────────────────────────────────
# Maps model class names → Firestore collection names
_COLLECTION_MAP = {
    'User':            'users',
    'CompanySettings': 'company_settings',
    'Account':         'accounts',
    'Category':        'categories',
    'Customer':        'customers',
    'Vendor':          'vendors',
    'Product':         'products',
    'StockMovement':   'stock_movements',
    'Invoice':         'invoices',
    'InvoiceItem':     'invoice_items',
    'Bill':            'bills',
    'BillItem':        'bill_items',
    'PaymentReceived': 'payments_received',
    'PaymentMade':     'payments_made',
    'Expense':         'expenses',
    'JournalEntry':    'journal_entries',
    'JournalLine':     'journal_lines',
}

# Models we skip from auto-sync (none currently)
_SKIP_MODELS = set()


def _serialize(obj, deleted=False):
    """
    Convert a SQLAlchemy model instance to a dict suitable for Firestore.
    Returns None for models we don't sync.
    """
    class_name = type(obj).__name__

    if class_name in _SKIP_MODELS:
        return None

    collection = _COLLECTION_MAP.get(class_name)
    if not collection:
        return None

    if deleted:
        return {
            'collection': collection,
            'doc_id': str(getattr(obj, 'id', None)),
        }

    # Generic serialization: iterate over table columns
    data = {}
    for col in obj.__class__.__table__.columns:
        val = getattr(obj, col.name, None)
        # Convert non-JSON-serializable types
        if isinstance(val, (date, datetime)):
            val = val.isoformat()
        elif val is None:
            val = None
        data[col.name] = val

    return {
        'collection': collection,
        'doc_id': str(data.get('id', '')),
        'data': data,
    }


# ─── BACKGROUND SYNC WORKER ──────────────────────────────────────────
def _sync_batch(batch):
    """Push a batch of changes to Firestore. Runs in a daemon thread."""
    if not _firestore_client:
        return

    try:
        fb_batch = _firestore_client.batch()
        ops = 0

        for action, payload in batch:
            collection = payload['collection']
            doc_id = payload['doc_id']
            if not doc_id or doc_id == 'None':
                continue

            ref = _firestore_client.collection(collection).document(doc_id)

            if action == 'delete':
                fb_batch.delete(ref)
            else:
                fb_batch.set(ref, payload.get('data', {}), merge=True)
            ops += 1

            # Firestore batch limit is 500
            if ops >= 450:
                fb_batch.commit()
                fb_batch = _firestore_client.batch()
                ops = 0

        if ops > 0:
            fb_batch.commit()

        logger.debug(f'Firebase sync: pushed {len(batch)} changes')
    except Exception as exc:
        logger.error(f'Firebase sync failed (non-fatal): {exc}')


# ─── MANUAL FULL BACKUP ──────────────────────────────────────────────
def full_backup():
    """
    Push the entire SQLite database to Firestore.
    Called from the Settings / Backup page.
    Returns (success: bool, message: str).
    """
    if not _sync_enabled or not _firestore_client:
        return False, 'Firebase is not configured. Add firebase-credentials.json and restart.'

    try:
        from database.models import (
            User, CompanySettings, Account, Category, Customer, Vendor, Product,
            StockMovement, Invoice, InvoiceItem, Bill, BillItem,
            PaymentReceived, PaymentMade, Expense, JournalEntry, JournalLine,
        )

        models = [
            User, CompanySettings, Account, Category, Customer, Vendor, Product,
            StockMovement, Invoice, InvoiceItem, Bill, BillItem,
            PaymentReceived, PaymentMade, Expense, JournalEntry, JournalLine,
        ]

        total = 0
        for model_cls in models:
            class_name = model_cls.__name__
            collection = _COLLECTION_MAP.get(class_name)
            if not collection:
                continue

            records = model_cls.query.all()
            fb_batch = _firestore_client.batch()
            ops = 0

            for record in records:
                payload = _serialize(record)
                if not payload:
                    continue
                doc_id = payload['doc_id']
                if not doc_id or doc_id == 'None':
                    continue

                ref = _firestore_client.collection(collection).document(doc_id)
                fb_batch.set(ref, payload['data'], merge=True)
                ops += 1
                total += 1

                if ops >= 450:
                    fb_batch.commit()
                    fb_batch = _firestore_client.batch()
                    ops = 0

            if ops > 0:
                fb_batch.commit()

        return True, f'Full backup complete — {total} records synced to Firebase.'
    except Exception as exc:
        logger.error(f'Full backup failed: {exc}')
        return False, f'Backup failed: {exc}'


# ─── FULL RESTORE (Firebase → SQLite) ────────────────────────────────
def full_restore():
    """
    Pull all data from Firestore and replace local SQLite data.
    Returns (success: bool, message: str).
    """
    if not _sync_enabled or not _firestore_client:
        return False, 'Firebase is not configured.'

    try:
        from database.models import (
            db, User, CompanySettings, Account, Category, Customer, Vendor, Product,
            StockMovement, Invoice, InvoiceItem, Bill, BillItem,
            PaymentReceived, PaymentMade, Expense, JournalEntry, JournalLine,
        )

        # Order matters: delete children first, restore parents first
        restore_order = [
            (JournalLine, 'journal_lines'),
            (JournalEntry, 'journal_entries'),
            (InvoiceItem, 'invoice_items'),
            (BillItem, 'bill_items'),
            (PaymentReceived, 'payments_received'),
            (PaymentMade, 'payments_made'),
            (StockMovement, 'stock_movements'),
            (Invoice, 'invoices'),
            (Bill, 'bills'),
            (Expense, 'expenses'),
            (Product, 'products'),
            (Customer, 'customers'),
            (Vendor, 'vendors'),
            (Category, 'categories'),
            (Account, 'accounts'),
            (CompanySettings, 'company_settings'),
            (User, 'users'),
        ]

        # Delete all local data (children first)
        for model_cls, _ in restore_order:
            model_cls.query.delete()
        db.session.commit()

        total = 0
        # Restore in reverse order (parents first)
        for model_cls, collection_name in reversed(restore_order):
            docs = _firestore_client.collection(collection_name).stream()
            for doc in docs:
                data = doc.to_dict()
                if not data:
                    continue
                # Convert ISO date strings back to date/datetime objects
                data = _deserialize_dates(model_cls, data)
                # Remove None keys that might conflict
                data = {k: v for k, v in data.items() if v is not None or k == 'id'}
                record = model_cls(**data)
                db.session.add(record)
                total += 1
            db.session.flush()

        db.session.commit()
        return True, f'Restore complete — {total} records loaded from Firebase.'
    except Exception as exc:
        logger.error(f'Full restore failed: {exc}')
        from database.models import db
        db.session.rollback()
        return False, f'Restore failed: {exc}'


def _deserialize_dates(model_cls, data):
    """Convert ISO date strings back to Python date/datetime objects."""
    from sqlalchemy import Date, DateTime
    for col in model_cls.__table__.columns:
        if col.name in data and data[col.name]:
            if isinstance(col.type, Date):
                try:
                    data[col.name] = date.fromisoformat(str(data[col.name]))
                except (ValueError, TypeError):
                    pass
            elif isinstance(col.type, DateTime):
                try:
                    data[col.name] = datetime.fromisoformat(str(data[col.name]))
                except (ValueError, TypeError):
                    pass
    return data
