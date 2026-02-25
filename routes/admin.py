"""
Admin Panel routes – Super-admin user management, approval, account control.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, login_user, logout_user, current_user
from database.models import db, User, ChatMessage, log_activity, Announcement, SystemSettings
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def superadmin_required(f):
    """Decorator: only the system super-admin can access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


# ─── ADMIN AUTH ───────────────────────────────────────────────────────
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Separate login page for the admin panel."""
    if current_user.is_authenticated and current_user.is_superadmin:
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter(
            User.username.ilike(username),
            User.is_superadmin == True
        ).first()

        if user and user.check_password(password) and user.is_superadmin:
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('admin.index'))
        else:
            flash('Invalid credentials or insufficient privileges.', 'danger')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """Log out from admin panel and redirect to admin login."""
    logout_user()
    flash('You have been logged out from the Admin Panel.', 'info')
    return redirect(url_for('admin.login'))


# ─── DASHBOARD ────────────────────────────────────────────────────────
@admin_bp.route('/')
@superadmin_required
def index():
    from database.models import (AuditLog, Account, Customer, Vendor,
                                 Product, Invoice, Bill, Expense, JournalEntry, CompanySettings)
    from datetime import datetime, timedelta

    # ── User stats (include ALL users) ──
    all_users = User.query.count()
    pending = User.query.filter_by(approval_status='pending').count()
    active_users = User.query.filter_by(approval_status='approved', account_status='active').count()
    suspended_users = User.query.filter_by(account_status='suspended').count()
    locked_users = User.query.filter_by(account_status='locked').count()

    # ── Unread chat count ──
    unread_chats = ChatMessage.query.filter_by(receiver_id=current_user.id, is_read=False).count()

    # ── System health stats (admin-focused) ──
    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)

    # Registrations this week
    new_registrations_week = User.query.filter(User.created_at >= week_ago).count()

    # Logins today
    logins_today = AuditLog.query.filter(
        AuditLog.action == 'login',
        AuditLog.timestamp >= datetime.combine(today, datetime.min.time())
    ).count()

    # Total audit actions this week
    actions_this_week = AuditLog.query.filter(AuditLog.timestamp >= week_ago).count()

    # Users who never logged in
    never_logged_in = User.query.filter(User.last_login.is_(None), User.is_superadmin == False).count()

    # Per-user usage breakdown (non-superadmin, approved users)
    regular_users = User.query.filter(
        User.is_superadmin == False,
        User.approval_status == 'approved'
    ).order_by(User.last_login.desc().nullslast()).all()

    user_usage = []
    for u in regular_users:
        settings = CompanySettings.query.filter_by(user_id=u.id).first()
        inv_count = Invoice.query.filter_by(user_id=u.id).count()
        bill_count = Bill.query.filter_by(user_id=u.id).count()
        prod_count = Product.query.filter_by(user_id=u.id).count()
        cust_count = Customer.query.filter_by(user_id=u.id).count()
        user_usage.append({
            'user': u,
            'industry': settings.industry if settings else '—',
            'company': settings.company_name if settings else '—',
            'invoices': inv_count,
            'bills': bill_count,
            'products': prod_count,
            'customers': cust_count,
            'total_activity': inv_count + bill_count,
        })

    # ── Recent users (all, latest first, max 10) ──
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    # ── Recent activity (latest 10 audit log entries) ──
    recent_activity = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()

    return render_template('admin/index.html',
                           all_users=all_users,
                           pending=pending,
                           active_users=active_users,
                           suspended_users=suspended_users,
                           locked_users=locked_users,
                           unread_chats=unread_chats,
                           new_registrations_week=new_registrations_week,
                           logins_today=logins_today,
                           actions_this_week=actions_this_week,
                           never_logged_in=never_logged_in,
                           user_usage=user_usage,
                           recent_users=recent_users,
                           recent_activity=recent_activity,
                           require_approval=SystemSettings.require_approval())


# ─── REGISTRATION APPROVAL TOGGLE ───────────────────────────────────
@admin_bp.route('/toggle-approval', methods=['POST'])
@superadmin_required
def toggle_approval():
    """Toggle registration approval requirement on/off."""
    current = SystemSettings.require_approval()
    new_value = 'false' if current else 'true'
    SystemSettings.set('require_registration_approval', new_value)
    status = 'ON' if new_value == 'true' else 'OFF'
    log_activity('update', 'SystemSettings', None, 'Registration Approval',
                 f'Registration approval toggled {status}')
    flash(f'Registration approval is now {status}. '
          f'{"New users must be approved before they can sign in." if new_value == "true" else "New users can sign in immediately after registration."}',
          'success')
    return redirect(url_for('admin.index'))


# ─── PENDING REGISTRATIONS ───────────────────────────────────────────
@admin_bp.route('/pending')
@superadmin_required
def pending_registrations():
    users = User.query.filter_by(approval_status='pending', is_superadmin=False)\
                      .order_by(User.created_at.desc()).all()
    return render_template('admin/pending.html', users=users)


@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@superadmin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        abort(403)
    user.approval_status = 'approved'
    user.account_status = 'active'
    log_activity('approve', 'User', user.id, user.full_name, f'Approved registration for {user.email}')
    db.session.commit()
    flash(f'{user.full_name} has been approved.', 'success')
    return redirect(url_for('admin.pending_registrations'))


@admin_bp.route('/reject/<int:user_id>', methods=['POST'])
@superadmin_required
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        abort(403)
    reason = request.form.get('reason', '').strip()
    user.approval_status = 'rejected'
    user.rejection_reason = reason
    user.account_status = 'removed'
    log_activity('reject', 'User', user.id, user.full_name, f'Rejected registration: {reason}')
    db.session.commit()
    flash(f'{user.full_name} has been rejected.', 'warning')
    return redirect(url_for('admin.pending_registrations'))


# ─── ALL USERS LIST ──────────────────────────────────────────────────
@admin_bp.route('/users')
@superadmin_required
def users_list():
    status_filter = request.args.get('status', 'all')
    q = User.query
    # Exclude soft-deleted users unless specifically filtering for 'removed'
    if status_filter != 'removed':
        q = q.filter((User.is_deleted == False) | (User.is_deleted == None))
    if status_filter == 'active':
        q = q.filter_by(approval_status='approved', account_status='active')
    elif status_filter == 'suspended':
        q = q.filter_by(account_status='suspended')
    elif status_filter == 'locked':
        q = q.filter_by(account_status='locked')
    elif status_filter == 'pending':
        q = q.filter_by(approval_status='pending')
    elif status_filter == 'rejected':
        q = q.filter_by(approval_status='rejected')
    elif status_filter == 'removed':
        q = q.filter_by(account_status='removed')
    users = q.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, status_filter=status_filter, now=datetime.utcnow())


# ─── USER DETAIL / EDIT ──────────────────────────────────────────────
@admin_bp.route('/users/<int:user_id>')
@superadmin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('admin/user_detail.html', user=user)


@admin_bp.route('/users/<int:user_id>/change-email', methods=['POST'])
@superadmin_required
def change_email(user_id):
    user = User.query.get_or_404(user_id)
    new_email = request.form.get('new_email', '').strip().lower()
    if not new_email:
        flash('Email cannot be empty.', 'danger')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    existing = User.query.filter_by(email=new_email).first()
    if existing and existing.id != user.id:
        flash('That email is already in use.', 'danger')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    old_email = user.email
    user.email = new_email
    log_activity('update', 'User', user.id, user.full_name, f'Email changed from {old_email} to {new_email}')
    db.session.commit()
    flash(f'Email updated to {new_email}.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/change-password', methods=['POST'])
@superadmin_required
def change_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '')
    if len(new_password) < 8:
        flash('Password must be at least 8 characters.', 'danger')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    user.set_password(new_password)
    log_activity('update', 'User', user.id, user.full_name, 'Password reset by admin')
    db.session.commit()
    flash(f'Password has been reset for {user.full_name}.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


# ─── ACCOUNT ACTIONS (suspend / lock / reactivate / remove) ──────────
@admin_bp.route('/users/<int:user_id>/suspend', methods=['POST'])
@superadmin_required
def suspend_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        abort(403)
    reason = request.form.get('reason', '').strip()
    days = request.form.get('days', 7, type=int)
    if days < 1:
        days = 1
    if days > 365:
        days = 365
    user.account_status = 'suspended'
    user.suspended_reason = reason
    user.suspended_until = datetime.utcnow() + timedelta(days=days)
    log_activity('suspend', 'User', user.id, user.full_name, f'Account suspended for {days} days: {reason}')
    db.session.commit()
    flash(f'{user.full_name} has been suspended for {days} days.', 'warning')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/lock', methods=['POST'])
@superadmin_required
def lock_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        abort(403)
    reason = request.form.get('reason', '').strip()
    user.account_status = 'locked'
    user.suspended_reason = reason
    log_activity('lock', 'User', user.id, user.full_name, f'Account locked: {reason}')
    db.session.commit()
    flash(f'{user.full_name} has been locked.', 'warning')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/reactivate', methods=['POST'])
@superadmin_required
def reactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        abort(403)
    user.account_status = 'active'
    user.approval_status = 'approved'
    user.suspended_reason = ''
    user.suspended_until = None
    log_activity('reactivate', 'User', user.id, user.full_name, 'Account reactivated')
    db.session.commit()
    flash(f'{user.full_name} has been reactivated.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/delete-info')
@superadmin_required
def delete_info(user_id):
    """API: Return JSON with user age, data counts and deletion guidance."""
    from database.models import (Account, Customer, Vendor, Product, Invoice, Bill,
                                 Expense, JournalEntry, CompanySettings, AuditLog,
                                 Category, Budget, CreditNote, DebitNote,
                                 PaymentReceived, PaymentMade, StockMovement)
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        abort(403)

    now = datetime.utcnow()
    days_since_registration = (now - user.created_at).days
    is_old_user = days_since_registration > 30  # > 30 days = "old" user

    # Count all related data
    counts = {
        'invoices':   Invoice.query.filter_by(user_id=user.id).count(),
        'bills':      Bill.query.filter_by(user_id=user.id).count(),
        'expenses':   Expense.query.filter_by(user_id=user.id).count(),
        'journals':   JournalEntry.query.filter_by(user_id=user.id).count(),
        'customers':  Customer.query.filter_by(user_id=user.id).count(),
        'vendors':    Vendor.query.filter_by(user_id=user.id).count(),
        'products':   Product.query.filter_by(user_id=user.id).count(),
        'accounts':   Account.query.filter_by(user_id=user.id).count(),
        'categories': Category.query.filter_by(user_id=user.id).count(),
        'budgets':    Budget.query.filter_by(user_id=user.id).count(),
        'credit_notes': CreditNote.query.filter_by(user_id=user.id).count(),
        'debit_notes':  DebitNote.query.filter_by(user_id=user.id).count(),
        'payments_received': PaymentReceived.query.filter_by(user_id=user.id).count(),
        'payments_made':     PaymentMade.query.filter_by(user_id=user.id).count(),
        'audit_logs': AuditLog.query.filter_by(user_id=user.id).count(),
    }
    total_records = sum(counts.values())
    has_data = total_records > 0

    return jsonify({
        'user_id': user.id,
        'full_name': user.full_name,
        'email': user.email,
        'registered_on': user.created_at.strftime('%d-%m-%Y'),
        'registered_on_display': user.created_at.strftime('%b %d, %Y'),
        'days_since_registration': days_since_registration,
        'last_login': user.last_login.strftime('%b %d, %Y') if user.last_login else 'Never',
        'is_old_user': is_old_user,
        'has_data': has_data,
        'total_records': total_records,
        'counts': counts,
    })


@admin_bp.route('/users/<int:user_id>/remove', methods=['POST'])
@superadmin_required
def remove_user(user_id):
    from database.models import (Account, Customer, Vendor, Product, Invoice, Bill,
                                 Expense, JournalEntry, CompanySettings, AuditLog,
                                 Category, Budget, CreditNote, DebitNote,
                                 PaymentReceived, PaymentMade, StockMovement,
                                 InvoiceItem, BillItem, CreditNoteItem, DebitNoteItem,
                                 JournalLine, FiscalPeriod)
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        abort(403)

    delete_mode = request.form.get('delete_mode', 'hard')  # 'soft' or 'hard'
    user_name = user.full_name
    user_email = user.email

    if delete_mode == 'soft':
        # ── Soft delete: keep data, allow recovery on re-registration ──
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        user.allow_recovery = True
        user.account_status = 'removed'
        user.is_active_user = False
        log_activity('soft_delete', 'User', user.id, user_name,
                     f'Account soft-deleted (recovery allowed): {user_email}')
        db.session.commit()
        flash(f'{user_name} ({user_email}) has been deleted. Their data is preserved — they can recover it if they re-register.', 'warning')
    else:
        # ── Hard delete: wipe all user data permanently ──
        # Delete invoice items through invoices
        invoice_ids = [i.id for i in Invoice.query.filter_by(user_id=user.id).all()]
        if invoice_ids:
            InvoiceItem.query.filter(InvoiceItem.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)

        # Delete bill items through bills
        bill_ids = [b.id for b in Bill.query.filter_by(user_id=user.id).all()]
        if bill_ids:
            BillItem.query.filter(BillItem.bill_id.in_(bill_ids)).delete(synchronize_session=False)

        # Delete credit note items
        cn_ids = [c.id for c in CreditNote.query.filter_by(user_id=user.id).all()]
        if cn_ids:
            CreditNoteItem.query.filter(CreditNoteItem.credit_note_id.in_(cn_ids)).delete(synchronize_session=False)

        # Delete debit note items
        dn_ids = [d.id for d in DebitNote.query.filter_by(user_id=user.id).all()]
        if dn_ids:
            DebitNoteItem.query.filter(DebitNoteItem.debit_note_id.in_(dn_ids)).delete(synchronize_session=False)

        # Delete journal lines through journal entries
        je_ids = [j.id for j in JournalEntry.query.filter_by(user_id=user.id).all()]
        if je_ids:
            JournalLine.query.filter(JournalLine.journal_entry_id.in_(je_ids)).delete(synchronize_session=False)

        # Delete main records
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

        # Delete chat messages
        ChatMessage.query.filter(
            (ChatMessage.sender_id == user.id) | (ChatMessage.receiver_id == user.id)
        ).delete(synchronize_session=False)

        log_activity('delete', 'User', user.id, user_name,
                     f'Account permanently deleted with all data wiped: {user_email}')
        db.session.delete(user)
        db.session.commit()
        flash(f'{user_name} ({user_email}) has been permanently deleted along with all their data. This cannot be undone.', 'danger')

    return redirect(url_for('admin.users_list'))

# ─── ROLE MANAGEMENT ─────────────────────────────────────────────────
@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@superadmin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_superadmin:
        abort(403)
    new_role = request.form.get('new_role', '').strip().lower()
    valid_roles = ('admin', 'accountant', 'viewer')
    if new_role not in valid_roles:
        flash('Invalid role selected.', 'danger')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    old_role = user.role
    if old_role == new_role:
        flash(f'{user.full_name} is already a {new_role.title()}.', 'info')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    user.role = new_role
    log_activity('update', 'User', user.id, user.full_name,
                 f'Role changed from {old_role} to {new_role}')
    db.session.commit()
    flash(f'{user.full_name}\'s role changed from {old_role.title()} to {new_role.title()}.', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


# ─── ANNOUNCEMENTS ───────────────────────────────────────────────────
@admin_bp.route('/announcements')
@superadmin_required
def announcements():
    all_announcements = Announcement.query.order_by(
        Announcement.is_pinned.desc(),
        Announcement.created_at.desc()
    ).all()
    return render_template('admin/announcements.html', announcements=all_announcements)


@admin_bp.route('/announcements/create', methods=['POST'])
@superadmin_required
def create_announcement():
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    ann_type = request.form.get('type', 'info')
    is_pinned = request.form.get('is_pinned') == 'on'
    expires_at_str = request.form.get('expires_at', '').strip()

    if not title or not message:
        flash('Title and message are required.', 'danger')
        return redirect(url_for('admin.announcements'))

    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d')
        except ValueError:
            pass

    ann = Announcement(
        title=title,
        message=message,
        type=ann_type,
        is_pinned=is_pinned,
        created_by=current_user.id,
        expires_at=expires_at
    )
    db.session.add(ann)
    log_activity('create', 'Announcement', None, title, f'Created announcement: {title}')
    db.session.commit()
    flash(f'Announcement "{title}" published successfully.', 'success')
    return redirect(url_for('admin.announcements'))


@admin_bp.route('/announcements/<int:ann_id>/toggle', methods=['POST'])
@superadmin_required
def toggle_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    ann.is_active = not ann.is_active
    status = 'activated' if ann.is_active else 'deactivated'
    log_activity('update', 'Announcement', ann.id, ann.title, f'Announcement {status}')
    db.session.commit()
    flash(f'Announcement "{ann.title}" {status}.', 'success')
    return redirect(url_for('admin.announcements'))


@admin_bp.route('/announcements/<int:ann_id>/pin', methods=['POST'])
@superadmin_required
def pin_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    ann.is_pinned = not ann.is_pinned
    status = 'pinned' if ann.is_pinned else 'unpinned'
    log_activity('update', 'Announcement', ann.id, ann.title, f'Announcement {status}')
    db.session.commit()
    flash(f'Announcement "{ann.title}" {status}.', 'info')
    return redirect(url_for('admin.announcements'))


@admin_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
@superadmin_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    title = ann.title
    log_activity('delete', 'Announcement', ann.id, title, f'Deleted announcement: {title}')
    db.session.delete(ann)
    db.session.commit()
    flash(f'Announcement "{title}" deleted.', 'warning')
    return redirect(url_for('admin.announcements'))


# ─── BULK USER ACTIONS ───────────────────────────────────────────────
@admin_bp.route('/users/bulk-action', methods=['POST'])
@superadmin_required
def bulk_action():
    action = request.form.get('action', '')
    user_ids = request.form.getlist('user_ids')

    if not user_ids:
        flash('No users selected.', 'warning')
        return redirect(url_for('admin.users_list'))

    user_ids = [int(uid) for uid in user_ids if uid.isdigit()]
    users = User.query.filter(User.id.in_(user_ids), User.is_superadmin == False).all()

    if not users:
        flash('No valid users selected.', 'warning')
        return redirect(url_for('admin.users_list'))

    count = 0
    if action == 'suspend':
        for u in users:
            if u.account_status == 'active':
                u.account_status = 'suspended'
                u.suspended_reason = 'Bulk suspension by admin'
                u.suspended_until = datetime.utcnow() + timedelta(days=7)
                log_activity('suspend', 'User', u.id, u.full_name, 'Bulk suspended')
                count += 1
        db.session.commit()
        flash(f'{count} user(s) suspended.', 'warning')

    elif action == 'lock':
        for u in users:
            if u.account_status == 'active':
                u.account_status = 'locked'
                u.suspended_reason = 'Bulk lock by admin'
                log_activity('lock', 'User', u.id, u.full_name, 'Bulk locked')
                count += 1
        db.session.commit()
        flash(f'{count} user(s) locked.', 'warning')

    elif action == 'reactivate':
        for u in users:
            if u.account_status in ('suspended', 'locked'):
                u.account_status = 'active'
                u.approval_status = 'approved'
                u.suspended_reason = ''
                u.suspended_until = None
                log_activity('reactivate', 'User', u.id, u.full_name, 'Bulk reactivated')
                count += 1
        db.session.commit()
        flash(f'{count} user(s) reactivated.', 'success')

    elif action == 'approve':
        for u in users:
            if u.approval_status == 'pending':
                u.approval_status = 'approved'
                u.account_status = 'active'
                log_activity('approve', 'User', u.id, u.full_name, 'Bulk approved')
                count += 1
        db.session.commit()
        flash(f'{count} user(s) approved.', 'success')

    elif action == 'change_role':
        new_role = request.form.get('bulk_role', 'viewer')
        if new_role in ('admin', 'accountant', 'viewer'):
            for u in users:
                old_role = u.role
                u.role = new_role
                log_activity('update', 'User', u.id, u.full_name,
                             f'Role changed from {old_role} to {new_role} (bulk)')
                count += 1
            db.session.commit()
            flash(f'{count} user(s) role changed to {new_role.title()}.', 'success')

    else:
        flash('Unknown action.', 'danger')

    return redirect(url_for('admin.users_list'))


# ─── ADMIN LIVE CHAT ─────────────────────────────────────────────────
@admin_bp.route('/chat')
@superadmin_required
def chat_list():
    """Show list of users who have chatted with admin."""
    # Get distinct users who have sent or received messages with super admin
    from sqlalchemy import or_, func
    subq = db.session.query(
        db.case(
            (ChatMessage.sender_id != current_user.id, ChatMessage.sender_id),
            else_=ChatMessage.receiver_id
        ).label('other_user_id'),
        func.max(ChatMessage.created_at).label('last_msg_time')
    ).filter(
        or_(
            ChatMessage.sender_id == current_user.id,
            ChatMessage.receiver_id == current_user.id
        )
    ).group_by('other_user_id').subquery()

    conversations = db.session.query(User, subq.c.last_msg_time).join(
        subq, User.id == subq.c.other_user_id
    ).order_by(subq.c.last_msg_time.desc()).all()

    # Count unread per user
    conv_data = []
    for user, last_time in conversations:
        unread = ChatMessage.query.filter_by(
            sender_id=user.id, receiver_id=current_user.id, is_read=False
        ).count()
        last_msg = ChatMessage.query.filter(
            or_(
                db.and_(ChatMessage.sender_id == user.id, ChatMessage.receiver_id == current_user.id),
                db.and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == user.id),
            )
        ).order_by(ChatMessage.created_at.desc()).first()
        conv_data.append({
            'user': user,
            'unread': unread,
            'last_time': last_time,
            'last_message': last_msg.message[:60] if last_msg else ''
        })

    return render_template('admin/chat_list.html', conversations=conv_data)


@admin_bp.route('/chat/<int:user_id>')
@superadmin_required
def chat_room(user_id):
    """Chat with a specific user."""
    other_user = User.query.get_or_404(user_id)
    from sqlalchemy import or_
    messages = ChatMessage.query.filter(
        or_(
            db.and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == user_id),
            db.and_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == current_user.id),
        )
    ).order_by(ChatMessage.created_at.asc()).all()

    # Mark unread messages as read
    ChatMessage.query.filter_by(
        sender_id=user_id, receiver_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()

    return render_template('admin/chat_room.html', other_user=other_user, messages=messages)


@admin_bp.route('/chat/<int:user_id>/send', methods=['POST'])
@superadmin_required
def chat_send(user_id):
    """Send message to a user (admin side)."""
    other_user = User.query.get_or_404(user_id)
    message_text = request.form.get('message', '').strip()
    if not message_text:
        flash('Cannot send empty message.', 'warning')
        return redirect(url_for('admin.chat_room', user_id=user_id))

    msg = ChatMessage(
        sender_id=current_user.id,
        receiver_id=user_id,
        message=message_text
    )
    db.session.add(msg)
    db.session.commit()
    return redirect(url_for('admin.chat_room', user_id=user_id))


@admin_bp.route('/chat/<int:user_id>/messages')
@superadmin_required
def chat_messages_api(user_id):
    """API endpoint – return new messages as JSON for live polling."""
    last_id = request.args.get('after', 0, type=int)
    from sqlalchemy import or_
    messages = ChatMessage.query.filter(
        ChatMessage.id > last_id,
        or_(
            db.and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == user_id),
            db.and_(ChatMessage.sender_id == user_id, ChatMessage.receiver_id == current_user.id),
        )
    ).order_by(ChatMessage.created_at.asc()).all()

    # Mark incoming as read
    for m in messages:
        if m.receiver_id == current_user.id:
            m.is_read = True
    db.session.commit()

    return jsonify([{
        'id': m.id,
        'sender_id': m.sender_id,
        'message': m.message,
        'is_mine': m.sender_id == current_user.id,
        'time': m.created_at.strftime('%b %d, %I:%M %p')
    } for m in messages])
