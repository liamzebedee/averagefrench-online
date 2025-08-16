from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import hashlib
import os
import time
from datetime import datetime
import json
from config import config

app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

# Custom Jinja2 filter for formatting numbers like Twitter
@app.template_filter('format_count')
def format_count(value):
    """Format numbers like Twitter: 1K, 1.2M, etc."""
    if value < 1000:
        return str(value)
    elif value < 1000000:
        if value % 1000 == 0:
            return f"{value // 1000}K"
        else:
            return f"{value / 1000:.1f}K".replace('.0K', 'K')
    else:
        if value % 1000000 == 0:
            return f"{value // 1000000}M"
        else:
            return f"{value / 1000000:.1f}M".replace('.0M', 'M')

@app.template_filter('format_time')
def format_time(timestamp):
    """Format timestamp as relative time"""
    if not timestamp:
        return ''
    
    try:
        timestamp = int(timestamp)
        now = int(time.time())
        diff = now - timestamp
        
        if diff < 60:
            return 'now'
        elif diff < 3600:
            minutes = diff // 60
            return f'{minutes}m'
        elif diff < 86400:
            hours = diff // 3600
            return f'{hours}h'
        elif diff < 2592000:
            days = diff // 86400
            return f'{days}d'
        else:
            months = diff // 2592000
            return f'{months}mo'
    except:
        return str(timestamp)

# Database configuration
DB_PATH = app.config['DB_PATH']

def get_db_connection():
    """Get database connection with WAL mode enabled for parallel writes"""
    conn = sqlite3.connect(DB_PATH, timeout=app.config['DATABASE_TIMEOUT'])
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=10000')
    conn.execute('PRAGMA temp_store=MEMORY')
    return conn

def init_db():
    """Initialize database tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            bio TEXT,
            profile_image TEXT,
            banner_image TEXT,
            is_clanker BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create new engagements table for likes and replies
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_engagements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('like', 'reply', 'clanked')),
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (post_id) REFERENCES posts (id),
            UNIQUE(user_id, post_id, type)
        )
    ''')
    
    # Create notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            typ TEXT NOT NULL CHECK (typ IN ('like', 'reply', 'clanked')),
            obj_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (obj_id) REFERENCES posts (id)
        )
    ''')
    
    # Add new columns to existing users table if they don't exist
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN bio TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN profile_image TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN banner_image TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN last_seen_notif INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN is_clanker BOOLEAN DEFAULT FALSE')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create case insensitive unique index on username
    try:
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower ON users (LOWER(username))')
    except sqlite3.OperationalError:
        pass  # Index already exists
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

def create_notification(user_id, typ, obj_id):
    """Create a notification for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the post owner's user_id
    cursor.execute('SELECT user FROM posts WHERE id = ?', (obj_id,))
    post = cursor.fetchone()
    if post:
        # Get the post owner's user_id from username
        cursor.execute('SELECT id FROM users WHERE username = ?', (post[0],))
        post_owner = cursor.fetchone()
        if post_owner and post_owner[0] != user_id:  # Don't notify yourself
            cursor.execute('''
                INSERT INTO notifs (typ, obj_id, user_id) 
                VALUES (?, ?, ?)
            ''', (typ, obj_id, post_owner[0]))
            conn.commit()
    
    conn.close()

