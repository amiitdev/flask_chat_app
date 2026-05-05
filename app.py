import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from dotenv import load_dotenv
from models import db, User, Message
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
from PIL import Image

# Cloudinary imports
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False

load_dotenv()

app = Flask(__name__)

# Security configurations
is_production = os.getenv('FLASK_ENV') == 'production'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')

# Database configuration with multiple fallbacks
db_url = os.getenv('DATABASE_URL', '').strip()
if not db_url:
    # Try render's automatic database binding
    db_url = os.getenv('RENDER_POSTGRES_DATABASE_URL', '').strip()

print(f"DEBUG: DATABASE_URL = {'SET' if db_url else 'NOT SET'}")

if db_url and db_url != '':
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    # Ensure SSL mode is set for production PostgreSQL connections
    if '?' not in db_url and 'postgresql://' in db_url:
        db_url += '?sslmode=require'
    elif '?sslmode=' not in db_url and 'postgresql://' in db_url:
        db_url += '&sslmode=require'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    print(f"DEBUG: Using PostgreSQL database")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
    print("DEBUG: Using SQLite fallback (DATABASE_URL not set)")
    
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}



# Initialize database


db.init_app(app)
with app.app_context():
    db.create_all()
    # Fix password_hash column length if needed (for scrypt hashes)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        columns = {c['name']: c for c in inspector.get_columns('user')}
        if 'password_hash' in columns and columns['password_hash']['type'].length < 255:
            db.session.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE VARCHAR(255)'))
            db.session.commit()
            print("Fixed password_hash column length")
    except Exception as e:
        print(f"Migration check skipped: {e}")
    # Fix existing users with default.png profile pic
    try:
        default_cloudinary = 'https://ui-avatars.com/api/?name=User&background=0d6efd&color=fff&size=128'
        affected = User.query.filter_by(profile_pic='default.png').update({'profile_pic': default_cloudinary})
        db.session.commit()
        if affected:
            print(f"Updated {affected} users with default Cloudinary profile pic")
    except Exception as e:
        print(f"Profile pic migration skipped: {e}")
    print("Database initialized successfully")

# Flask-Migrate for database migrations (optional, for manual use)
try:
    from flask_migrate import Migrate
    migrate = Migrate(app, db)
except ImportError:
    migrate = None

# CORS configuration - restrict in production
cors_origins = os.getenv('CORS_ORIGINS', '*')
if is_production and cors_origins == '*':
    cors_origins = os.getenv('RENDER_EXTERNAL_URL', '')

# Initialize SocketIO without forcing async_mode - let it auto-detect
socketio = SocketIO(app, cors_allowed_origins=cors_origins)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Cloudinary configuration
if False and CLOUDINARY_AVAILABLE and os.getenv('CLOUDINARY_CLOUD_NAME'):
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True
    )

