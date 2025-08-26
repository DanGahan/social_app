# populate_db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Post, Connection, ConnectionRequest
from config import Config
from werkzeug.security import generate_password_hash
import random
from datetime import datetime, timedelta

# Database setup
app_config = Config()
engine = create_engine(app_config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# ----------------------------
# Test data arrays
# ----------------------------
IMAGE_URLS = [
    "https://as1.ftcdn.net/v2/jpg/01/21/06/48/1000_F_121064813_5CONOqmYSLyCLJlkRn3FsUl8733cg2qc.jpg",
    "https://t3.ftcdn.net/jpg/09/38/20/44/360_F_938204480_5BZPwZ4dL5iujr2XZwzkxdFeQJoRDsRE.jpg",
    "https://images.contentstack.io/v3/assets/bltcedd8dbd5891265b/blt4a4af7e6facea579/6668df6ceca9a600983250ac/beautiful-flowers-hero.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/b/b1/Beautiful-landscape.png",
    "https://media.restless.co.uk/uploads/2024/05/the-most-beautiful-places-to-visit-in-turkey-e1714748961993.jpg",
    "https://media.timeout.com/images/106041640/750/562/image.jpg",
    "https://travelatheart.de/wp-content/uploads/2022/02/iceland-brs-216.jpg",
    "https://www.barcelo.com/guia-turismo/wp-content/uploads/2024/09/ok-paisajes-de-tenerife.jpg",
    "https://wildnordics.com/wp-content/uploads/2019/01/France.jpg",
    "https://delveintoeurope.com/wp-content/uploads/2018/06/wengen2-1024x683.jpg",
    "https://www.mediastorehouse.co.uk/p/780/beautiful-beach-tranquil-scenery-33032242.jpg",
    "https://i.natgeofe.com/n/9ad480f8-ca3a-46b2-842d-889d93afc43e/deosai-national-park-pakistan.jpg"
]

PROFILE_PIC_URLS = [
    "https://wallpapers.com/images/hd/cool-profile-picture-paper-bag-head-4co57dtwk64fb7lv.jpg",
    "https://res.cloudinary.com/jerrick/image/upload/d_642250b563292b35f27461a7.png,f_jpg,q_auto,w_720/6734c8df768161001d967e25.png",
    "https://www.befunky.com/images/wp/wp-2024-12-creative-profile-pics-double-exposure.jpg?auto=avif,webp&format=jpg&width=944",
    "https://marketplace.canva.com/EAFOWUXOOvs/1/0/1600w/canva-green-gradient-minimalist-simple-instagram-profile-picture-tBlf3wVYGhg.jpg",
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQw9ozccPOSAwiNtYwqPLk6Gzbk-ltR8cv7Hw&s"
]

FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona", "George", "Hannah", "Ian", "Julia"]
LAST_NAMES = ["Smith", "Jones", "Williams", "Brown", "Davies", "Evans", "Wilson", "Taylor", "Wright", "White"]

CAPTION_MESSAGES = [
    "Such a beautiful scene!",
    "My favourite place.",
    "Absolutely stunning!",
    "Wish I was there.",
    "Nature at its best.",
    "Breathtaking view.",
    "Incredible landscape.",
    "Pure serenity.",
    "A moment of peace.",
    "Simply gorgeous."
]

# ----------------------------
# Populate test data
# ----------------------------
def populate_data(session=None):
    print("Populating test data...")

    # Create engine and session if not provided
    if session is None:
        Session = sessionmaker(bind=engine)
        session = Session()

    # Create tables
    Base.metadata.create_all(engine)

    # Clear existing data
    session.query(Connection).delete()
    session.query(ConnectionRequest).delete()
    session.query(Post).delete()
    session.query(User).delete()
    session.commit()

    users = []
    # Create 20 users
    for i in range(1, 21):
        email = f"user{i}@example.com"
        password_hash = generate_password_hash(f"password{i}")
        display_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        profile_picture_url = random.choice(PROFILE_PIC_URLS)

        user = User(email=email, password_hash=password_hash,
                    display_name=display_name,
                    profile_picture_url=profile_picture_url)
        session.add(user)
        users.append(user)

    session.commit()
    print(f"Created {len(users)} users.")

    # Create posts for each user
    posts = []
    for user in users:
        num_posts = random.randint(3, 5)
        for _ in range(num_posts):
            image_url = random.choice(IMAGE_URLS)
            caption = random.choice(CAPTION_MESSAGES)
            random_days = random.randint(0, 6)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            created_at = datetime.now() - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
            post = Post(user_id=user.id, image_url=image_url, caption=caption, created_at=created_at)
            session.add(post)
            posts.append(post)

    session.commit()
    print(f"Created {len(posts)} posts.")

    # Create connections
    connections_count = 0
    for i, user1 in enumerate(users):
        possible_connections = [u for u in users if u.id != user1.id]
        random.shuffle(possible_connections)
        for user2 in possible_connections[:2]:
            u1_id = min(user1.id, user2.id)
            u2_id = max(user1.id, user2.id)
            existing_connection = session.query(Connection).filter_by(user_id1=u1_id, user_id2=u2_id).first()
            if not existing_connection:
                connection = Connection(user_id1=u1_id, user_id2=u2_id)
                session.add(connection)
                connections_count += 1

    session.commit()
    print(f"Created {connections_count} connections.")
    print("Test data population complete.")

# ----------------------------
# Main
# ----------------------------
def main():
    populate_data()

if __name__ == "__main__":
    main()