def get_unread_notification_count(user_id):
    """Get count of unread notifications for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM notifs 
        WHERE user_id = ? AND id > (
            SELECT COALESCE(last_seen_notif, 0) FROM users WHERE id = ?
        )
    ''', (user_id, user_id))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_aggregated_notifications(user_id):
    """Get aggregated notifications for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all notifications with user details
        cursor.execute('''
            SELECT n.id, n.typ, n.obj_id, n.created_at, p.text, p.user, u.display_name, u.profile_image
            FROM notifs n
            JOIN posts p ON n.obj_id = p.id
            JOIN users u ON p.user = u.username
            WHERE n.user_id = ?
            ORDER BY n.created_at DESC
            LIMIT 100
        ''', (user_id,))
        
        notifications = []
        for row in cursor.fetchall():
            notification = {
                'id': row[0],
                'type': row[1],
                'post_id': row[2],
                'created_at': row[3],
                'post_text': row[4],
                'post_user': row[5],
                'post_user_display_name': row[6] or row[5],
                'post_user_profile_image': row[7]
            }
            
            # For replies, get the actual reply content and ID
            if row[1] == 'reply':
                cursor.execute('''
                    SELECT e.id, e.content, e.user_id
                    FROM new_engagements e
                    WHERE e.post_id = ? AND e.type = 'reply'
                    ORDER BY e.created_at DESC
                    LIMIT 1
                ''', (row[2],))
                reply_data = cursor.fetchone()
                if reply_data:
                    notification['reply_id'] = reply_data[0]
                    notification['reply_content'] = reply_data[1]
                    notification['reply_user_id'] = reply_data[2]
            
            notifications.append(notification)
        
        # Aggregate likes by post
        aggregated = []
        post_likes = {}
        
        for notif in notifications:
            if notif['type'] == 'like':
                post_id = notif['post_id']
                if post_id not in post_likes:
                    post_likes[post_id] = {
                        'post_id': post_id,
                        'post_text': notif['post_text'],
                        'post_user': notif['post_user'],
                        'post_user_display_name': notif['post_user_display_name'],
                        'post_user_profile_image': notif['post_user_profile_image'],
                        'likers': [],
                        'created_at': notif['created_at']
                    }
                
                # Get liker details
                cursor.execute('''
                    SELECT u.username, u.display_name, u.profile_image
                    FROM new_engagements e
                    JOIN users u ON e.user_id = u.id
                    WHERE e.post_id = ? AND e.type = 'like'
                    ORDER BY e.created_at DESC
                    LIMIT 5
                ''', (post_id,))
                
                likers = []
                for liker_row in cursor.fetchall():
                    likers.append({
                        'username': liker_row[0],
                        'display_name': liker_row[1] or liker_row[0],
                        'profile_image': liker_row[2]
                    })
                
                post_likes[post_id]['likers'] = likers
                post_likes[post_id]['like_count'] = len(likers)
        
        # Convert aggregated likes to notifications
        for post_data in post_likes.values():
            if post_data['like_count'] > 0:
                aggregated.append({
                    'type': 'aggregated_likes',
                    'post_id': post_data['post_id'],
                    'post_text': post_data['post_text'],
                    'post_user': post_data['post_user'],
                    'post_user_display_name': post_data['post_user_display_name'],
                    'post_user_profile_image': post_data['post_user_profile_image'],
                    'likers': post_data['likers'],
                    'like_count': post_data['like_count'],
                    'created_at': post_data['created_at']
                })
        
        # Add non-like notifications
        for notif in notifications:
            if notif['type'] != 'like':
                aggregated.append(notif)
        
        # Sort by most recent
        aggregated.sort(key=lambda x: x['created_at'], reverse=True)
        
        return aggregated[:50]  # Limit to 50 notifications
        
    except Exception as e:
        print(f"Error getting aggregated notifications: {e}")
        return []
    finally:
        conn.close()

