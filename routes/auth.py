from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, current_user
from database.models import db, User, CompanySettings, SystemSettings, log_activity
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/set-language', methods=['POST'])
def set_language():
    """Set user language preference in session."""
    data = request.get_json(silent=True) or {}
    lang = data.get('language', 'en')
    if lang not in ('en', 'km'):
        lang = 'en'
    session['language'] = lang
    return jsonify({'status': 'ok', 'language': lang})


def validate_password_strength(password):
    """Enforce password complexity: min 8 chars, upper, lower, digit, special."""
    errors = []
    if len(password) < 8:
        errors.append('Password must be at least 8 characters.')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter.')
    if not re.search(r'\d', password):
        errors.append('Password must contain at least one number.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', password):
        errors.append('Password must contain at least one special character.')
    return errors


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        recovery_choice = request.form.get('recovery_choice', '')  # 'recover' or 'fresh'

        # ── Check for recoverable soft-deleted account FIRST (before password validation) ──
        existing = User.query.filter_by(email=email).first()
        if existing and existing.is_deleted and existing.allow_recovery and not recovery_choice:
            # Show the recovery choice page — no password validation needed yet
            return render_template('auth/register.html',
                                   full_name=full_name, email=email,
                                   show_recovery=True,
                                   deleted_user=existing)

        # Validation
        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email is required.')
        errors.extend(validate_password_strength(password))
        if password != confirm:
            errors.append('Passwords do not match.')

        # Handle recovery choices (user already saw the recovery page)
        if existing:
            if existing.is_deleted and existing.allow_recovery:
                if recovery_choice == 'recover':
                    # Recover the old account with all data
                    if errors:
                        for e in errors:
                            flash(e, 'danger')
                        return render_template('auth/register.html',
                                               full_name=full_name, email=email,
                                               show_recovery=True,
                                               deleted_user=existing)
                    approval_required = SystemSettings.require_approval()
                    existing.full_name = full_name
                    existing.set_password(password)
                    existing.is_deleted = False
                    existing.deleted_at = None
                    existing.allow_recovery = False
                    existing.is_active_user = True
                    existing.account_status = 'active'
                    existing.approval_status = 'pending' if approval_required else 'approved'
                    log_activity('recover', 'User', existing.id, full_name,
                                 f'Account recovered with previous data: {email}')
                    db.session.commit()
                    if approval_required:
                        flash(f'\U0001f389 Congratulations, {full_name}! Your account has been recovered with all your previous data! Please wait for admin approval.', 'success')
                    else:
                        flash(f'\U0001f389 Congratulations, {full_name}! Your account has been recovered with all your previous data! You can now sign in.', 'success')
                    return redirect(url_for('auth.login'))
                elif recovery_choice == 'fresh':
                    # Delete old data and create fresh account
                    if errors:
                        for e in errors:
                            flash(e, 'danger')
                        return render_template('auth/register.html',
                                               full_name=full_name, email=email,
                                               show_recovery=True,
                                               deleted_user=existing)
                    # Wipe all old data
                    _wipe_user_data(existing)
                    approval_required = SystemSettings.require_approval()
                    existing.full_name = full_name
                    existing.set_password(password)
                    existing.is_deleted = False
                    existing.deleted_at = None
                    existing.allow_recovery = False
                    existing.is_active_user = True
                    existing.account_status = 'active'
                    existing.approval_status = 'pending' if approval_required else 'approved'
                    log_activity('fresh_start', 'User', existing.id, full_name,
                                 f'Account re-created with fresh data (old data wiped): {email}')
                    db.session.commit()
                    if approval_required:
                        flash(f'\U0001f389 Congratulations, {full_name}! Your new account has been created with a fresh start! Please wait for admin approval.', 'success')
                    else:
                        flash(f'\U0001f389 Congratulations, {full_name}! Your new account has been created with a fresh start! You can now sign in.', 'success')
                    return redirect(url_for('auth.login'))
            else:
                errors.append('An account with this email already exists.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/register.html',
                                   full_name=full_name, email=email)

        # Check if this is the very first user → super-admin (auto-approved)
        is_first_user = User.query.filter(User.is_deleted == False).count() == 0

        # Determine approval mode: if admin turned off approval requirement, auto-approve
        approval_required = SystemSettings.require_approval() if not is_first_user else False

        user = User(
            full_name=full_name,
            email=email,
            is_admin=True if is_first_user else False,
            is_superadmin=is_first_user,
            approval_status='approved' if (is_first_user or not approval_required) else 'pending',
            account_status='active',
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        log_activity('register', 'User', user.id, user.full_name,
                     f'New account registered: {email}' + (' (super-admin)' if is_first_user else ''))
        db.session.commit()

        if is_first_user:
            # First user (super-admin) – log in immediately
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome, {full_name}! You are the system administrator. Let\'s set up your business.', 'success')
            return redirect(url_for('setup.choose_industry'))
        elif not approval_required:
            # Auto-approved – no admin approval needed
            flash(f'🎉 Congratulations, {full_name}! Your account has been created successfully. You can now sign in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            # Regular user – must wait for admin approval
            flash(f'🎉 Congratulations, {full_name}! Your account has been registered successfully. Please wait for the administrator to approve your registration before you can sign in.', 'info')
            return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


def _wipe_user_data(user):
    """Helper to delete all data owned by a user (for fresh re-registration)."""
    from database.models import (Account, Customer, Vendor, Product, Invoice, Bill,
                                 Expense, JournalEntry, CompanySettings, AuditLog,
                                 Category, Budget, CreditNote, DebitNote,
                                 PaymentReceived, PaymentMade, StockMovement,
                                 InvoiceItem, BillItem, CreditNoteItem, DebitNoteItem,
                                 JournalLine, FiscalPeriod, ChatMessage)

    invoice_ids = [i.id for i in Invoice.query.filter_by(user_id=user.id).all()]
    if invoice_ids:
        InvoiceItem.query.filter(InvoiceItem.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)

    bill_ids = [b.id for b in Bill.query.filter_by(user_id=user.id).all()]
    if bill_ids:
        BillItem.query.filter(BillItem.bill_id.in_(bill_ids)).delete(synchronize_session=False)

    cn_ids = [c.id for c in CreditNote.query.filter_by(user_id=user.id).all()]
    if cn_ids:
        CreditNoteItem.query.filter(CreditNoteItem.credit_note_id.in_(cn_ids)).delete(synchronize_session=False)

    dn_ids = [d.id for d in DebitNote.query.filter_by(user_id=user.id).all()]
    if dn_ids:
        DebitNoteItem.query.filter(DebitNoteItem.debit_note_id.in_(dn_ids)).delete(synchronize_session=False)

    je_ids = [j.id for j in JournalEntry.query.filter_by(user_id=user.id).all()]
    if je_ids:
        JournalLine.query.filter(JournalLine.journal_entry_id.in_(je_ids)).delete(synchronize_session=False)

    PaymentReceived.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    PaymentMade.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Invoice.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Bill.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    CreditNote.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    DebitNote.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Expense.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    JournalEntry.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    StockMovement.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Product.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Category.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Customer.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Vendor.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Account.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Budget.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    FiscalPeriod.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    CompanySettings.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    AuditLog.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    ChatMessage.query.filter(
        (ChatMessage.sender_id == user.id) | (ChatMessage.receiver_id == user.id)
    ).delete(synchronize_session=False)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = 'remember' in request.form

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # ── Check approval status ──
            if user.approval_status == 'pending':
                flash('Your registration is still pending admin approval. Please wait for the administrator to approve your account.', 'warning')
                return render_template('auth/login.html', email=email)

            if user.approval_status == 'rejected':
                reason = user.rejection_reason or 'No reason provided.'
                flash(f'Your registration has been rejected. Reason: {reason}', 'danger')
                return render_template('auth/login.html', email=email)

            # ── Check account status ──
            if user.account_status == 'suspended':
                # Check if suspension has expired
                if user.suspended_until and datetime.utcnow() >= user.suspended_until:
                    user.account_status = 'active'
                    user.suspended_reason = ''
                    user.suspended_until = None
                    db.session.commit()
                else:
                    reason = user.suspended_reason or 'Contact administrator.'
                    remaining = ''
                    if user.suspended_until:
                        days_left = (user.suspended_until - datetime.utcnow()).days + 1
                        remaining = f' ({days_left} day{"s" if days_left != 1 else ""} remaining)'
                    flash(f'Your account has been suspended{remaining}. Reason: {reason}', 'danger')
                    return render_template('auth/login.html', email=email)

            if user.account_status == 'locked':
                reason = user.suspended_reason or 'Contact administrator.'
                flash(f'Your account has been locked. Reason: {reason}', 'danger')
                return render_template('auth/login.html', email=email)

            if user.account_status == 'removed':
                flash('Your account has been removed from the system.', 'danger')
                return render_template('auth/login.html', email=email)

            # Determine if this is first login (new user) or returning
            is_first_login = user.last_login is None

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            log_activity('login', 'User', user.id, user.full_name, f'{user.email} signed in')
            db.session.commit()

            # Welcome message – new user vs returning user
            if is_first_login:
                flash(f'🎉 Welcome to KH Accounting Software, {user.full_name}! Let\'s get you started.', 'success')
            else:
                flash(f'👋 Welcome back, {user.full_name}!', 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)

            # If setup not done, go to setup
            settings = CompanySettings.query.filter_by(user_id=user.id).first()
            if not settings or not settings.is_setup_complete:
                return redirect(url_for('setup.choose_industry'))

            return redirect(url_for('dashboard.index'))
        else:
            log_activity('login_failed', 'User', None, email, f'Failed login attempt for {email}')
            db.session.commit()
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', email=email)

    return render_template('auth/login.html')


@auth_bp.route('/about')
def about():
    return render_template('auth/about.html')


@auth_bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        log_activity('logout', 'User', current_user.id, current_user.full_name,
                     f'{current_user.email} signed out')
        db.session.commit()
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
