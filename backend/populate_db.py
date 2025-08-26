# populate_db.py

from models import Base, User, Post, Connection
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
import random
from datetime import datetime, timedelta

DATABASE_URL = 'postgresql://user:password@db:5432/social_db'

def populate_data(session=None):
    print("Populating test data...")

    # Create engine and session if not provided
    engine = create_engine(DATABASE_URL)
    if session is None:
        Session = sessionmaker(bind=engine)
        session = Session()

    # Create tables
    Base.metadata.create_all(engine)

    # Example: Create 20 users
    for i in range(20):
        user = User(
            email=f"user{i}@example.com",
            password_hash=generate_password_hash(f"password{i}"),
            display_name=f"Name{i} Surname{i}",
            profile_picture_url=f"pic{i}.jpg"
        )
        session.add(user)

    # Commit all users
    session.commit()
    print("Created 20 users.")

    # Example: create posts and connections (simplified)
    for i in range(20):
        post = Post(
            user_id=i+1,
            caption=f"Caption {i}",
            image_url=f"image{i}.jpg",
            created_at=datetime.now()
        )
        session.add(post)

    session.commit()
    print(f"Created {20} posts.")

    # Add some connections
    for i in range(0, 20, 2):
        conn = Connection(user_id1=i+1, user_id2=i+2)
        session.add(conn)

    session.commit()
    print(f"Created {10} connections.")
    print("Test data population complete.")

def main():
    populate_data()

if __name__ == "__main__":
    main()