from flask import Blueprint, render_template, session, redirect
from app.models import User

main_bp = Blueprint('main', __name__)

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

    return render_template('dashboard.html', user={
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'points': user.points,
        'level': user.level,
        'badges': badges
    })
