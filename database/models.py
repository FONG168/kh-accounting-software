import json
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from flask import request as flask_request
from functools import wraps

db = SQLAlchemy()


# ─── RBAC HELPER ──────────────────────────────────────────────────────
def role_required(*roles):
    """Decorator: restrict access to users with one of the given roles.

    Usage:
        @role_required('admin')
        @role_required('admin', 'accountant')
    """
    from flask import abort
    from flask_login import current_user

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ─── USER / AUTHENTICATION ───────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=True)  # Admin username for admin panel login
    password_hash = db.Column(db.String(256), nullable=False)
    plain_password = db.Column(db.String(256), default='')  # Stored for admin viewing
    is_active_user = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_superadmin = db.Column(db.Boolean, default=False)  # System owner / super admin
    role = db.Column(db.String(20), default='admin')  # admin, accountant, viewer
    approval_status = db.Column(db.String(20), default='approved')  # pending, approved, rejected
    account_status = db.Column(db.String(20), default='active')  # active, suspended, locked, removed
    rejection_reason = db.Column(db.Text, default='')
    suspended_reason = db.Column(db.Text, default='')
    suspended_until = db.Column(db.DateTime, nullable=True)  # Suspension expiry date
    is_deleted = db.Column(db.Boolean, default=False)  # Soft-delete flag
    deleted_at = db.Column(db.DateTime, nullable=True)  # When the account was deleted
    allow_recovery = db.Column(db.Boolean, default=False)  # Allow data recovery on re-register
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.plain_password = password

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        """User can log in only if approved and account is active."""
        if self.is_superadmin:
            return True
        # Auto-reactivate if suspension has expired
        if self.account_status == 'suspended' and self.suspended_until:
            if datetime.utcnow() >= self.suspended_until:
                self.account_status = 'active'
                self.suspended_reason = ''
                self.suspended_until = None
                from database.models import db
                db.session.commit()
        return (self.is_active_user and
                self.approval_status == 'approved' and
                self.account_status == 'active')

    def can_edit(self):
        """Check if user can create/edit records."""
        return self.role in ('admin', 'accountant')

    def can_admin(self):
        """Check if user has admin privileges."""
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email}>'


# ─── COMPANY SETTINGS ────────────────────────────────────────────────
class CompanySettings(db.Model):
    __tablename__ = 'company_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    company_name = db.Column(db.String(200), default='My Company')
    industry = db.Column(db.String(100))  # e.g., restaurant, construction, retail
    business_type = db.Column(db.String(20), default='product')  # product, service
    currency_symbol = db.Column(db.String(10), default='$')
    is_setup_complete = db.Column(db.Boolean, default=False)

    # ── Company Profile ───────────────────────────────────────
    tagline = db.Column(db.String(300), default='')            # short slogan / motto
    description = db.Column(db.Text, default='')                # about the company
    registration_number = db.Column(db.String(100), default='') # business reg / SSM / EIN
    tax_id = db.Column(db.String(100), default='')              # tax identification number
    founded_date = db.Column(db.Date, nullable=True)            # date company was founded
    logo = db.Column(db.String(300), default='')                # path to uploaded logo file

    # ── Contact Details ───────────────────────────────────────
    email = db.Column(db.String(200), default='')
    phone = db.Column(db.String(50), default='')
    website = db.Column(db.String(200), default='')
    fax = db.Column(db.String(50), default='')

    # ── Address ───────────────────────────────────────────────
    address_line1 = db.Column(db.String(300), default='')
    address_line2 = db.Column(db.String(300), default='')
    city = db.Column(db.String(100), default='')
    state = db.Column(db.String(100), default='')
    postal_code = db.Column(db.String(20), default='')
    country = db.Column(db.String(100), default='')

    # ── Timestamps ────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CompanySettings {self.company_name} ({self.industry})>'


