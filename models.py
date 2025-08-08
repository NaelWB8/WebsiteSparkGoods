from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

user_badge = db.Table('user_badge',
                      db.Column('user_id', db.Integer,
                                db.ForeignKey('user.id')),
                      db.Column('badge_id', db.Integer,
                                db.ForeignKey('badge.id'))
                      )


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    points = db.Column(db.Integer, default=0)
    donations = db.relationship('Donation', backref='user', lazy=True)
    badges = db.relationship('Badge', secondary=user_badge, backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(50))
    value = db.Column(db.Integer)
    points = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