@app.route('/')
def home():
    """Home page showing recent posts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get recent posts with user info and engagement counts
    if session.get('user_id'):
        cursor.execute('''
            SELECT 
                p.id, p.text, p.timestamp,
                p.user,
                u.display_name,
                u.profile_image,
                u.is_clanker,
                COUNT(DISTINCT CASE WHEN e.type = 'like' THEN e.id END) as like_count,
                COUNT(DISTINCT CASE WHEN e.type = 'reply' THEN e.id END) as reply_count,
                COUNT(DISTINCT CASE WHEN e.type = 'clanked' THEN e.id END) as clanked_count,
                CASE WHEN user_like.id IS NOT NULL THEN 1 ELSE 0 END as user_liked,
                CASE WHEN user_clanked.id IS NOT NULL THEN 1 ELSE 0 END as user_clanked
            FROM posts p
            LEFT JOIN users u ON LOWER(p.user) = LOWER(u.username)
            LEFT JOIN new_engagements e ON p.id = e.post_id
            LEFT JOIN new_engagements user_like ON p.id = user_like.post_id 
                AND user_like.user_id = ? AND user_like.type = 'like'
            LEFT JOIN new_engagements user_clanked ON p.id = user_clanked.post_id 
                AND user_clanked.user_id = ? AND user_clanked.type = 'clanked'
            GROUP BY p.id
            ORDER BY p.timestamp DESC
            LIMIT 20
        ''', (session['user_id'], session['user_id']))
    else:
        cursor.execute('''
            SELECT 
                p.id, p.text, p.timestamp,
                p.user,
                u.display_name,
                u.profile_image,
                u.is_clanker,
                COUNT(DISTINCT CASE WHEN e.type = 'like' THEN e.id END) as like_count,
                COUNT(DISTINCT CASE WHEN e.type = 'reply' THEN e.id END) as reply_count,
                COUNT(DISTINCT CASE WHEN e.type = 'clanked' THEN e.id END) as clanked_count,
                0 as user_liked,
                0 as user_clanked
            FROM posts p
            LEFT JOIN users u ON LOWER(p.user) = LOWER(u.username)
            LEFT JOIN new_engagements e ON p.id = e.post_id
            GROUP BY p.id
            ORDER BY p.timestamp DESC
            LIMIT 20
        ''')
    
    posts = []
    for row in cursor.fetchall():
        posts.append({
            'id': row[0],
            'content': row[1],
            'created_at': row[2],
            'username': row[3],
            'display_name': row[4] or row[3],  # Fallback to username if no display name
            'profile_image': row[5],
            'is_clanker': bool(row[6]),
            'like_count': row[7],
            'reply_count': row[8],
            'clanked_count': row[9],
            'user_liked': bool(row[10]),
            'user_clanked': bool(row[11])
        })
    
    conn.close()
    
    # Get notification count for logged in user
    notification_count = 0
    if session.get('user_id'):
        notification_count = get_unread_notification_count(session['user_id'])
    
    return render_template('home.html', posts=posts, notification_count=notification_count)

@app.route('/u/<username>')
def user_profile(username):
    """User profile page showing their posts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user info with profile fields (case insensitive)
    cursor.execute('''
        SELECT id, username, display_name, bio, profile_image, banner_image, created_at, is_clanker
        FROM users WHERE LOWER(username) = LOWER(?)
    ''', (username,))
    user = cursor.fetchone()
    
    if not user:
        flash('User not found')
        return redirect(url_for('home'))
    
    # Create user_data first
    user_data = {
        'id': user[0],
        'username': user[1],
        'display_name': user[2] or user[1],  # Fallback to username if no display name
        'bio': user[3] or '',
        'profile_image': user[4] or None,
        'banner_image': user[5] or None,
        'created_at': user[6],
        'is_clanker': bool(user[7])
    }
    
    # Get user's posts with engagement counts and like status (case insensitive)
    if session.get('user_id'):
        cursor.execute('''
            SELECT 
                p.id, p.text, p.timestamp,
                COUNT(DISTINCT CASE WHEN e.type = 'like' THEN e.id END) as like_count,
                COUNT(DISTINCT CASE WHEN e.type = 'reply' THEN e.id END) as reply_count,
                COUNT(DISTINCT CASE WHEN e.type = 'clanked' THEN e.id END) as clanked_count,
                CASE WHEN user_like.id IS NOT NULL THEN 1 ELSE 0 END as user_liked
            FROM posts p
            LEFT JOIN new_engagements e ON p.id = e.post_id
            LEFT JOIN new_engagements user_like ON p.id = user_like.post_id 
                AND user_like.user_id = ? AND user_like.type = 'like'
            WHERE UPPER(p.user) = UPPER(?)
            GROUP BY p.id
            ORDER BY p.timestamp DESC
        ''', (session['user_id'], username))
    else:
        cursor.execute('''
            SELECT 
                p.id, p.text, p.timestamp,
                COUNT(DISTINCT CASE WHEN e.type = 'like' THEN e.id END) as like_count,
                COUNT(DISTINCT CASE WHEN e.type = 'reply' THEN e.id END) as reply_count,
                COUNT(DISTINCT CASE WHEN e.type = 'clanked' THEN e.id END) as clanked_count,
                0 as user_liked
            FROM posts p
            LEFT JOIN new_engagements e ON p.id = e.post_id
            WHERE UPPER(p.user) = UPPER(?)
            GROUP BY p.id
            ORDER BY p.timestamp DESC
        ''', (username,))
    
    posts = []
    for row in cursor.fetchall():
        posts.append({
            'id': row[0],
            'content': row[1],
            'created_at': row[2],
            'like_count': row[3],
            'reply_count': row[4],
            'clanked_count': row[5],
            'user_liked': bool(row[6]),
            'is_clanker': user_data['is_clanker']  # Use the user's clanker status for all their posts
        })
    
    conn.close()
    
    return render_template('profile.html', user=user_data, posts=posts)

