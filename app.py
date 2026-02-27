from datetime import timedelta
from flask import Flask, request, jsonify, session, send_from_directory, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

# =========================
# App Setup
# =========================

app = Flask(__name__, static_folder='static', template_folder='templates')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sparkgoods.db'
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)

CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000",
                    "http://localhost:8000", "http://127.0.0.1:8000"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# =========================
# Models
# =========================


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)
    tiktok_id = db.Column(db.String(100))
    level = db.Column(db.String(20), default='Bronze')

    donations = db.relationship('Donation', backref='user', lazy=True)

    badges = db.relationship(
        'Badge',
        secondary='user_badge',
        backref=db.backref('users', lazy=True)
    )


class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    donation_type = db.Column(db.String(50), nullable=False)
    points_earned = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)


user_badge = db.Table(
    'user_badge',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'))
)

# =========================
# Helper Functions
# =========================


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

    total_donations = len(user.donations)
    donation_types = {d.donation_type for d in user.donations}
    total_barang = sum(
        d.amount for d in user.donations if d.donation_type == 'barang')
    total_tiktok = sum(
        d.amount for d in user.donations if d.donation_type == 'tiktok')
    total_amount = sum(d.amount for d in user.donations)

    conditions = [
        ('Pemula Dermawan', total_donations >= 1),
        ('Multi Kontributor', len(donation_types) >= 2),
        ('Fashion Giver', total_barang >= 100000),
        ('Live Warrior', total_tiktok >= 500000),
        ('Sultan Dermawan', total_amount >= 2000000),
    ]

    for badge_name, condition in conditions:
        if condition and badge_name not in user_badges_set:
            badge = Badge.query.filter_by(name=badge_name).first()
            if badge:
                user.badges.append(badge)

# =========================
# Frontend Routes
# =========================


@app.route('/')
@app.route('/index')
def index():
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

    badges = [badge.name for badge in user.badges]

    return render_template('dashboard.html', user={
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'points': user.points,
        'level': user.level,
        'badges': badges
    })

# =========================
# API Routes
# =========================


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

    return jsonify({'badges': [badge.name for badge in user.badges]})


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Name, email and password required'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    hashed_password = generate_password_hash(data['password'])

    new_user = User(
        name=data['name'],
        email=data['email'],
        password=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.id

    return jsonify({'message': 'Registration successful'}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user.id

    return jsonify({'message': 'Login successful'})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out'})


@app.route('/api/donate', methods=['POST'])
def donate():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    donation_type = data.get('type')
    amount = int(data.get('amount', 0))

    user = User.query.get(session['user_id'])

    if donation_type == 'uang':
        points = amount // 10000
    elif donation_type == 'barang':
        points = amount // 5000
    elif donation_type == 'tiktok':
        points = amount // 10000
    else:
        return jsonify({'error': 'Invalid donation type'}), 400

    donation = Donation(
        user_id=user.id,
        amount=amount,
        donation_type=donation_type,
        points_earned=points
    )

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

# =========================
# Static + Errors
# =========================


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

# =========================
# Initialization
# =========================


def initialize_database():
    db.create_all()

    initial_badges = [
        'Pemula Dermawan',
        'Multi Kontributor',
        'Fashion Giver',
        'Live Warrior',
        'Sultan Dermawan'
    ]

    for badge_name in initial_badges:
        if not Badge.query.filter_by(name=badge_name).first():
            db.session.add(Badge(name=badge_name))

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        initialize_database()

    app.run(debug=True, port=5000)