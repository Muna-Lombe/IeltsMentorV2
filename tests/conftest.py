import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app as flask_app  # Import the Flask app instance
from models.user import Base, User

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def app():
    """Create a Flask app instance for the tests."""
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL,
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for tests
    })
    return flask_app

@pytest.fixture(scope="session")
def engine():
    """Create a database engine for the tests."""
    return create_engine(TEST_DATABASE_URL)

@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(engine, tables):
    """Create a new database session for each test."""
    connection = engine.connect()
    # begin a non-ORM transaction
    transaction = connection.begin()
    # bind an individual session to the connection
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    # rollback - everything that happened with the
    # session above (including calls to commit())
    # is rolled back.
    transaction.rollback()
    connection.close()

@pytest.fixture
def sample_user(db_session):
    """Create a sample user and add it to the test database."""
    user = User(
        user_id=123456789,
        first_name="Test",
        last_name="User",
        username="testuser",
        preferred_language="en"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def mock_update():
    """Create a mock Telegram update object."""
    from unittest.mock import MagicMock, AsyncMock
    
    update = MagicMock(spec=AsyncMock)
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"
    update.effective_user.username = "testuser"
    update.effective_user.language_code = "en"
    update.effective_user.to_dict.return_value = {
        'id': 12345,
        'first_name': 'Test',
        'last_name': 'User',
        'username': 'testuser',
        'language_code': 'en'
    }
    
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    
    return update

@pytest.fixture
def mock_context():
    """Create a mock Telegram context object."""
    from unittest.mock import MagicMock
    return MagicMock() 