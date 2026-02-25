"""
KH Accounting Software Enterprise
Main application entry point
"""
import os
from flask import Flask, redirect, url_for, request
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config
from database.models import db, Account, CompanySettings, Category, User, SystemSettings
from database.firebase_sync import init_firebase, register_sync_events, is_enabled as firebase_enabled

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    # Flask-Login setup
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please sign in to continue.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.accounts import accounts_bp
    from routes.journal import journal_bp
    from routes.customers import customers_bp
    from routes.vendors import vendors_bp
    from routes.sales import sales_bp
    from routes.purchases import purchases_bp
    from routes.inventory import inventory_bp
    from routes.expenses import expenses_bp
    from routes.reports import reports_bp
    from routes.setup import setup_bp
    from routes.categories import categories_bp
    from routes.audit import audit_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(audit_bp)

    # Register new feature blueprints
    from routes.credit_notes import credit_notes_bp
    from routes.debit_notes import debit_notes_bp
    from routes.fiscal import fiscal_bp
    from routes.budgets import budgets_bp
    from routes.admin import admin_bp
    from routes.chat import chat_bp

    app.register_blueprint(credit_notes_bp)
    app.register_blueprint(debit_notes_bp)
    app.register_blueprint(fiscal_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chat_bp)

    # Context processor – inject company settings & user to all templates
    @app.context_processor
    def inject_globals():
        if current_user.is_authenticated:
            settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
        else:
            settings = None
        cs = settings.currency_symbol if settings else app.config.get('CURRENCY_SYMBOL', '$')

        # Helper callables for the admin sidebar badges
        def _pending_count():
            if current_user.is_authenticated and current_user.is_superadmin:
                return User.query.filter_by(approval_status='pending', is_superadmin=False).count()
            return 0

        def _unread_chat_count():
            from database.models import ChatMessage
            if current_user.is_authenticated and current_user.is_superadmin:
                return ChatMessage.query.filter_by(receiver_id=current_user.id, is_read=False).count()
            return 0

        return dict(
            company_name=settings.company_name if settings else app.config.get('COMPANY_NAME', 'My Company'),
            currency_symbol=cs,
            cs=cs,  # shorthand alias for templates
            company_settings=settings,
            business_type=settings.business_type if settings and settings.business_type else 'product',
            is_service_business=(settings.business_type == 'service') if settings and settings.business_type else False,
            firebase_cloud_sync=firebase_enabled(),
            fiscal_year_start=app.config.get('FISCAL_YEAR_START_MONTH', 1),
            pending_count=_pending_count,
            unread_chat_count=_unread_chat_count,
            require_approval=SystemSettings.require_approval(),
        )

    # ─── GLOBAL GUARD ──────────────────────────────────────────
    # Flow:  Register → Login → Choose Industry → Dashboard
    @app.before_request
    def enforce_auth_and_setup():
        # Always allow: static files, auth pages, admin pages
        if request.endpoint and (
            request.endpoint.startswith('auth') or
            request.endpoint.startswith('admin') or
            request.endpoint == 'static'
        ):
            return

        # Not logged in → go to login (unless heading to setup choose_industry)
        if not current_user.is_authenticated:
            # Allow the setup.choose_industry POST for edge cases
            if request.endpoint and request.endpoint.startswith('setup'):
                return redirect(url_for('auth.login'))
            return redirect(url_for('auth.login'))

        # Logged in but setup not complete → force industry selection
        if request.endpoint and not request.endpoint.startswith('setup'):
            settings = CompanySettings.query.filter_by(user_id=current_user.id).first()
            if not settings or not settings.is_setup_complete:
                return redirect(url_for('setup.choose_industry'))

            # Safety: if user somehow has no accounts, seed them now
            if Account.query.filter_by(user_id=current_user.id).first() is None:
                for acct in DEFAULT_ACCOUNTS + IFRS_ACCOUNTS:
                    db.session.add(Account(
                        code=acct['code'], name=acct['name'],
                        account_type=acct['account_type'],
                        sub_type=acct.get('sub_type', ''),
                        normal_balance=acct.get('normal_balance', 'debit'),
                        is_system=True, user_id=current_user.id,
                    ))
                db.session.commit()

    # Create database tables & seed defaults on first run
    with app.app_context():
        db.create_all()

        # ── lightweight migrations for new columns ──
        from sqlalchemy import inspect as sa_inspect, text
        insp = sa_inspect(db.engine)

        # CompanySettings migrations
        cs_cols = [c['name'] for c in insp.get_columns('company_settings')]
        if 'logo' not in cs_cols:
            db.session.execute(text("ALTER TABLE company_settings ADD COLUMN logo VARCHAR(300) DEFAULT ''"))
            db.session.commit()
        if 'business_type' not in cs_cols:
            db.session.execute(text("ALTER TABLE company_settings ADD COLUMN business_type VARCHAR(20) DEFAULT 'product'"))
            db.session.commit()
        # Backfill business_type from industry for existing records
        try:
            _service_industries = "('services','education','healthcare','realestate')"
            db.session.execute(text(f"UPDATE company_settings SET business_type = 'service' WHERE industry IN {_service_industries} AND (business_type IS NULL OR business_type = 'product')"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Category migrations (category_type column)
        cat_cols = [c['name'] for c in insp.get_columns('categories')]
        if 'category_type' not in cat_cols:
            db.session.execute(text("ALTER TABLE categories ADD COLUMN category_type VARCHAR(20) DEFAULT 'product'"))
            db.session.commit()

        # Product migrations (advanced classification columns)
        prod_cols = [c['name'] for c in insp.get_columns('products')]
        for col_name, col_def in [
            ('item_type', "VARCHAR(30) DEFAULT 'product'"),
            ('sub_category', "VARCHAR(100) DEFAULT ''"),
            ('revenue_type', "VARCHAR(30) DEFAULT ''"),
            ('cost_behavior', "VARCHAR(30) DEFAULT ''"),
            ('tax_type', "VARCHAR(20) DEFAULT 'taxable'"),
        ]:
            if col_name not in prod_cols:
                db.session.execute(text(f"ALTER TABLE products ADD COLUMN {col_name} {col_def}"))
                db.session.commit()
        # Backfill item_type from is_service flag
        try:
            db.session.execute(text("UPDATE products SET item_type = 'service' WHERE is_service = 1 AND (item_type IS NULL OR item_type = 'product')"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # User migrations (role column + admin fields)
        user_cols = [c['name'] for c in insp.get_columns('users')]
        if 'role' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'"))
            db.session.commit()
        if 'is_superadmin' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_superadmin BOOLEAN DEFAULT 0"))
            db.session.commit()
        if 'approval_status' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN approval_status VARCHAR(20) DEFAULT 'approved'"))
            db.session.commit()
        if 'account_status' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN account_status VARCHAR(20) DEFAULT 'active'"))
            db.session.commit()
        if 'rejection_reason' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN rejection_reason TEXT DEFAULT ''"))
            db.session.commit()
        if 'suspended_reason' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN suspended_reason TEXT DEFAULT ''"))
            db.session.commit()
        if 'username' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(100) DEFAULT NULL"))
            db.session.commit()
        if 'plain_password' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN plain_password VARCHAR(200) DEFAULT ''"))
            db.session.commit()
        if 'suspended_until' not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN suspended_until DATETIME DEFAULT NULL"))
            db.session.commit()

        # ── user_id column migrations for multi-tenant isolation ──
        _multi_tenant_tables = [
            'company_settings', 'categories', 'accounts', 'journal_entries',
            'journal_lines', 'customers', 'vendors', 'products', 'stock_movements',
            'invoices', 'payments_received', 'bills', 'payments_made',
            'expenses', 'fiscal_periods', 'credit_notes', 'debit_notes',
            'budgets', 'audit_log',
        ]
        for _tbl in _multi_tenant_tables:
            try:
                _cols = [c['name'] for c in insp.get_columns(_tbl)]
                if 'user_id' not in _cols:
                    db.session.execute(text(f"ALTER TABLE {_tbl} ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                    db.session.commit()
            except Exception:
                db.session.rollback()

        # Backfill: assign all records with NULL user_id to the superadmin
        _sa = User.query.filter_by(is_superadmin=True).first()
        if _sa:
            for _tbl in _multi_tenant_tables:
                try:
                    db.session.execute(text(f"UPDATE {_tbl} SET user_id = :uid WHERE user_id IS NULL"), {'uid': _sa.id})
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        # Drop old UNIQUE indexes that are no longer valid with multi-tenant
        _unique_indexes_to_drop = [
            ('accounts', 'code'), ('products', 'sku'),
            ('invoices', 'invoice_number'), ('bills', 'bill_number'),
            ('credit_notes', 'cn_number'), ('debit_notes', 'dn_number'),
        ]
        for _tbl, _col in _unique_indexes_to_drop:
            try:
                # Find and drop unique index on the column
                rows = db.session.execute(text(f"PRAGMA index_list('{_tbl}')")).fetchall()
                for row in rows:
                    idx_name = row[1]
                    is_unique = row[2]
                    if is_unique:
                        idx_info = db.session.execute(text(f"PRAGMA index_info('{idx_name}')")).fetchall()
                        if len(idx_info) == 1 and idx_info[0][2] == _col:
                            db.session.execute(text(f"DROP INDEX IF EXISTS \"{idx_name}\""))
                            db.session.commit()
            except Exception:
                db.session.rollback()

        # ── Ensure the ONE super admin exists ────────────────────────
        SUPERADMIN_USERNAME = 'Fong168'
        SUPERADMIN_EMAIL = 'fong@gmail.com'
        SUPERADMIN_PASSWORD = 'Dd112211'

        # Remove superadmin flag from anyone who shouldn't have it
        rogue_admins = User.query.filter(
            User.is_superadmin == True,
            User.email != SUPERADMIN_EMAIL
        ).all()
        for rogue in rogue_admins:
            rogue.is_superadmin = False
            rogue.is_admin = False
        if rogue_admins:
            db.session.commit()

        # Create or update the real super admin
        sa = User.query.filter_by(email=SUPERADMIN_EMAIL).first()
        if not sa:
            # First deployment — create the super admin
            sa = User(
                full_name='Super Admin',
                email=SUPERADMIN_EMAIL,
                username=SUPERADMIN_USERNAME,
                is_superadmin=True,
                is_admin=True,
                role='admin',
                approval_status='approved',
                account_status='active',
                is_active_user=True,
                plain_password=SUPERADMIN_PASSWORD
            )
            sa.set_password(SUPERADMIN_PASSWORD)
            db.session.add(sa)
            db.session.commit()
        else:
            # Ensure credentials are always correct
            changed = False
            if sa.username != SUPERADMIN_USERNAME:
                sa.username = SUPERADMIN_USERNAME
                changed = True
            if not sa.is_superadmin:
                sa.is_superadmin = True
                changed = True
            if not sa.is_admin:
                sa.is_admin = True
                changed = True
            if sa.approval_status != 'approved':
                sa.approval_status = 'approved'
                changed = True
            if sa.account_status != 'active':
                sa.account_status = 'active'
                changed = True
            if not sa.check_password(SUPERADMIN_PASSWORD):
                sa.set_password(SUPERADMIN_PASSWORD)
                changed = True
            if not sa.plain_password:
                sa.plain_password = SUPERADMIN_PASSWORD
                changed = True
            if changed:
                db.session.commit()

        # Seed default system settings
        if not SystemSettings.query.filter_by(key='require_registration_approval').first():
            db.session.add(SystemSettings(key='require_registration_approval', value='true'))
            db.session.commit()

        # Seed default accounts for superadmin user
        sa_user = User.query.filter_by(is_superadmin=True).first()
        if sa_user:
            seed_default_accounts(sa_user.id)
            seed_ifrs_accounts(sa_user.id)

    # ── Firebase Cloud Sync ───────────────────────────────
    init_firebase(app)
    register_sync_events(db)

    return app


# ─── DEFAULT CHART OF ACCOUNTS ─────────────────────────────────────────
DEFAULT_ACCOUNTS = [
    # ── Assets ──
    {'code': '1000', 'name': 'Cash',                 'account_type': 'Asset', 'sub_type': 'Current Asset',  'normal_balance': 'debit'},
    {'code': '1050', 'name': 'Petty Cash',            'account_type': 'Asset', 'sub_type': 'Current Asset',  'normal_balance': 'debit'},
    {'code': '1100', 'name': 'Bank Account',          'account_type': 'Asset', 'sub_type': 'Current Asset',  'normal_balance': 'debit'},
    {'code': '1200', 'name': 'Accounts Receivable',   'account_type': 'Asset', 'sub_type': 'Current Asset',  'normal_balance': 'debit'},
    {'code': '1300', 'name': 'Inventory Asset',       'account_type': 'Asset', 'sub_type': 'Current Asset',  'normal_balance': 'debit'},
    {'code': '1400', 'name': 'Prepaid Expenses',      'account_type': 'Asset', 'sub_type': 'Current Asset',  'normal_balance': 'debit'},
    {'code': '1500', 'name': 'Office Equipment',      'account_type': 'Asset', 'sub_type': 'Fixed Asset',    'normal_balance': 'debit'},
    {'code': '1600', 'name': 'Accumulated Depreciation','account_type': 'Asset','sub_type': 'Fixed Asset',   'normal_balance': 'credit'},
    # ── Liabilities ──
    {'code': '2000', 'name': 'Accounts Payable',      'account_type': 'Liability', 'sub_type': 'Current Liability', 'normal_balance': 'credit'},
    {'code': '2100', 'name': 'Accrued Expenses',      'account_type': 'Liability', 'sub_type': 'Current Liability', 'normal_balance': 'credit'},
    {'code': '2200', 'name': 'Sales Tax Payable',     'account_type': 'Liability', 'sub_type': 'Current Liability', 'normal_balance': 'credit'},
    {'code': '2300', 'name': 'Short-term Loan',       'account_type': 'Liability', 'sub_type': 'Current Liability', 'normal_balance': 'credit'},
    {'code': '2500', 'name': 'Long-term Loan',        'account_type': 'Liability', 'sub_type': 'Long-term Liability', 'normal_balance': 'credit'},
    # ── Equity ──
    {'code': '3000', 'name': "Owner's Equity",        'account_type': 'Equity', 'sub_type': 'Equity', 'normal_balance': 'credit'},
    {'code': '3100', 'name': 'Retained Earnings',     'account_type': 'Equity', 'sub_type': 'Equity', 'normal_balance': 'credit'},
    {'code': '3200', 'name': "Owner's Draw",          'account_type': 'Equity', 'sub_type': 'Equity', 'normal_balance': 'debit'},
    # ── Revenue ──
    {'code': '4000', 'name': 'Sales Revenue',         'account_type': 'Revenue', 'sub_type': 'Income',  'normal_balance': 'credit'},
    {'code': '4100', 'name': 'Service Revenue',       'account_type': 'Revenue', 'sub_type': 'Income',  'normal_balance': 'credit'},
    {'code': '4200', 'name': 'Interest Income',       'account_type': 'Revenue', 'sub_type': 'Other Income', 'normal_balance': 'credit'},
    {'code': '4300', 'name': 'Other Income',          'account_type': 'Revenue', 'sub_type': 'Other Income', 'normal_balance': 'credit'},
    # ── Cost of Goods Sold ──
    {'code': '5000', 'name': 'Cost of Goods Sold',    'account_type': 'Expense', 'sub_type': 'Cost of Sales', 'normal_balance': 'debit'},
    # ── Operating Expenses ──
    {'code': '6000', 'name': 'Advertising & Marketing','account_type': 'Expense','sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6100', 'name': 'Bank Fees & Charges',   'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6200', 'name': 'Insurance',             'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6300', 'name': 'Office Supplies',       'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6400', 'name': 'Rent Expense',          'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6500', 'name': 'Salaries & Wages',      'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6600', 'name': 'Telephone & Internet',  'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6700', 'name': 'Travel & Transportation','account_type': 'Expense','sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6800', 'name': 'Utilities',             'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6900', 'name': 'Depreciation Expense',  'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
    {'code': '6950', 'name': 'Miscellaneous Expense', 'account_type': 'Expense', 'sub_type': 'Operating Expense','normal_balance': 'debit'},
]


def seed_default_accounts(user_id):
    """Insert default Chart of Accounts for a specific user if none exist."""
    if Account.query.filter_by(user_id=user_id).first() is not None:
        return  # already seeded for this user
    for acct in DEFAULT_ACCOUNTS:
        db.session.add(Account(
            code=acct['code'],
            name=acct['name'],
            account_type=acct['account_type'],
            sub_type=acct.get('sub_type', ''),
            normal_balance=acct.get('normal_balance', 'debit'),
            is_system=True,
            user_id=user_id,
        ))
    db.session.commit()
    print(f'✔ Default Chart of Accounts seeded for user {user_id}.')


# ─── ADDITIONAL IFRS/IAS COMPLIANT ACCOUNTS ────────────────────────────
IFRS_ACCOUNTS = [
    # ── Additional Assets (IAS 38, IFRS 9, IFRS 16) ──
    {'code': '1250', 'name': 'Allowance for Doubtful Accounts', 'account_type': 'Asset', 'sub_type': 'Current Asset', 'normal_balance': 'credit'},
    {'code': '1700', 'name': 'Intangible Assets',               'account_type': 'Asset', 'sub_type': 'Fixed Asset',   'normal_balance': 'debit'},
    {'code': '1710', 'name': 'Accumulated Amortization',         'account_type': 'Asset', 'sub_type': 'Fixed Asset',   'normal_balance': 'credit'},
    {'code': '1800', 'name': 'Right-of-Use Assets (IFRS 16)',    'account_type': 'Asset', 'sub_type': 'Fixed Asset',   'normal_balance': 'debit'},
    {'code': '1900', 'name': 'Deferred Tax Asset',               'account_type': 'Asset', 'sub_type': 'Non-current Asset', 'normal_balance': 'debit'},
    # ── Additional Liabilities (IAS 12, IAS 37, IFRS 16) ──
    {'code': '2150', 'name': 'Income Tax Payable',               'account_type': 'Liability', 'sub_type': 'Current Liability',    'normal_balance': 'credit'},
    {'code': '2250', 'name': 'Unearned Revenue',                 'account_type': 'Liability', 'sub_type': 'Current Liability',    'normal_balance': 'credit'},
    {'code': '2400', 'name': 'Lease Liabilities (IFRS 16)',      'account_type': 'Liability', 'sub_type': 'Long-term Liability',  'normal_balance': 'credit'},
    {'code': '2600', 'name': 'Provisions (IAS 37)',              'account_type': 'Liability', 'sub_type': 'Long-term Liability',  'normal_balance': 'credit'},
    {'code': '2700', 'name': 'Deferred Tax Liability',           'account_type': 'Liability', 'sub_type': 'Long-term Liability',  'normal_balance': 'credit'},
    # ── Additional Equity ──
    {'code': '3300', 'name': 'Dividends Declared',               'account_type': 'Equity',    'sub_type': 'Equity',    'normal_balance': 'debit'},
    {'code': '3400', 'name': 'Other Comprehensive Income',       'account_type': 'Equity',    'sub_type': 'Equity',    'normal_balance': 'credit'},
    # ── Additional Revenue ──
    {'code': '4400', 'name': 'Gain on Disposal of Assets',       'account_type': 'Revenue', 'sub_type': 'Other Income', 'normal_balance': 'credit'},
    {'code': '4500', 'name': 'Foreign Exchange Gain',            'account_type': 'Revenue', 'sub_type': 'Other Income', 'normal_balance': 'credit'},
    # ── Additional Expenses ──
    {'code': '6060', 'name': 'Bad Debt Expense',                 'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
    {'code': '6070', 'name': 'Amortization Expense',             'account_type': 'Expense', 'sub_type': 'Operating Expense', 'normal_balance': 'debit'},
    {'code': '7000', 'name': 'Interest Expense',                 'account_type': 'Expense', 'sub_type': 'Finance Cost',      'normal_balance': 'debit'},
    {'code': '7100', 'name': 'Foreign Exchange Loss',            'account_type': 'Expense', 'sub_type': 'Finance Cost',      'normal_balance': 'debit'},
    {'code': '7200', 'name': 'Loss on Disposal of Assets',       'account_type': 'Expense', 'sub_type': 'Other Expense',     'normal_balance': 'debit'},
    {'code': '8000', 'name': 'Income Tax Expense',               'account_type': 'Expense', 'sub_type': 'Tax Expense',       'normal_balance': 'debit'},
]


def seed_ifrs_accounts(user_id):
    """Add additional IFRS-compliant accounts for a specific user."""
    for acct in IFRS_ACCOUNTS:
        existing = Account.query.filter_by(code=acct['code'], user_id=user_id).first()
        if not existing:
            db.session.add(Account(
                code=acct['code'],
                name=acct['name'],
                account_type=acct['account_type'],
                sub_type=acct.get('sub_type', ''),
                normal_balance=acct.get('normal_balance', 'debit'),
                is_system=True,
                user_id=user_id,
            ))
    db.session.commit()


# ─── RUN ────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV', 'development') != 'production'
    app.run(debug=debug, port=5000)
