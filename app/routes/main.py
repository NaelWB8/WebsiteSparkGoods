from hashlib import md5
from flask import Blueprint, render_template, session, redirect, request
from sqlalchemy import func, desc
from app.models import db, User, Donation

main_bp = Blueprint('main', __name__)


def _public_name(name):
    parts = (name or '').strip().split()
    if not parts:
        return 'Anonymous'
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."

@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template('index.html')

@main_bp.route('/financials')
def financials():
    return render_template('financials.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')

@main_bp.route('/rewards')
def rewards():
    return render_template('rewards.html')

@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    user = User.query.get(session['user_id'])
    if not user:
        return redirect('/')

    badges = [badge.name for badge in user.badges]
    total_donation = db.session.query(func.coalesce(func.sum(Donation.amount), 0)).filter(
        Donation.user_id == user.id).scalar() or 0
    donation_count = Donation.query.filter_by(user_id=user.id).count()
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

    return render_template('dashboard.html', user={
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'profile_image': profile_image,
        'account_created': first_activity.isoformat() if first_activity else None,
        'donation_total': total_donation,
        'donation_count': donation_count,
        'points': user.points,
        'level': user.level,
        'badges': badges,
        'rank': rank,
        'recent_activity': recent_activity
    })


@main_bp.route('/leaderboard')
def leaderboard():
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

    return render_template('leaderboard.html', leaderboard={
        'entries': entries,
        'page': pagination.page,
        'pages': pagination.pages,
        'has_next': pagination.has_next
    })
