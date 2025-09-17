from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, send_from_directory, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sparkgoods.db'
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    days=7)  # Session lasts 7 days

# Initialize extensions
# SQLAlchemy itu ORM, Object-Relational-Mapping, supaya Python bisa 'communicate' ke SQL tanpa bahasa SQL.
db = SQLAlchemy(app)
CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000", "http://localhost:8000", "http://127.0.0.1:8000"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Database Models


class User(db.Model):  # db.Model itu base class dari SQLAlchemy
    id = db.Column(db.Integer, primary_key=True)  # kolom ID
    name = db.Column(db.String(100), nullable=False)  # kolom nama
    email = db.Column(db.String(100), unique=True,
                      nullable=False)  # kolom email dsb
    password = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)
    tiktok_id = db.Column(db.String(100), nullable=True)
    level = db.Column(db.String(20), default='Bronze')
    donations = db.relationship('Donation', backref='user', lazy=True)


class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    # 'uang', 'barang', 'tiktok'
    donation_type = db.Column(db.String(50), nullable=False)
    points_earned = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)


# Association table for user-badge many-to-many relationship
user_badge = db.Table('user_badge',
                      db.Column('user_id', db.Integer,
                                db.ForeignKey('user.id')),
                      db.Column('badge_id', db.Integer,
                                db.ForeignKey('badge.id'))
                      )

# Helper Functions


def calculate_level(points):
    if points >= 2000:
        return 'Platinum'
    elif points >= 500:
        return 'Gold'
    elif points >= 100:
        return 'Silver'
    return 'Bronze'


def assign_badges(user):
    user_badges_set = {badge.name for badge in user.badges}
    new_badges = []

    # Badge conditions
    total_donations = len(user.donations)
    donation_types = {d.donation_type for d in user.donations}
    total_barang = sum(
        d.amount for d in user.donations if d.donation_type == 'barang')
    total_tiktok = sum(
        d.amount for d in user.donations if d.donation_type == 'tiktok')
    total_amount = sum(d.amount for d in user.donations)

    if total_donations >= 1 and 'Pemula Dermawan' not in user_badges_set:
        new_badges.append('Pemula Dermawan')
    if len(donation_types) >= 2 and 'Multi Kontributor' not in user_badges_set:
        new_badges.append('Multi Kontributor')
    if total_barang >= 100000 and 'Fashion Giver' not in user_badges_set:
        new_badges.append('Fashion Giver')
    if total_tiktok >= 500000 and 'Live Warrior' not in user_badges_set:
        new_badges.append('Live Warrior')
    if total_amount >= 2000000 and 'Sultan Dermawan' not in user_badges_set:
        new_badges.append('Sultan Dermawan')

    for badge_name in new_badges:
        badge = Badge.query.filter_by(name=badge_name).first()
        if badge and badge not in user.badges:
            user.badges.append(badge)

# Frontend Routes


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/index')
def index_alt():
    return render_template('index.html')


@app.route('/financials')
def financials():
    return render_template('financials.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/rewards')
def rewards():
    return render_template('rewards.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/')

    # Get user badges
    badges = [badge.name for badge in user.badges]

    return render_template('dashboard.html',
                           user={
                               'id': user.id,
                               'name': user.name,
                               'email': user.email,
                               'points': user.points,
                               'level': user.level,
                               'badges': badges
                           })


# API Routes


@app.route('/api/check-auth')
def check_auth():
    if 'user_id' not in session:
        return jsonify({'authenticated': False})

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'authenticated': False})

    return jsonify({
        'authenticated': True,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'points': user.points,
            'level': user.level
        }
    })


@app.route('/api/user/badges')
def get_user_badges():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'badges': [badge.name for badge in user.badges]
    })


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Name, email and password are required'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    try:
        hashed_password = generate_password_hash(data['password'])
        new_user = User(
            name=data['name'],
            email=data['email'],
            password=hashed_password,
            points=0,
            level='Bronze'
        )
        db.session.add(new_user)
        db.session.commit()

        # Auto-login after registration
        session['user_id'] = new_user.id
        return jsonify({
            'message': 'Registration successful',
            'user': {
                'id': new_user.id,
                'name': new_user.name,
                'email': new_user.email
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    if not user:
        return jsonify({'error': 'No account found with this email'}), 401

    if not check_password_hash(user.password, data['password']):
        return jsonify({'error': 'Incorrect password'}), 401

    session['user_id'] = user.id
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'points': user.points,
            'level': user.level
        }
    })


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})


@app.route('/api/donate', methods=['POST'])
def donate():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or not data.get('type') or not data.get('amount'):
        return jsonify({'error': 'Type and amount are required'}), 400

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        # Calculate points based on donation type
        donation_type = data['type']
        amount = int(data['amount'])

        if donation_type == 'uang':
            points = amount // 10000
        elif donation_type == 'barang':
            points = amount // 5000
        elif donation_type == 'tiktok':
            points = amount // 10000
        else:
            return jsonify({'error': 'Invalid donation type'}), 400

        # Create donation record
        donation = Donation(
            user_id=user.id,
            amount=amount,
            donation_type=donation_type,
            points_earned=points
        )

        # Update user
        user.points += points
        user.level = calculate_level(user.points)
        assign_badges(user)

        db.session.add(donation)
        db.session.commit()

        return jsonify({
            'message': 'Donation recorded',
            'points_earned': points,
            'total_points': user.points,
            'level': user.level,
            'badges': [badge.name for badge in user.badges]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Static files


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Error handling


@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404


# Initialization
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Create initial badges if they don't exist
        badges = [
            'Pemula Dermawan',
            'Multi Kontributor',
            'Fashion Giver',
            'Live Warrior',
            'Sultan Dermawan'
        ]

        for badge_name in badges:
            if not Badge.query.filter_by(name=badge_name).first():
                db.session.add(Badge(name=badge_name))

        db.session.commit()

    app.run(debug=True, port=5000)


def init_db():
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()


init_db()


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400

    try:
        with sqlite3.connect("users.db") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                      (name, email, password))
            conn.commit()
        return jsonify({'message': 'Registration successful'}), 200
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already registered'}), 400


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()

        if user:
            session['user'] = user[1]  # Save name in session
            return jsonify({'message': 'Login successful'}), 200
        else:
            return jsonify({'error': 'Invalid email or password'}), 401


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return 'Unauthorized', 401
    return f'Welcome, {session["user"]}!'


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# --- End of Auth Section ---


if __name__ == '__main__':
    app.run(debug=True)
