from app.models import Badge, db

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