online_users = {}
user_sid_map = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    if file and allowed_file(file.filename):
        filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)

        if False and CLOUDINARY_AVAILABLE and os.getenv('CLOUDINARY_CLOUD_NAME'):
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                folder='chat_app/images',
                transformation=[{'width': 1200, 'height': 1200, 'crop': 'limit'}],
                quality='auto:good'
            )
            return jsonify({'url': upload_result['secure_url']})
        else:
            # Local storage fallback
            filepath = os.path.join('static/uploads', 'images', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            try:
                img = Image.open(filepath)
                img.thumbnail((1200, 1200), Image.LANCZOS)
                img.save(filepath, optimize=True, quality=85)
            except Exception:
                pass
            return jsonify({'url': f'/static/uploads/images/{filename}'})
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/upload-profile', methods=['POST'])
@login_required
def upload_profile():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    if file and allowed_file(file.filename):
        filename = f"user_{current_user.id}_" + secure_filename(file.filename)

        if False and CLOUDINARY_AVAILABLE and os.getenv('CLOUDINARY_CLOUD_NAME'):
            upload_result = cloudinary.uploader.upload(
                file,
                folder='chat_app/profiles',
                transformation=[{'width': 200, 'height': 200, 'crop': 'fill', 'gravity': 'face'}],
                quality='auto:good'
            )
            profile_pic_url = upload_result['secure_url']
            current_user.profile_pic = profile_pic_url
        else:
            filepath = os.path.join('static/uploads', 'profiles', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            profile_pic_url = f'/static/uploads/profiles/{filename}'
            current_user.profile_pic = filename

        db.session.commit()

        socketio.emit('profile_pic_updated', {
            'user_id': current_user.id,
            'profile_pic_url': profile_pic_url
        })

        return jsonify({'url': profile_pic_url})
    return jsonify({'error': 'Invalid file'}), 400

@app.route('/message/<int:message_id>/edit', methods=['POST'])
@login_required
def edit_message(message_id):
    msg = Message.query.get_or_404(message_id)
    if msg.sender_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    new_content = data.get('content', '').strip()
    if new_content:
        msg.content = new_content
        msg.is_edited = True
        db.session.commit()
        socketio.emit('message_edited', {
            'message_id': message_id,
            'content': new_content,
            'recipient_id': msg.recipient_id,
            'sender_id': current_user.id
        }, room=str(msg.recipient_id))
        if msg.recipient_id != current_user.id:
            socketio.emit('message_edited', {
                'message_id': message_id,
                'content': new_content,
                'recipient_id': msg.recipient_id,
                'sender_id': current_user.id
            }, room=str(current_user.id))
        return jsonify({'success': True})
    return jsonify({'error': 'Empty message'}), 400

@app.route('/message/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    msg = Message.query.get_or_404(message_id)
    if msg.sender_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    msg.is_deleted = True
    msg.content = ''
    db.session.commit()
    socketio.emit('message_deleted', {
        'message_id': message_id,
        'recipient_id': msg.recipient_id,
        'sender_id': current_user.id
    }, room=str(msg.recipient_id))
    if msg.recipient_id != current_user.id:
        socketio.emit('message_deleted', {
            'message_id': message_id,
            'recipient_id': msg.recipient_id,
            'sender_id': current_user.id
        }, room=str(current_user.id))
    return jsonify({'success': True})

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if user:
            token = user.set_reset_token()
            db.session.commit()
            flash(f'Password reset link: /reset-password/{token} (Demo - in production, send via email)')
        else:
            flash('User not found.')
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired token.')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if password == confirm:
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            flash('Password reset successful!')
            return redirect(url_for('auth.login'))
        flash('Passwords do not match.')
    return render_template('reset_password.html')

# Import and register blueprints
from routes.auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint)

from routes.main import main as main_blueprint
app.register_blueprint(main_blueprint)

from routes.settings import settings as settings_blueprint
app.register_blueprint(settings_blueprint)

def broadcast_online_users_list():
    """Broadcast filtered online users list to everyone"""
    online_user_ids = []
    for uid in user_sid_map.keys():
        user = User.query.get(uid)
        if user and user.show_online_status:
            online_user_ids.append(uid)
    socketio.emit('online_users_list', {'user_ids': online_user_ids})

# SocketIO events
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        sid = request.sid
        join_room(str(current_user.id))
        online_users[sid] = current_user.id
        user_sid_map[current_user.id] = sid
        print(f"User {current_user.username} (ID: {current_user.id}) connected.")
        # Only broadcast online status if user has it enabled
        if current_user.show_online_status:
            emit('user_online', {'user_id': current_user.id}, broadcast=True)
        # Broadcast updated online users list (only those with online status enabled)
        broadcast_online_users_list()

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    user_id = online_users.get(sid)
    if user_id:
        del online_users[sid]
        if user_id in user_sid_map:
            del user_sid_map[user_id]
        print(f"User ID {user_id} disconnected.")
        # Only broadcast offline status if user has it enabled
        user = User.query.get(user_id)
        if user and user.show_online_status:
            emit('user_offline', {'user_id': user_id}, broadcast=True)
        # Broadcast updated online users list
        broadcast_online_users_list()

@socketio.on('manual_logout')
def handle_manual_logout():
    sid = request.sid
    user_id = online_users.get(sid)
    if user_id:
        del online_users[sid]
        if user_id in user_sid_map:
            del user_sid_map[user_id]
        # Only broadcast offline status if user has it enabled
        user = User.query.get(user_id)
        if user and user.show_online_status:
            emit('user_offline', {'user_id': user_id}, broadcast=True)
        # Broadcast updated online users list
        broadcast_online_users_list()

@socketio.on('private_message')
def handle_private_message(data):
    if current_user.is_authenticated:
        recipient_id = data.get('recipient_id')
        content = data.get('content', '')
        message_type = data.get('message_type', 'text')
        image_url = data.get('image_url', None)
        reply_to_id = data.get('reply_to_id', None)

        if recipient_id and (content or image_url):
            msg = Message(
                sender_id=current_user.id,
                recipient_id=recipient_id,
                content=content,
                message_type=message_type,
                image_url=image_url,
                reply_to_id=reply_to_id
            )
            db.session.add(msg)
            db.session.commit()

            reply_data = None
            if reply_to_id:
                reply_msg = Message.query.get(reply_to_id)
                if reply_msg:
                    reply_data = {
                        'id': reply_msg.id,
                        'content': reply_msg.content[:50] + ('...' if len(reply_msg.content) > 50 else ''),
                        'sender_username': reply_msg.sender.username
                    }

            message_data = {
                'id': msg.id,
                'sender_id': current_user.id,
                'recipient_id': recipient_id,
                'sender_username': current_user.username,
                'content': content,
                'message_type': message_type,
                'image_url': image_url,
                'timestamp': msg.timestamp.isoformat() + 'Z',
                'reply_to': reply_data
            }

            emit('new_message', message_data, room=str(recipient_id))
            emit('new_message', message_data, room=str(current_user.id))

@socketio.on('message_read')
def handle_message_read(data):
    if current_user.is_authenticated:
        message_id = data.get('message_id')
        message = Message.query.get(message_id)
        if message and message.recipient_id == current_user.id and not message.is_read:
            message.is_read = True
            db.session.commit()
            socketio.emit('read_receipt', {
                'message_id': message.id,
                'recipient_id': message.recipient_id
            }, room=str(message.sender_id))

@socketio.on('typing')
def handle_typing(data):
    if current_user.is_authenticated and current_user.typing_status_enabled:
        recipient_id = data.get('recipient_id')
        if recipient_id:
            emit('user_typing', {
                'user_id': current_user.id,
                'username': current_user.username
            }, room=str(recipient_id), include_self=False)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    if current_user.is_authenticated and current_user.typing_status_enabled:
        recipient_id = data.get('recipient_id')
        if recipient_id:
            emit('user_stop_typing', {
                'user_id': current_user.id
            }, room=str(recipient_id), include_self=False)

@socketio.on('toggle_online_status')
def handle_toggle_online_status(data):
    if current_user.is_authenticated:
        show_online = data.get('show_online', True)
        if show_online:
            emit('user_online', {'user_id': current_user.id}, broadcast=True, include_self=False)
        else:
            emit('user_offline', {'user_id': current_user.id}, broadcast=True, include_self=False)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Always use socketio.run() for proper WebSocket support
    socketio.run(app, host='0.0.0.0', port=port, debug=not is_production, allow_unsafe_werkzeug=True)
