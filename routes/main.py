from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from models import User, Message, db
from sqlalchemy import or_

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('chat.html', users=users)

@main.route('/messages/<int:other_user_id>')
@login_required
def get_messages(other_user_id):
    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.recipient_id == other_user_id),
            (Message.sender_id == other_user_id) & (Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()

    return jsonify([{
        'id': m.id,
        'sender_id': m.sender_id,
        'sender_username': m.sender.username,
        'sender_profile_pic': m.sender.profile_pic,
        'content': '(deleted)' if m.is_deleted else m.content,
        'message_type': m.message_type,
        'image_url': m.image_url,
        'timestamp': m.timestamp.isoformat() + 'Z',
        'is_edited': m.is_edited,
        'is_deleted': m.is_deleted,
        'is_read': m.is_read,
        'reply_to': {
            'id': m.reply_to.id,
            'content': m.reply_to.content[:50] + ('...' if len(m.reply_to.content) > 50 else '') if m.reply_to else None,
            'sender_username': m.reply_to.sender.username if m.reply_to else None
        } if m.reply_to else None
    } for m in messages])