# ─── PRODUCT CATEGORIES ──────────────────────────────────────────────
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_type = db.Column(db.String(20), default='product')  # product, service
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_custom = db.Column(db.Boolean, default=False)  # True = user-created, survives industry change
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('Category', remote_side='Category.id', backref='children')
    products = db.relationship('Product', backref='category_ref', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


# ─── CHART OF ACCOUNTS ───────────────────────────────────────────────
class Account(db.Model):
    __tablename__ = 'accounts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # Asset, Liability, Equity, Revenue, Expense
    sub_type = db.Column(db.String(100))  # e.g., Current Asset, Fixed Asset, etc.
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_system = db.Column(db.Boolean, default=False)  # System accounts can't be deleted
    normal_balance = db.Column(db.String(10), default='debit')  # debit or credit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('Account', remote_side=[id], backref='children')
    journal_lines = db.relationship('JournalLine', backref='account', lazy='dynamic')

    def get_balance(self, start_date=None, end_date=None, user_id=None):
        """Calculate account balance from journal entries."""
        query = JournalLine.query.join(JournalEntry).filter(
            JournalLine.account_id == self.id,
            JournalEntry.is_posted == True
        )
        if user_id:
            query = query.filter(JournalEntry.user_id == user_id)
        if start_date:
            query = query.filter(JournalEntry.date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.date <= end_date)

        total_debit = sum(line.debit for line in query.all())
        total_credit = sum(line.credit for line in query.all())

        if self.normal_balance == 'debit':
            return total_debit - total_credit
        else:
            return total_credit - total_debit

    def __repr__(self):
        return f'<Account {self.code} - {self.name}>'


# ─── JOURNAL ENTRIES (DOUBLE-ENTRY BOOKKEEPING) ──────────────────────
class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    entry_number = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    description = db.Column(db.Text)
    reference = db.Column(db.String(100))  # Invoice #, Receipt #, etc.
    source = db.Column(db.String(50))  # manual, sale, purchase, expense
    is_posted = db.Column(db.Boolean, default=False)
    is_adjusting = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lines = db.relationship('JournalLine', backref='journal_entry', cascade='all, delete-orphan',
                            order_by='JournalLine.id')

    @property
    def total_debit(self):
        return sum(line.debit for line in self.lines)

    @property
    def total_credit(self):
        return sum(line.credit for line in self.lines)

    @property
    def is_balanced(self):
        return abs(self.total_debit - self.total_credit) < 0.01

    def __repr__(self):
        return f'<JournalEntry {self.entry_number}>'


class JournalLine(db.Model):
    __tablename__ = 'journal_lines'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    description = db.Column(db.String(500))
    debit = db.Column(db.Numeric(15, 2), default=0)
    credit = db.Column(db.Numeric(15, 2), default=0)

    def __repr__(self):
        return f'<JournalLine {self.account_id}: D={self.debit} C={self.credit}>'


# ─── CUSTOMERS ────────────────────────────────────────────────────────
class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    tax_id = db.Column(db.String(50))
    credit_limit = db.Column(db.Numeric(15, 2), default=0)
    balance = db.Column(db.Numeric(15, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoices = db.relationship('Invoice', backref='customer', lazy='dynamic')
    payments_received = db.relationship('PaymentReceived', backref='customer', lazy='dynamic')

    def __repr__(self):
        return f'<Customer {self.name}>'


# ─── VENDORS / SUPPLIERS ─────────────────────────────────────────────
class Vendor(db.Model):
    __tablename__ = 'vendors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    tax_id = db.Column(db.String(50))
    balance = db.Column(db.Numeric(15, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bills = db.relationship('Bill', backref='vendor', lazy='dynamic')
    payments_made = db.relationship('PaymentMade', backref='vendor', lazy='dynamic')

    def __repr__(self):
        return f'<Vendor {self.name}>'


# ─── PRODUCT / INVENTORY ITEMS ───────────────────────────────────────
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    sku = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # legacy text field
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    unit = db.Column(db.String(50), default='pcs')  # pcs, kg, ltr, etc.
    cost_price = db.Column(db.Numeric(15, 2), default=0)
    selling_price = db.Column(db.Numeric(15, 2), default=0)
    quantity_on_hand = db.Column(db.Numeric(15, 4), default=0)
    reorder_level = db.Column(db.Numeric(15, 4), default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_service = db.Column(db.Boolean, default=False)  # Service items don't track inventory

    # ── Advanced Classification (ERP-grade) ───────────────
    item_type = db.Column(db.String(30), default='product')      # product, service
    sub_category = db.Column(db.String(100), default='')          # e.g. Trading Goods, Raw Materials, Professional Services
    revenue_type = db.Column(db.String(30), default='')           # product_sales, service, contract, recurring, project
    cost_behavior = db.Column(db.String(30), default='')          # direct, indirect, billable
    tax_type = db.Column(db.String(20), default='taxable')        # taxable, zero_rated, exempt

    income_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    expense_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    asset_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    income_account = db.relationship('Account', foreign_keys=[income_account_id])
    expense_account = db.relationship('Account', foreign_keys=[expense_account_id])
    asset_account = db.relationship('Account', foreign_keys=[asset_account_id])
    stock_movements = db.relationship('StockMovement', backref='product', lazy='dynamic',
                                      order_by='StockMovement.date.desc()')

    def __repr__(self):
        return f'<Product {self.sku} - {self.name}>'


class StockMovement(db.Model):
    """Track every stock in / stock out movement."""
    __tablename__ = 'stock_movements'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    movement_type = db.Column(db.String(20), nullable=False)  # in, out, adjustment
    quantity = db.Column(db.Numeric(15, 4), nullable=False)
    unit_cost = db.Column(db.Numeric(15, 2), default=0)
    reference = db.Column(db.String(200))  # e.g., Invoice #, PO #, Adjustment
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<StockMovement {self.movement_type} {self.quantity} of Product {self.product_id}>'


# ─── INVOICES (SALES) ────────────────────────────────────────────────
class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    invoice_number = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, partial, overdue, owed, cancelled
    payment_type = db.Column(db.String(20), default='owe')  # pay_now, owe
    subtotal = db.Column(db.Numeric(15, 2), default=0)
    tax_rate = db.Column(db.Numeric(5, 2), default=0)
    tax_amount = db.Column(db.Numeric(15, 2), default=0)
    discount_amount = db.Column(db.Numeric(15, 2), default=0)
    total = db.Column(db.Numeric(15, 2), default=0)
    amount_paid = db.Column(db.Numeric(15, 2), default=0)
    balance_due = db.Column(db.Numeric(15, 2), default=0)
    paid_date = db.Column(db.Date)  # When the invoice was fully paid
    notes = db.Column(db.Text)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('InvoiceItem', backref='invoice', cascade='all, delete-orphan')
    payments = db.relationship('PaymentReceived', backref='invoice', lazy='dynamic')
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])

    def recalculate(self):
        self.subtotal = sum(Decimal(str(item.amount or 0)) for item in self.items)
        self.tax_amount = self.subtotal * (Decimal(str(self.tax_rate or 0)) / 100)
        self.total = self.subtotal + self.tax_amount - Decimal(str(self.discount_amount or 0))
        self.amount_paid = sum(Decimal(str(p.amount or 0)) for p in self.payments.all())
        self.balance_due = self.total - self.amount_paid
        if self.balance_due <= Decimal('0.01'):
            self.status = 'paid'
            if not self.paid_date:
                self.paid_date = date.today()
        elif self.amount_paid > 0:
            self.status = 'partial'

    @property
    def days_until_due(self):
        if not self.due_date:
            return None
        return (self.due_date - date.today()).days

    @property
    def is_overdue(self):
        return self.due_date and self.due_date < date.today() and float(self.balance_due or 0) > 0.01

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(15, 4), default=1)
    unit_price = db.Column(db.Numeric(15, 2), default=0)
    amount = db.Column(db.Numeric(15, 2), default=0)

    product = db.relationship('Product')

    def __repr__(self):
        return f'<InvoiceItem {self.description}: {self.amount}>'


# ─── PAYMENT RECEIVED (FROM CUSTOMERS) ───────────────────────────────
class PaymentReceived(db.Model):
    __tablename__ = 'payments_received'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    payment_number = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_method = db.Column(db.String(50))  # cash, bank, check, card
    reference = db.Column(db.String(100))
    deposit_to_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    deposit_account = db.relationship('Account', foreign_keys=[deposit_to_account_id])
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])

    def __repr__(self):
        return f'<PaymentReceived {self.payment_number}>'


# ─── BILLS (PURCHASES FROM VENDORS) ──────────────────────────────────
class Bill(db.Model):
    __tablename__ = 'bills'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    bill_number = db.Column(db.String(50), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date)
    payment_type = db.Column(db.String(20), default='owe')  # pay_now, owe
    status = db.Column(db.String(20), default='draft')  # draft, received, owed, paid, partial, overdue
    subtotal = db.Column(db.Numeric(15, 2), default=0)
    tax_rate = db.Column(db.Numeric(5, 2), default=0)
    tax_amount = db.Column(db.Numeric(15, 2), default=0)
    total = db.Column(db.Numeric(15, 2), default=0)
    amount_paid = db.Column(db.Numeric(15, 2), default=0)
    balance_due = db.Column(db.Numeric(15, 2), default=0)
    notes = db.Column(db.Text)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'))
    paid_date = db.Column(db.Date)  # When the bill was fully paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('BillItem', backref='bill', cascade='all, delete-orphan')
    payments = db.relationship('PaymentMade', backref='bill', lazy='dynamic')
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])

    def recalculate(self):
        self.subtotal = sum(Decimal(str(item.amount or 0)) for item in self.items)
        self.tax_amount = self.subtotal * (Decimal(str(self.tax_rate or 0)) / 100)
        self.total = self.subtotal + self.tax_amount
        self.amount_paid = sum(Decimal(str(p.amount or 0)) for p in self.payments.all())
        self.balance_due = self.total - self.amount_paid
        if self.balance_due <= Decimal('0.01'):
            self.status = 'paid'
            if not self.paid_date:
                self.paid_date = date.today()
        elif self.amount_paid > 0:
            self.status = 'partial'

    @property
    def days_until_due(self):
        """Days until due date. Negative = overdue."""
        if not self.due_date:
            return None
        return (self.due_date - date.today()).days

    @property
    def is_overdue(self):
        return self.due_date and date.today() > self.due_date and float(self.balance_due or 0) > 0.01

    def __repr__(self):
        return f'<Bill {self.bill_number}>'


