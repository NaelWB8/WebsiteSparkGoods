from flask import Blueprint, request, jsonify, session
from app.models import db, User, Donation
from app.utils import calculate_level, assign_badges

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/check-auth')
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

@api_bp.route('/user/badges')
def get_user_badges():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'badges': [badge.name for badge in user.badges]})

@api_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Name, email and password required'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    new_user = User(
        name=data['name'],
        email=data['email']
    )
    new_user.set_password(data['password'])

    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.id

    return jsonify({'message': 'Registration successful'}), 201

@api_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user.id

    return jsonify({'message': 'Login successful'})

@api_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out'})

@api_bp.route('/donate', methods=['POST'])
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
