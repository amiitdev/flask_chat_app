import os
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, current_app as app
from flask_login import login_required, current_user
from models import db, User

settings = Blueprint('settings', __name__)

@settings.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    sound_files = []
    sounds_dir = os.path.join(current_app.root_path, 'static', 'sounds')
    if os.path.exists(sounds_dir):
        sound_files = [f for f in os.listdir(sounds_dir) if f.endswith('.mp3')]

    if request.method == 'POST':
        # Theme Settings
        current_user.theme_preference = request.form.get('theme_preference', 'dark')

        # Sound Settings
        current_user.sound_enabled = bool(request.form.get('sound_enabled'))
        current_user.notification_sound_choice = request.form.get('notification_sound_choice', 'notification.mp3')

        # Privacy Settings - check if online status changed
        old_online_status = current_user.show_online_status
        current_user.show_online_status = bool(request.form.get('show_online_status'))
        current_user.typing_status_enabled = bool(request.form.get('typing_status_enabled'))
        current_user.read_receipts_enabled = bool(request.form.get('read_receipts_enabled'))

        db.session.commit()

        # Notify other users about online status change
        if old_online_status != current_user.show_online_status:
            from app import socketio, broadcast_online_users_list
            if current_user.show_online_status:
                socketio.server.emit('user_online', {'user_id': current_user.id}, to=None)
            else:
                socketio.server.emit('user_offline', {'user_id': current_user.id}, to=None)
            # Broadcast updated online users list
            broadcast_online_users_list()

        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings.user_settings'))

    return render_template('settings.html', user=current_user, sound_files=sound_files)

@settings.route('/settings/sound_toggle', methods=['POST'])
@login_required
def toggle_sound():
    data = request.get_json()
    if data and 'sound_enabled' in data:
        current_user.sound_enabled = data['sound_enabled']
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@settings.route('/settings/theme_switch', methods=['POST'])
@login_required
def switch_theme():
    data = request.get_json()
    if data and 'theme' in data:
        current_user.theme_preference = data['theme']
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400