@app.route('/t/<int:post_id>')
def post_detail(post_id):
    """Individual post page with replies"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get post details with user info and like status
    if session.get('user_id'):
        cursor.execute('''
            SELECT p.id, p.text, p.timestamp, p.user, u.display_name, u.profile_image, u.is_clanker,
                   CASE WHEN user_like.id IS NOT NULL THEN 1 ELSE 0 END as user_liked,
                   CASE WHEN user_clanked.id IS NOT NULL THEN 1 ELSE 0 END as user_clanked
            FROM posts p
            LEFT JOIN users u ON LOWER(p.user) = LOWER(u.username)
            LEFT JOIN new_engagements user_like ON p.id = user_like.post_id 
                AND user_like.user_id = ? AND user_like.type = 'like'
            LEFT JOIN new_engagements user_clanked ON p.id = user_clanked.post_id 
                AND user_clanked.user_id = ? AND user_clanked.type = 'clanked'
            WHERE p.id = ?
        ''', (session['user_id'], session['user_id'], post_id))
    else:
        cursor.execute('''
            SELECT p.id, p.text, p.timestamp, p.user, u.display_name, u.profile_image, u.is_clanker,
                   0 as user_liked, 0 as user_clanked
            FROM posts p
            LEFT JOIN users u ON LOWER(p.user) = LOWER(u.username)
            WHERE p.id = ?
        ''', (post_id,))
    
    post = cursor.fetchone()
    if not post:
        flash('Post not found')
        return redirect(url_for('home'))
    
    # Get replies with user info
    cursor.execute('''
        SELECT e.content, e.created_at, u.username, u.display_name, u.profile_image
        FROM new_engagements e
        JOIN users u ON e.user_id = u.id
        WHERE e.post_id = ? AND e.type = 'reply'
        ORDER BY e.created_at ASC
    ''', (post_id,))
    
    replies = []
    for row in cursor.fetchall():
        replies.append({
            'content': row[0],
            'created_at': row[1],
            'username': row[2],
            'display_name': row[3] or row[2],
            'profile_image': row[4]
        })
    
    # Get like and clanked counts
    cursor.execute('''
        SELECT COUNT(*) FROM new_engagements 
        WHERE post_id = ? AND type = 'like'
    ''', (post_id,))
    
    like_count = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM new_engagements 
        WHERE post_id = ? AND type = 'clanked'
    ''', (post_id,))
    
    clanked_count = cursor.fetchone()[0]
    
    conn.close()
    
    post_data = {
        'id': post[0],
        'content': post[1],
        'created_at': post[2],
        'username': post[3],
        'display_name': post[4] or post[3],
        'profile_image': post[5],
        'is_clanker': bool(post[6]),
        'like_count': like_count,
        'clanked_count': clanked_count,
        'user_liked': bool(post[7]),
        'user_clanked': bool(post[8])
    }
    
    return render_template('post.html', post=post_data, replies=replies)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required')
            return render_template('register.html')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if username already exists (case insensitive)
        cursor.execute('SELECT id FROM users WHERE LOWER(username) = LOWER(?)', (username,))
        if cursor.fetchone():
            flash('Username already exists (case insensitive)')
            conn.close()
            return render_template('register.html')
        
        try:
            password_hash = hash_password(password)
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                         (username, password_hash))
            conn.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, password_hash FROM users WHERE LOWER(username) = LOWER(?)', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and verify_password(password, user[2]):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Login successful!')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    """Edit user profile"""
    if not session.get('user_id'):
        flash('Please login to edit your profile')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        display_name = request.form.get('display_name', '').strip()
        bio = request.form.get('bio', '').strip()
        
        # Handle profile image upload
        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename:
                # Save file to static/uploads directory
                import os
                upload_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                filename = f"profile_{session['user_id']}_{int(time.time())}.jpg"
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                profile_image = f"/static/uploads/{filename}"
        
        # Update user profile
        cursor.execute('''
            UPDATE users 
            SET display_name = ?, bio = ?, profile_image = COALESCE(?, profile_image)
            WHERE id = ?
        ''', (display_name, bio, profile_image, session['user_id']))
        
        conn.commit()
        conn.close()
        
        flash('Profile updated successfully!')
        return redirect(url_for('user_profile', username=session['username']))
    
    # Get current user profile
    cursor.execute('''
        SELECT username, display_name, bio, profile_image, is_clanker
        FROM users WHERE id = ?
    ''', (session['user_id'],))
    
    user = cursor.fetchone()
    conn.close()
    
    user_data = {
        'username': user[0],
        'display_name': user[1] or '',
        'bio': user[2] or '',
        'profile_image': user[3] or None,
        'is_clanker': bool(user[4])
    }
    
    return render_template('edit_profile.html', user=user_data)

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('home'))

@app.route('/notifications')
def notifications():
    """Notifications page"""
    if 'user_id' not in session:
        flash('Please log in to view notifications')
        return redirect(url_for('login'))
    
    notifications = get_aggregated_notifications(session['user_id'])
    return render_template('notifications.html', notifications=notifications)

@app.route('/api/clear-notifications', methods=['POST'])
def clear_notifications():
    """Mark notifications as seen"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the highest notification ID to mark as seen
    cursor.execute('SELECT MAX(id) FROM notifs WHERE user_id = ?', (session['user_id'],))
    max_id = cursor.fetchone()[0]
    
    if max_id:
        cursor.execute('''
            UPDATE users 
            SET last_seen_notif = ? 
            WHERE id = ?
        ''', (max_id, session['user_id']))
        conn.commit()
    
    conn.close()
    return jsonify({'success': True})

