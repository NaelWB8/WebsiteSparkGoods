from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import requests
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')

# Config DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'sqlite:///sparkgoods.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# Aktifkan CORS + credentials
CORS(app, supports_credentials=True)

# Init DB
db = SQLAlchemy(app)

# ---------------- MODELS ----------------


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default='user')


class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50))
    amount = db.Column(db.Integer)
    points_earned = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- HELPERS ----------------


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


def get_level(points: int):
    if points >= 1500:
        return 'Platinum'
    if points >= 500:
        return 'Gold'
    if points >= 100:
        return 'Silver'
    return 'Bronze'


def calculate_points(donation_type, amount):
    if donation_type == 'uang':
        return max(0, amount // 10000)
    if donation_type == 'barang':
        return max(0, amount // 5000)
    if donation_type == 'tiktok':
        return max(0, amount // 10000)
    return 0


def parse_request_data():
    """Ambil data dari JSON atau FormData"""
    data = request.get_json(silent=True)
    if not data:
        data = request.form.to_dict()
    return data

# ---------------- ROUTES ----------------


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)


@app.route('/leaderboard')
def leaderboard_view():
    return render_template('leaderboard.html')


@app.route('/admin')
@admin_required
def admin():
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    users = User.query.order_by(User.points.desc()).all()
    return render_template('admin.html', donations=donations, users=users)

# ---------------- API AUTH ----------------


@app.route('/api/register', methods=['POST'])
def api_register():
    data = parse_request_data()
    print("Register data:", data)  # debug

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({'error': 'Missing fields'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    hashed = generate_password_hash(password)
    user = User(name=name, email=email, password=hashed)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id

    return jsonify({'message': 'Registered', 'user': {'name': user.name, 'email': user.email}})


@app.route('/api/login', methods=['POST'])
def api_login():
    data = parse_request_data()
    print("Login data:", data)  # debug

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing fields'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user.id
    return jsonify({'message': 'Logged in'})


@app.route('/api/check-auth')
def api_check_auth():
    if 'user_id' not in session:
        return jsonify({'authenticated': False})
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'authenticated': False})

    return jsonify({
        'authenticated': True,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'points': user.points,
            'level': get_level(user.points),
            'badges': []
        }
    })


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

# ---------------- API DONATION ----------------


@app.route('/api/donate', methods=['POST'])
@login_required
def api_donate():
    data = parse_request_data()
    donation_type = data.get('type')
    amount = int(data.get('amount') or 0)

    if not donation_type or amount <= 0:
        return jsonify({'error': 'Invalid donation data'}), 400

    user = User.query.get(session['user_id'])
    points = calculate_points(donation_type, amount)

    donation = Donation(user_id=user.id, type=donation_type,
                        amount=amount, points_earned=points)
    user.points += points

    db.session.add(donation)
    db.session.commit()

    return jsonify({'message': 'Donation recorded', 'points_earned': points, 'user_points': user.points})

# ---------------- API LEADERBOARD ----------------


@app.route('/api/leaderboard')
def api_leaderboard():
    users = User.query.order_by(User.points.desc()).limit(10).all()
    out = [{'name': u.name, 'points': u.points, 'id': u.id} for u in users]
    return jsonify({'leaderboard': out})

# ---------------- ADMIN API ----------------


@app.route('/api/admin/donations', methods=['GET'])
@admin_required
def api_admin_get_donations():
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    out = []
    for d in donations:
        u = User.query.get(d.user_id)
        out.append({
            'id': d.id,
            'user': u.name if u else '—',
            'email': u.email if u else '—',
            'type': d.type,
            'amount': d.amount,
            'points': d.points_earned,
            'created_at': d.created_at.isoformat()
        })
    return jsonify({'donations': out})


@app.route('/api/admin/donation/<int:donation_id>', methods=['DELETE'])
@admin_required
def api_admin_delete_donation(donation_id):
    d = Donation.query.get(donation_id)
    if not d:
        return jsonify({'error': 'Not found'}), 404
    user = User.query.get(d.user_id)
    if user:
        user.points = max(0, user.points - (d.points_earned or 0))
    db.session.delete(d)
    db.session.commit()
    return jsonify({'message': 'Deleted'})

# ---------------- INIT DB ----------------


@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database initialized')


if __name__ == '__main__':
    app.run(debug=True)