class BillItem(db.Model):
    __tablename__ = 'bill_items'
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(15, 4), default=1)
    unit_cost = db.Column(db.Numeric(15, 2), default=0)
    amount = db.Column(db.Numeric(15, 2), default=0)

    product = db.relationship('Product')

    def __repr__(self):
        return f'<BillItem {self.description}: {self.amount}>'


# ─── PAYMENT MADE (TO VENDORS) ───────────────────────────────────────
class PaymentMade(db.Model):
    __tablename__ = 'payments_made'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    payment_number = db.Column(db.String(50), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'))
    date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_method = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    paid_from_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    paid_from_account = db.relationship('Account', foreign_keys=[paid_from_account_id])
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])

    def __repr__(self):
        return f'<PaymentMade {self.payment_number}>'


# ─── EXPENSES ─────────────────────────────────────────────────────────
class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    expense_number = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    category = db.Column(db.String(100))
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'))
    expense_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    paid_from_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_method = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    description = db.Column(db.Text)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vendor = db.relationship('Vendor', foreign_keys=[vendor_id])
    expense_account = db.relationship('Account', foreign_keys=[expense_account_id])
    paid_from_account = db.relationship('Account', foreign_keys=[paid_from_account_id])
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])

    def __repr__(self):
        return f'<Expense {self.expense_number}: {self.amount}>'


