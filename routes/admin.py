import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Message
from werkzeug.security import generate_password_hash

admin = Blueprint('admin', __name__)

# Simple admin check - in production, use a proper admin role
def is_admin():
    return current_user.is_authenticated and current_user.username == 'admin'

@admin.route('/admin')
@login_required
def dashboard():
    if not is_admin():
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('main.index'))
    
    users = User.query.all()
    user_stats = []
    for user in users:
        sent_count = Message.query.filter_by(sender_id=user.id).count()
        received_count = Message.query.filter_by(recipient_id=user.id).count()
        user_stats.append({
            'user': user,
            'sent_count': sent_count,
            'received_count': received_count,
            'total_messages': sent_count + received_count
        })
    
    total_messages = Message.query.count()
    
    return render_template('admin/dashboard.html', 
                         user_stats=user_stats, 
                         total_users=len(users),
                         total_messages=total_messages)

@admin.route('/admin/user/add', methods=['POST'])
@login_required
def add_user():
    if not is_admin():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': 'Username already exists'}), 400
    
    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User added successfully'})

@admin.route('/admin/user/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_user(user_id):
    if not is_admin():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username and username != user.username:
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        user.username = username
    
    if password:
        user.set_password(password)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'User updated successfully'})

@admin.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not is_admin():
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete yourself'}), 400
    
    user = User.query.get_or_404(user_id)
    
    # Delete all messages involving this user
    Message.query.filter(
        (Message.sender_id == user_id) | (Message.recipient_id == user_id)
    ).delete(synchronize_session=False)
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User deleted successfully'})
