import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from models.user import User # Assuming your User model is in models/user.py

class DatabaseManager:
    def __init__(self, db_url=None):
        if db_url:
            self.db_url = db_url
        else:
            load_dotenv() # Load environment variables from .env
            self.db_url = os.getenv("DATABASE_URL")
            if not self.db_url:
                raise ValueError("DATABASE_URL not set in environment or .env file")

        self.engine = create_engine(self.db_url)
        self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self):
        """Provides a database session."""
        return self._SessionLocal()

    def add_user(self, user_id: int, first_name: str = None, last_name: str = None, username: str = None, preferred_language: str = None):
        """Adds a new user to the database."""
        session = self.get_session()
        try:
            new_user = User(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                preferred_language=preferred_language
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return new_user
        except Exception as e:
            session.rollback()
            print(f"Error adding user: {e}") # Or use proper logging
            return None
        finally:
            session.close()

    def get_user_by_telegram_id(self, telegram_user_id: int):
        """Retrieves a user by their Telegram user_id."""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.user_id == telegram_user_id).first()
            return user
        except Exception as e:
            print(f"Error retrieving user: {e}") # Or use proper logging
            return None
        finally:
            session.close()

# Example of how to initialize (optional, for direct testing of this file)
if __name__ == '__main__':
    print("Initializing DatabaseManager...")
    try:
        db_manager = DatabaseManager()
        print("DatabaseManager initialized successfully.")
        print("Attempting to get a session...")
        example_session = db_manager.get_session()
        if example_session:
            print("Session obtained successfully.")
            example_session.close()
        else:
            print("Failed to obtain session.")
    except ValueError as ve:
        print(f"Error during initialization: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 