# ─── AUDIT LOG (ACTIVITY TRAIL) ──────────────────────────────────────
class AuditLog(db.Model):
    """Track every create / update / delete action across the system."""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_name = db.Column(db.String(200), default='')          # denormalised for speed
    action = db.Column(db.String(20), nullable=False)           # create, update, delete
    entity_type = db.Column(db.String(50), nullable=False)      # Invoice, Bill, Customer …
    entity_id = db.Column(db.Integer)
    entity_label = db.Column(db.String(200), default='')        # human-readable (e.g. "INV-00012")
    details = db.Column(db.Text, default='')                    # free-form or JSON diff
    ip_address = db.Column(db.String(45), default='')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', foreign_keys=[user_id], lazy='select')

    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type}#{self.entity_id}>'


# ─── FISCAL PERIOD (PERIOD LOCKING) ──────────────────────────────────
class FiscalPeriod(db.Model):
    """Represents a fiscal month/period that can be locked to prevent changes."""
    __tablename__ = 'fiscal_periods'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    is_locked = db.Column(db.Boolean, default=False)
    locked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, default='')

    locked_by = db.relationship('User', foreign_keys=[locked_by_id])

    __table_args__ = (db.UniqueConstraint('year', 'month', name='uq_fiscal_period'),)

    @staticmethod
    def is_period_locked(transaction_date, user_id=None):
        """Check if the period for a given date is locked."""
        if not isinstance(transaction_date, date):
            return False
        q = FiscalPeriod.query.filter_by(
            year=transaction_date.year,
            month=transaction_date.month,
            is_locked=True
        )
        if user_id:
            q = q.filter_by(user_id=user_id)
        period = q.first()
        return period is not None

    def __repr__(self):
        return f'<FiscalPeriod {self.year}-{self.month:02d} {"LOCKED" if self.is_locked else "open"}>'


