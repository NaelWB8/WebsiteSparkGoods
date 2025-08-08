# app.py
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import requests
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'sqlite:///sparkgoods.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

# init DB
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

# --------------- HELPERS ----------------


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
    # rules similar to your frontend rewards.html
    if donation_type == 'uang':
        return max(0, amount // 10000)  # 1 point per 10k
    if donation_type == 'barang':
        return max(0, amount // 5000)   # 1 point per 5k
    if donation_type == 'tiktok':
        return max(0, amount // 10000)
    return 0

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
    # static page that will fetch /api/leaderboard from frontend JS
    return render_template('leaderboard.html')


@app.route('/admin')
@admin_required
def admin():
    donations = Donation.query.order_by(Donation.created_at.desc()).all()
    users = User.query.order_by(User.points.desc()).all()
    return render_template('admin.html', donations=donations, users=users)

# ---------------- API - AUTH ----------------


@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json(force=True)
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
    data = request.get_json(force=True)
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
        return jsonify({'authenticated': False}), 200
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'authenticated': False}), 200

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

# --------------- API - DONATION ----------------


@app.route('/api/donate', methods=['POST'])
@login_required
def api_donate():
    data = request.get_json(force=True)
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

# --------------- API - LEADERBOARD ----------------


@app.route('/api/leaderboard')
def api_leaderboard():
    users = User.query.order_by(User.points.desc()).limit(10).all()
    out = [{'name': u.name, 'points': u.points, 'id': u.id} for u in users]
    return jsonify({'leaderboard': out})

# --------------- API - ADMIN (donation management) ----------------


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
    # roll back points to user
    user = User.query.get(d.user_id)
    if user:
        user.points = max(0, user.points - (d.points_earned or 0))
    db.session.delete(d)
    db.session.commit()
    return jsonify({'message': 'Deleted'})

# --------------- API - TIKTOK SYNC (mock + real flow) ----------------


@app.route('/api/tiktok-sync', methods=['POST'])
@admin_required
def api_tiktok_sync():
    """
    This endpoint attempts to fetch orders from TikTok Shop API and record completed purchases as donations.
    For real usage: set TIKTOK_API_KEY env var and update the URL to the correct TikTok Shop endpoint.
    """
    TIKTOK_API_KEY = os.getenv('TIKTOK_API_KEY')
    if not TIKTOK_API_KEY:
        return jsonify({'error': 'TIKTOK_API_KEY not configured'}), 500

    headers = {'Authorization': f'Bearer {TIKTOK_API_KEY}'}
    # Example URL (replace with real official endpoint)
    url = os.getenv('TIKTOK_ORDERS_URL',
                    'https://open-api.tiktokglobalshop.com/api/orders')

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        return jsonify({'error': 'Failed to fetch from TikTok', 'detail': str(e)}), 500

    # Example: expect payload['orders'] to be a list of orders
    orders = payload.get('orders') or payload.get('data') or []
    processed = 0

    for order in orders:
        # normalize: try buyer email and total price
        buyer_email = order.get('buyer_email') or order.get(
            'buyer', {}).get('email')
        total_price = int(float(order.get('total_price', 0))) if order.get(
            'total_price') else int(order.get('total', 0) or 0)
        status = order.get('status') or order.get('order_status')

        if not buyer_email or not total_price:
            continue
        # only count completed orders
        if str(status).lower() not in ('delivered', 'completed', 'paid'):
            continue

        user = User.query.filter_by(email=buyer_email).first()
        if not user:
            # optionally create a guest user or skip
            continue

        pts = calculate_points('tiktok', total_price)
        d = Donation(user_id=user.id, type='tiktok',
                     amount=total_price, points_earned=pts)
        user.points += pts
        db.session.add(d)
        processed += 1

    db.session.commit()
    return jsonify({'processed': processed})

# --------------- DB init helper ----------------


@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database initialized')


if __name__ == '__main__':
    app.run(debug=True)
