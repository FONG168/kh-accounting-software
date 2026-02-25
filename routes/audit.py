from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from database.models import db, AuditLog

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')


@audit_bp.route('/')
@login_required
def index():
    """Paginated, filterable activity log."""
    page = request.args.get('page', 1, type=int)
    per_page = 30

    # Optional filters
    action_filter = request.args.get('action', '')
    entity_filter = request.args.get('entity', '')
    search_query = request.args.get('q', '').strip()

    query = AuditLog.query.filter_by(user_id=current_user.id)

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if entity_filter:
        query = query.filter(AuditLog.entity_type == entity_filter)
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

    # Distinct entity types for filter dropdown
    entity_types = [r[0] for r in db.session.query(AuditLog.entity_type).filter(AuditLog.user_id == current_user.id).distinct().order_by(AuditLog.entity_type).all()]

    return render_template(
        'audit/index.html',
        logs=logs,
        action_filter=action_filter,
        entity_filter=entity_filter,
        search_query=search_query,
        entity_types=entity_types,
    )