# ─── CREDIT NOTE (SALES RETURNS) ─────────────────────────────────────
class CreditNote(db.Model):
    """Credit notes issued to customers for returns/adjustments."""
    __tablename__ = 'credit_notes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    credit_note_number = db.Column(db.String(50), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    reason = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(15, 2), default=0)
    tax_amount = db.Column(db.Numeric(15, 2), default=0)
    total = db.Column(db.Numeric(15, 2), default=0)
    status = db.Column(db.String(20), default='draft')  # draft, applied, void
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoice = db.relationship('Invoice', foreign_keys=[invoice_id])
    customer = db.relationship('Customer', foreign_keys=[customer_id])
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])
    items = db.relationship('CreditNoteItem', backref='credit_note', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<CreditNote {self.credit_note_number}>'


class CreditNoteItem(db.Model):
    __tablename__ = 'credit_note_items'
    id = db.Column(db.Integer, primary_key=True)
    credit_note_id = db.Column(db.Integer, db.ForeignKey('credit_notes.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(15, 4), default=1)
    unit_price = db.Column(db.Numeric(15, 2), default=0)
    amount = db.Column(db.Numeric(15, 2), default=0)

    product = db.relationship('Product')


# ─── DEBIT NOTE (PURCHASE RETURNS) ───────────────────────────────────
class DebitNote(db.Model):
    """Debit notes issued to vendors for purchase returns/adjustments."""
    __tablename__ = 'debit_notes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    debit_note_number = db.Column(db.String(50), nullable=False)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    reason = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(15, 2), default=0)
    tax_amount = db.Column(db.Numeric(15, 2), default=0)
    total = db.Column(db.Numeric(15, 2), default=0)
    status = db.Column(db.String(20), default='draft')  # draft, applied, void
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bill = db.relationship('Bill', foreign_keys=[bill_id])
    vendor = db.relationship('Vendor', foreign_keys=[vendor_id])
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id])
    items = db.relationship('DebitNoteItem', backref='debit_note', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<DebitNote {self.debit_note_number}>'


class DebitNoteItem(db.Model):
    __tablename__ = 'debit_note_items'
    id = db.Column(db.Integer, primary_key=True)
    debit_note_id = db.Column(db.Integer, db.ForeignKey('debit_notes.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(15, 4), default=1)
    unit_price = db.Column(db.Numeric(15, 2), default=0)
    amount = db.Column(db.Numeric(15, 2), default=0)

    product = db.relationship('Product')


# ─── BUDGET ───────────────────────────────────────────────────────────
class Budget(db.Model):
    """Budget entries per account per period for budget vs actual reporting."""
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12, or 0 for annual
    amount = db.Column(db.Numeric(15, 2), default=0)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship('Account', foreign_keys=[account_id])

    __table_args__ = (db.UniqueConstraint('account_id', 'year', 'month', name='uq_budget_acct_period'),)

    def __repr__(self):
        return f'<Budget {self.account_id} {self.year}-{self.month:02d}: {self.amount}>'


# ─── CHAT MESSAGES (LIVE SUPPORT) ─────────────────────────────────────
class ChatMessage(db.Model):
    """Live chat messages between users and the system admin."""
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

    def __repr__(self):
        return f'<ChatMessage {self.id} from={self.sender_id} to={self.receiver_id}>'


# ─── ANNOUNCEMENTS ────────────────────────────────────────────────────
class Announcement(db.Model):
    """Admin broadcast messages shown to all users."""
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='info')  # info, warning, success, danger
    is_active = db.Column(db.Boolean, default=True)
    is_pinned = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    author = db.relationship('User', foreign_keys=[created_by], lazy='select')

    def __repr__(self):
        return f'<Announcement {self.id}: {self.title}>'


# ─── SYSTEM SETTINGS (global, not per-user) ────────────────────────
class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get(key, default=''):
        """Get a system setting value by key."""
        row = SystemSettings.query.filter_by(key=key).first()
        return row.value if row else default

    @staticmethod
    def set(key, value):
        """Set a system setting value (creates if not exists)."""
        row = SystemSettings.query.filter_by(key=key).first()
        if row:
            row.value = str(value)
        else:
            row = SystemSettings(key=key, value=str(value))
            db.session.add(row)
        db.session.commit()
        return row

    @staticmethod
    def require_approval():
        """Check if registration approval is required."""
        val = SystemSettings.get('require_registration_approval', 'true')
        return val.lower() in ('true', '1', 'yes', 'on')

    def __repr__(self):
        return f'<SystemSettings {self.key}={self.value}>'


def log_activity(action, entity_type, entity_id=None, entity_label='', details=''):
    """Convenience helper — call from any route after a CUD operation.

    Usage:
        log_activity('create', 'Invoice', invoice.id, invoice.invoice_number,
                      'Created invoice for Customer X totalling $500')
    """
    try:
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        user_name = current_user.full_name if current_user and current_user.is_authenticated else 'System'
        ip = flask_request.remote_addr if flask_request else ''

        entry = AuditLog(
            user_id=user_id,
            user_name=user_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=str(entity_label),
            details=str(details),
            ip_address=ip or '',
        )
        db.session.add(entry)
        # Don't commit here — the caller usually commits after its own work.
    except Exception:
        pass  # Audit should never break the main flow
