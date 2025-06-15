import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

from models.user import User # Assuming your User model is in models/user.py
from utils.error_handler import BotError

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_url=None):
        if db_url:
            self.db_url = db_url
        else:
            load_dotenv() # Load environment variables from .env
            self.db_url = os.getenv("DATABASE_URL")
            if not self.db_url:
                raise ValueError("DATABASE_URL not set in environment or .env file")

        try:
            self.engine = create_engine(self.db_url)
            self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("DatabaseManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseManager: {e}")
            raise BotError(f"Database initialization failed: {str(e)}")

    def get_session(self):
        """Provides a database session."""
        try:
            return self._SessionLocal()
        except Exception as e:
            logger.error(f"Failed to create database session: {e}")
            raise BotError(f"Database session creation failed: {str(e)}")

    def add_user(self, user_id: int, first_name: str = None, last_name: str = None, 
                username: str = None, preferred_language: str = None) -> User:
        """
        Adds a new user to the database.
        
        Args:
            user_id: Telegram user ID
            first_name: User's first name
            last_name: User's last name
            username: User's username
            preferred_language: User's preferred language code
            
        Returns:
            User: The newly created user object
            
        Raises:
            BotError: If user creation fails
        """
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
            logger.info(f"Successfully added new user: {user_id}")
            return new_user
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error while adding user {user_id}: {e}")
            raise BotError(f"Failed to create user: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error while adding user {user_id}: {e}")
            raise BotError(f"Unexpected error while creating user: {str(e)}")
        finally:
            session.close()

    def get_user_by_telegram_id(self, telegram_user_id: int) -> User:
        """
        Retrieves a user by their Telegram user_id.
        
        Args:
            telegram_user_id: The Telegram user ID to look up
            
        Returns:
            User: The found user object or None if not found
            
        Raises:
            BotError: If database query fails
        """
        session = self.get_session()
        try:
            user = session.query(User).filter(User.user_id == telegram_user_id).first()
            if user:
                logger.debug(f"Found user {telegram_user_id}")
            else:
                logger.debug(f"No user found for Telegram ID {telegram_user_id}")
            return user
        except SQLAlchemyError as e:
            logger.error(f"Database error while retrieving user {telegram_user_id}: {e}")
            raise BotError(f"Failed to retrieve user: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while retrieving user {telegram_user_id}: {e}")
            raise BotError(f"Unexpected error while retrieving user: {str(e)}")
        finally:
            session.close()

    def update_user(self, user: User) -> bool:
        """
        Updates an existing user in the database.
        
        Args:
            user: The User object to update
            
        Returns:
            bool: True if update was successful
            
        Raises:
            BotError: If update fails
        """
        session = self.get_session()
        try:
            session.add(user)
            session.commit()
            logger.info(f"Successfully updated user {user.user_id}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error while updating user {user.user_id}: {e}")
            raise BotError(f"Failed to update user: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error while updating user {user.user_id}: {e}")
            raise BotError(f"Unexpected error while updating user: {str(e)}")
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