@app.route('/api/notification-count')
def api_notification_count():
    """Get current notification count for user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    count = get_unread_notification_count(session['user_id'])
    return jsonify({'count': count})

@app.route('/api/toggle-clanker', methods=['POST'])
def api_toggle_clanker():
    """Toggle clanker status for current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get current clanker status
        cursor.execute('SELECT is_clanker FROM users WHERE id = ?', (session['user_id'],))
        current_status = cursor.fetchone()
        
        if current_status is None:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Toggle the status
        new_status = not current_status[0]
        cursor.execute('UPDATE users SET is_clanker = ? WHERE id = ?', (new_status, session['user_id']))
        conn.commit()
        
        conn.close()
        return jsonify({'is_clanker': new_status})
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/post', methods=['POST'])
def create_post():
    """Create a new post"""
    if 'user_id' not in session:
        flash('You must be logged in to post')
        return redirect(url_for('home'))
    
    content = request.form.get('content')
    if not content:
        flash('Post content is required')
        return redirect(url_for('home'))
    
    if len(content) > 280:
        flash('Post is too long. Maximum 280 characters.')
        return redirect(url_for('home'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get username from session
    username = session.get('username')
    
    # Insert into existing posts table
    cursor.execute('INSERT INTO posts (text, user, timestamp) VALUES (?, ?, ?)', 
                  (content, username, datetime.now().isoformat()))
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    
    flash('Post created successfully!')
    return redirect(url_for('home'))

# API Routes

@app.route('/api/users/', methods=['GET', 'POST'])
def api_users():
    """API endpoint for users CRUD"""
    if request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, created_at FROM users')
        users = [{'id': row[0], 'username': row[1], 'created_at': row[2]} 
                for row in cursor.fetchall()]
        conn.close()
        return jsonify(users)
    
    elif request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = hash_password(password)
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                         (username, password_hash))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return jsonify({'id': user_id, 'username': username}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Username already exists'}), 409

@app.route('/api/posts/', methods=['GET', 'POST'])
def api_posts():
    """API endpoint for posts CRUD"""
    if request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, p.text, p.timestamp, p.user
            FROM posts p
            ORDER BY p.timestamp DESC
        ''')
        posts = [{'id': row[0], 'content': row[1], 'created_at': row[2], 'username': row[3]} 
                for row in cursor.fetchall()]
        conn.close()
        return jsonify(posts)
    
    elif request.method == 'POST':
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        content = data.get('content')
        
        if not content:
            return jsonify({'error': 'Content required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO posts (text, user, timestamp) VALUES (?, ?, ?)', 
                      (content, session['username'], datetime.now().isoformat()))
        conn.commit()
        post_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'id': post_id, 'content': content}), 201

@app.route('/api/engagements/', methods=['GET', 'POST'])
def api_engagements():
    """API endpoint for engagements CRUD"""
    if request.method == 'GET':
        post_id = request.args.get('post_id')
        if post_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.id, e.type, e.content, e.created_at, u.username
                FROM new_engagements e
                JOIN users u ON e.user_id = u.id
                WHERE e.post_id = ?
                ORDER BY e.created_at ASC
            ''', (post_id,))
            engagements = [{'id': row[0], 'type': row[1], 'content': row[2], 
                           'created_at': row[3], 'username': row[4]} 
                          for row in cursor.fetchall()]
            conn.close()
            return jsonify(engagements)
        else:
            return jsonify({'error': 'post_id parameter required'}), 400
    
    elif request.method == 'POST':
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        post_id = data.get('post_id')
        engagement_type = data.get('type')
        content = data.get('content')
        
        if not post_id or not engagement_type:
            return jsonify({'error': 'post_id and type required'}), 400
        
        if engagement_type not in ['like', 'reply', 'clanked']:
            return jsonify({'error': 'Invalid engagement type'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO new_engagements (user_id, post_id, type, content)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], post_id, engagement_type, content))
            conn.commit()
            engagement_id = cursor.lastrowid
            conn.close()
            
            # Create notification for the post owner
            create_notification(session['user_id'], engagement_type, post_id)
            
            return jsonify({'id': engagement_id, 'type': engagement_type}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Engagement already exists'}), 409

@app.route('/api/engagements/<int:engagement_id>', methods=['DELETE'])
def api_delete_engagement(engagement_id):
    """Delete an engagement (unlike)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user owns this engagement
    cursor.execute('SELECT user_id FROM new_engagements WHERE id = ?', (engagement_id,))
    engagement = cursor.fetchone()
    
    if not engagement:
        conn.close()
        return jsonify({'error': 'Engagement not found'}), 404
    
    if engagement[0] != session['user_id']:
        conn.close()
        return jsonify({'error': 'Not authorized'}), 403
    
    cursor.execute('DELETE FROM new_engagements WHERE id = ?', (engagement_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=True)
