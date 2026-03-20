from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

user_badge = db.Table(
    'user_badge',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)
    tiktok_id = db.Column(db.String(100))
    level = db.Column(db.String(20), default='Bronze')

    donations = db.relationship('Donation', backref='user', lazy=True)
    badges = db.relationship(
        'Badge',
        secondary=user_badge,
        backref=db.backref('users', lazy=True)
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
