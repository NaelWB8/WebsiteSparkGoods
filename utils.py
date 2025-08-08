from models import Badge, db


def calculate_points(source, value):
    if source == 'barang':
        return value // 10000
    elif source in ['tiktok', 'tunai']:
        return value // 10000
    return 0


def assign_badges(user):
    badge_names = [badge.name for badge in user.badges]
    if 'Pemula Dermawan' not in badge_names:
        user.badges.append(get_or_create_badge('Pemula Dermawan'))

    sumber = {don.source for don in user.donations}
    if 'Multi Kontributor' not in badge_names and len(sumber) >= 2:
        user.badges.append(get_or_create_badge('Multi Kontributor'))

    barang_count = sum(1 for d in user.donations if d.source ==
                       'barang' and d.value >= 10000)
    if 'Fashion Giver' not in badge_names and barang_count >= 5:
        user.badges.append(get_or_create_badge('Fashion Giver'))

    tiktok_don = [d for d in user.donations if d.source == 'tiktok']
    if 'Live Warrior' not in badge_names and len(tiktok_don) >= 3:
        user.badges.append(get_or_create_badge('Live Warrior'))

    if 'Sultan Dermawan' not in badge_names and user.points > 100:
        user.badges.append(get_or_create_badge('Sultan Dermawan'))


def get_or_create_badge(name):
    badge = Badge.query.filter_by(name=name).first()
    if not badge:
        badge = Badge(name=name)
        db.session.add(badge)
        db.session.commit()
    return badge
