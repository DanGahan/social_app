from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User
from config import Config

# Load configuration
app_config = Config()

# Database setup
engine = create_engine(app_config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Query for the user with display_name 'Ian Jones'
    user = session.query(User).filter_by(display_name='Ian Jones').first()

    if user:
        print(f"Email of Ian Jones: {user.email}")
    else:
        print("User with display name 'Ian Jones' not found.")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    session.close()