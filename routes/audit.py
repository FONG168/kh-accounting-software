from flask import Blueprint, render_template, request, jsonify, url_for as flask_url_for
from flask_login import login_required, current_user
from database.models import db, AuditLog, User
from datetime import datetime, timedelta

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')


# ─── ACTION DEFINITIONS (label, icon, badge-class) ──────────────────
ACTION_META = {
    'create':       {'label': 'Created',       'icon': 'bi-plus-circle',          'badge': 'bg-success-subtle text-success-emphasis'},
    'update':       {'label': 'Updated',       'icon': 'bi-pencil',               'badge': 'bg-warning-subtle text-warning-emphasis'},
    'delete':       {'label': 'Deleted',       'icon': 'bi-trash',                'badge': 'bg-danger-subtle text-danger-emphasis'},
    'login':        {'label': 'Login',         'icon': 'bi-box-arrow-in-right',   'badge': 'bg-info-subtle text-info-emphasis'},
    'login_failed': {'label': 'Login Failed',  'icon': 'bi-shield-exclamation',   'badge': 'bg-danger-subtle text-danger-emphasis'},
    'logout':       {'label': 'Logout',        'icon': 'bi-box-arrow-right',      'badge': 'bg-secondary-subtle text-secondary-emphasis'},
    'register':     {'label': 'Registered',    'icon': 'bi-person-plus',          'badge': 'bg-primary-subtle text-primary-emphasis'},
    'approve':      {'label': 'Approved',      'icon': 'bi-check-circle',         'badge': 'bg-success-subtle text-success-emphasis'},
    'reject':       {'label': 'Rejected',      'icon': 'bi-x-circle',             'badge': 'bg-danger-subtle text-danger-emphasis'},
    'suspend':      {'label': 'Suspended',     'icon': 'bi-pause-circle',         'badge': 'bg-warning-subtle text-warning-emphasis'},
    'lock':         {'label': 'Locked',        'icon': 'bi-lock',                 'badge': 'bg-danger-subtle text-danger-emphasis'},
    'reactivate':   {'label': 'Reactivated',   'icon': 'bi-arrow-counterclockwise','badge': 'bg-success-subtle text-success-emphasis'},
    'soft_delete':  {'label': 'Soft Deleted',  'icon': 'bi-archive',              'badge': 'bg-danger-subtle text-danger-emphasis'},
    'fresh_start':  {'label': 'Fresh Start',   'icon': 'bi-arrow-repeat',         'badge': 'bg-info-subtle text-info-emphasis'},
    'recover':      {'label': 'Recovered',     'icon': 'bi-arrow-return-left',    'badge': 'bg-info-subtle text-info-emphasis'},
    'void':         {'label': 'Voided',        'icon': 'bi-slash-circle',         'badge': 'bg-danger-subtle text-danger-emphasis'},
    'cancel':       {'label': 'Cancelled',     'icon': 'bi-x-lg',                'badge': 'bg-secondary-subtle text-secondary-emphasis'},
    'adjust':       {'label': 'Adjusted',      'icon': 'bi-sliders',              'badge': 'bg-warning-subtle text-warning-emphasis'},
    'backup':       {'label': 'Backup',        'icon': 'bi-cloud-upload',         'badge': 'bg-info-subtle text-info-emphasis'},
    'restore':      {'label': 'Restore',       'icon': 'bi-cloud-download',       'badge': 'bg-info-subtle text-info-emphasis'},
}

# ─── ENTITY → VIEW URL MAPPING ──────────────────────────────────────
# Maps entity_type to (blueprint.view_function, param_name)
ENTITY_VIEW_MAP = {
    'Invoice':          ('sales.view',         'id'),
    'Bill':             ('purchases.view',     'id'),
    'Credit Note':      ('credit_notes.view',  'id'),
    'Debit Note':       ('debit_notes.view',   'id'),
    'Journal Entry':    ('journal.view',       'id'),
    'Product':          ('inventory.edit',     'id'),
    'Customer':         ('customers.edit',     'id'),
    'Vendor':           ('vendors.edit',       'id'),
}


def get_entity_url(entity_type, entity_id, action):
    """Build a URL to view/preview the entity, or return None."""
    if not entity_id or action == 'delete':
        return None
    mapping = ENTITY_VIEW_MAP.get(entity_type)
    if not mapping:
        return None
    endpoint, param = mapping
    try:
        return flask_url_for(endpoint, **{param: entity_id})
    except Exception:
        return None


@audit_bp.route('/')
@login_required
def index():
    """Paginated, filterable activity log.
    Admins see ALL users' activity; regular users see only their own.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # ── Filters ──
    action_filter  = request.args.get('action', '')
    entity_filter  = request.args.get('entity', '')
    user_filter    = request.args.get('user', '', type=str)
    search_query   = request.args.get('q', '').strip()
    date_from      = request.args.get('date_from', '').strip()
    date_to        = request.args.get('date_to', '').strip()

    # Admin/owner sees all users' activity; others see only their own
    is_owner = current_user.is_admin or current_user.is_superadmin
    if is_owner:
        query = AuditLog.query
    else:
        query = AuditLog.query.filter_by(user_id=current_user.id)

    # Apply filters
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if entity_filter:
        query = query.filter(AuditLog.entity_type == entity_filter)
    if user_filter:
        try:
            query = query.filter(AuditLog.user_id == int(user_filter))
        except ValueError:
            pass
    if date_from:
        try:
            dt = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < dt)
        except ValueError:
            pass
    if search_query:
        like = f'%{search_query}%'
        query = query.filter(
            db.or_(
                AuditLog.entity_label.ilike(like),
                AuditLog.details.ilike(like),
                AuditLog.user_name.ilike(like),
            )
        )

    logs = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Build dropdown data
    base_filter = AuditLog.query if is_owner else AuditLog.query.filter_by(user_id=current_user.id)
    entity_types = [r[0] for r in
                    db.session.query(AuditLog.entity_type).filter(
                        AuditLog.id.in_(base_filter.with_entities(AuditLog.id))
                    ).distinct().order_by(AuditLog.entity_type).all()]

    action_types = [r[0] for r in
                    db.session.query(AuditLog.action).filter(
                        AuditLog.id.in_(base_filter.with_entities(AuditLog.id))
                    ).distinct().order_by(AuditLog.action).all()]

    # Users list (for admin filter)
    users_list = []
    if is_owner:
        users_list = User.query.filter(User.is_deleted == False).order_by(User.full_name).all()

    return render_template(
        'audit/index.html',
        logs=logs,
        action_filter=action_filter,
        entity_filter=entity_filter,
        user_filter=user_filter,
        search_query=search_query,
        date_from=date_from,
        date_to=date_to,
        entity_types=entity_types,
        action_types=action_types,
        action_meta=ACTION_META,
        users_list=users_list,
        is_owner=is_owner,
        get_entity_url=get_entity_url,
    )
