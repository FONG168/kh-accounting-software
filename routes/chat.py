"""
Live Chat routes – User side: contact support / system admin.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.models import db, User, ChatMessage
from sqlalchemy import or_

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


def _get_superadmin():
    """Return the first super-admin user (system owner)."""
    return User.query.filter_by(is_superadmin=True).first()


@chat_bp.route('/')
@login_required
def index():
    """User live chat – single conversation with support admin."""
    admin = _get_superadmin()
    if not admin:
        flash('Support is not available yet.', 'warning')
        return redirect(url_for('dashboard.index'))

    messages = ChatMessage.query.filter(
        or_(
            db.and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == admin.id),
            db.and_(ChatMessage.sender_id == admin.id, ChatMessage.receiver_id == current_user.id),
        )
    ).order_by(ChatMessage.created_at.asc()).all()

    # Mark admin messages as read
    ChatMessage.query.filter_by(
        sender_id=admin.id, receiver_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()

    return render_template('chat/index.html', messages=messages, admin=admin)


@chat_bp.route('/send', methods=['POST'])
@login_required
def send():
    """User sends message to admin."""
    admin = _get_superadmin()
    if not admin:
        flash('Support is not available yet.', 'warning')
        return redirect(url_for('dashboard.index'))

    message_text = request.form.get('message', '').strip()
    if not message_text:
        flash('Cannot send empty message.', 'warning')
        return redirect(url_for('chat.index'))

    msg = ChatMessage(
        sender_id=current_user.id,
        receiver_id=admin.id,
        message=message_text
    )
    db.session.add(msg)
    db.session.commit()
    return redirect(url_for('chat.index'))


@chat_bp.route('/messages')
@login_required
def messages_api():
    """API endpoint – return new messages as JSON for live polling."""
    admin = _get_superadmin()
    if not admin:
        return jsonify([])

    last_id = request.args.get('after', 0, type=int)
    messages = ChatMessage.query.filter(
        ChatMessage.id > last_id,
        or_(
            db.and_(ChatMessage.sender_id == current_user.id, ChatMessage.receiver_id == admin.id),
            db.and_(ChatMessage.sender_id == admin.id, ChatMessage.receiver_id == current_user.id),
        )
    ).order_by(ChatMessage.created_at.asc()).all()

    # Mark admin messages as read
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


@chat_bp.route('/unread-count')
@login_required
def unread_count():
    """Return unread message count for the current user."""
    admin = _get_superadmin()
    if not admin:
        return jsonify({'count': 0})
    count = ChatMessage.query.filter_by(
        sender_id=admin.id, receiver_id=current_user.id, is_read=False
    ).count()
    return jsonify({'count': count})
