import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Import Base and User model
# Assuming models are in a 'models' directory and user.py contains the User model and Base
from models.user import Base, User  
from models.practice_session import PracticeSession # Import the new PracticeSession model

def setup_database():
    """Sets up the database by creating tables based on SQLAlchemy models."""
    load_dotenv()  # Load environment variables from .env file

    database_url = os.getenv("DATABASE_URL_DEV")
    if not database_url:
        print("Error: DATABASE_URL not found in .env file.")
        return

    try:
        print(f"Connecting to database: {database_url.split('@')[-1].split('/')[0]}...") # Mask credentials for printing
        engine = create_engine(database_url)
        
        # Create all tables in the database (if they don't exist already)
        # This will create tables for all models that inherit from Base
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully (if they didn't already exist).")

    except Exception as e:
        print(f"An error occurred during database setup: {e}")

if __name__ == "__main__":
    print("Starting database setup...")
    setup_database()
    print("Database setup process finished.") 