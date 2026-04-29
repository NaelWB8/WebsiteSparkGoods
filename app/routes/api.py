from flask import Blueprint, request, jsonify, session
from hashlib import md5
from sqlalchemy import func, desc
from app.models import db, User, Donation
from app.utils import calculate_level, assign_badges

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _public_name(name):
    parts = (name or '').strip().split()
    if not parts:
        return 'Anonymous'
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."

@api_bp.route('/check-auth')
def check_auth():
    if 'user_id' not in session:
        return jsonify({'authenticated': False})

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'authenticated': False})

    total_donation = db.session.query(func.coalesce(func.sum(Donation.amount), 0)).filter(
        Donation.user_id == user.id).scalar() or 0
    first_activity = db.session.query(func.min(Donation.created_at)).filter(
        Donation.user_id == user.id).scalar()

    leaderboard_rows = db.session.query(
        User.id,
        func.coalesce(func.sum(Donation.amount), 0).label('total_donation')
    ).outerjoin(Donation, Donation.user_id == User.id).group_by(User.id).order_by(
        desc('total_donation'),
        User.id.asc()
    ).all()
    rank = next((idx for idx, row in enumerate(leaderboard_rows, start=1)
                 if row.id == user.id), None)

    recent_donations = Donation.query.filter_by(user_id=user.id).order_by(
        Donation.created_at.desc()).limit(5).all()
    recent_activity = [
        {
            'type': donation.donation_type,
            'amount': donation.amount,
            'points_earned': donation.points_earned,
            'created_at': donation.created_at.isoformat() if donation.created_at else None
        }
        for donation in recent_donations
    ]
    gravatar_hash = md5(user.email.strip().lower().encode('utf-8')).hexdigest()
    profile_image = f"https://www.gravatar.com/avatar/{gravatar_hash}?d=identicon&s=160"

    return jsonify({
        'authenticated': True,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'profile_image': profile_image,
            'donation_total': total_donation,
            'account_created': first_activity.isoformat() if first_activity else None,
            'points': user.points,
            'level': user.level,
            'rank': rank,
            'badges': [badge.name for badge in user.badges],
            'recent_activity': recent_activity
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
        'donation_total': sum(d.amount for d in user.donations),
        'total_points': user.points,
        'level': user.level,
        'badges': [badge.name for badge in user.badges]
    })


@api_bp.route('/leaderboard')
def get_leaderboard():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 30)

    pagination = db.session.query(
        User.id,
        User.name,
        func.coalesce(func.sum(Donation.amount), 0).label('donation_total'),
        User.points,
        User.level,
        func.min(Donation.created_at).label('joined_date')
    ).outerjoin(Donation, Donation.user_id == User.id).group_by(
        User.id, User.name, User.points, User.level
    ).order_by(
        desc('donation_total'),
        User.points.desc(),
        User.id.asc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    entries = [
        {
            'rank': ((pagination.page - 1) * pagination.per_page) + idx,
            'name': _public_name(row.name),
            'donation_total': row.donation_total,
            'points': row.points,
            'level': row.level,
            'joined_date': row.joined_date.isoformat() if row.joined_date else None
        }
        for idx, row in enumerate(pagination.items, start=1)
    ]

    return jsonify({
        'entries': entries,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_next': pagination.has_next
    })
