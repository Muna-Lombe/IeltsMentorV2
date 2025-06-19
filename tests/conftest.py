import sys
import os

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from telegram import Update, User as TelegramUser

from app import create_app
from extensions import db
from models.user import User
from models.practice_session import PracticeSession
from models import Teacher, TeacherExercise, Group
from utils.translation_system import TranslationSystem
from services.auth_service import AuthService

# This engine will be used for the entire test session
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    app = create_app('testing')
    app.config.update({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", 'SQLALCHEMY_TRACK_MODIFICATIONS': False, 'WTF_CSRF_ENABLED': False})
    
    with app.app_context():
        # Bind the app's db metadata to the test engine
        db.metadata.create_all(bind=engine)

    yield app

    with app.app_context():
        db.metadata.drop_all(bind=engine)


@pytest.fixture(scope='function')
def session(app):
    """
    Creates a new database session for each test, managed by a transaction.
    The transaction is rolled back after each test, ensuring test isolation.
    """
    with app.app_context():
        # Create all tables for each test function
        db.create_all()

        connection = db.engine.connect()
        transaction = connection.begin()
        
        # The session is bound to the connection, ensuring it participates in the transaction
        db_session = TestingSessionLocal(bind=connection)

        yield db_session

        # Rollback the transaction and close the connection
        db_session.close()
        transaction.rollback()
        connection.close()

        # Drop all tables to ensure a clean state for the next test
        db.drop_all()

# --- Mock Fixtures ---

@pytest.fixture
def mock_update():
    """Creates a generic mock for the telegram.Update object."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"
    update.effective_user.username = "testuser"
    update.effective_user.language_code = 'en'
    
    update.effective_chat = MagicMock()
    update.message = MagicMock()
    update.callback_query = MagicMock()
    
    # Make mocks awaitable
    update.message.reply_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    
    # Configure from_user on callback_query
    update.callback_query.from_user = update.effective_user
    
    return update

@pytest.fixture
def mock_context():
    """Create mock Telegram context object."""
    mock_context = MagicMock()
    mock_context.bot = AsyncMock()
    mock_context.user_data = {}
    
    return mock_context

class MockUser:
    def __init__(self, id, first_name="Test", last_name="User", username="testuser", preferred_language="en"):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.preferred_language = preferred_language
        self.is_admin = False
        # Add a mock 'stats' attribute to align with the User model
        self.stats = {'reading': {'correct': 0, 'total': 0}, 'writing': {'tasks_submitted': 0, 'avg_score': 0}}
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
            'language_code': self.preferred_language
        }

class MockMessage:
    def __init__(self, text, from_user=None):
        self.text = text
        self.from_user = from_user or MockUser(id=123)
        self.chat_id = 12345
        self.reply_text = AsyncMock()
        self.delete = AsyncMock()
        self.edit_text = AsyncMock()

class MockCallbackQuery:
    def __init__(self, data, from_user=None, message=None):
        self.data = data
        self.from_user = from_user or MockUser(id=123)
        self.message = message or MockMessage(text="Original message")
        self.answer = AsyncMock()
        self.edit_message_text = AsyncMock()

# --- Data Fixtures ---

@pytest.fixture(scope='function')
def sample_user(session):
    """Create a sample user in the database for a single test."""
    user = User(
        user_id=12345,
        first_name="Test",
        last_name="User",
        username="testuser",
        preferred_language="en",
        stats={'reading': {'correct': 5, 'total': 10}}
    )
    session.add(user)
    session.flush()
    return user
    
@pytest.fixture(scope='function')
def regular_user(session):
    """Create a second sample user for testing interactions."""
    user = User(
        user_id=999,
        first_name="Regular",
        last_name="User",
        username="regularuser"
    )
    session.add(user)
    session.flush()
    session.commit()
    return user

@pytest.fixture(scope='function')
def approved_teacher_user(session):
    """Create a sample teacher user who is approved."""
    user = User(user_id=789, first_name="Approved", last_name="Teacher", username="approvedteacher", is_admin=True)
    session.add(user)
    session.flush()

    teacher = Teacher(user_id=user.id, is_approved=True)
    session.add(teacher)
    session.flush()
    return user

@pytest.fixture(scope='function')
def non_approved_teacher_user(session):
    """Create a sample teacher user who is not yet approved."""
    user = User(user_id=888, first_name="Unapproved", last_name="Teacher", username="unapprovedteacher", is_admin=True)
    session.add(user)
    session.flush()

    teacher = Teacher(user_id=user.id, is_approved=False)
    session.add(teacher)
    session.flush()
    return user

@pytest.fixture(scope='function')
def approved_teacher_with_exercises(session, approved_teacher_user):
    """A teacher with some exercises already created."""
    exercise1 = TeacherExercise(creator_id=approved_teacher_user.id, title="Test Exercise 1", exercise_type="reading", difficulty="medium", content={"q": "1"})
    exercise2 = TeacherExercise(creator_id=approved_teacher_user.id, title="Test Exercise 2", exercise_type="writing", difficulty="hard", content={"q": "2"})
    session.add_all([exercise1, exercise2])
    session.flush()
    return approved_teacher_user

@pytest.fixture
def mock_openai_service():
    """Mocks the OpenAIService to prevent actual API calls."""
    with patch('handlers.ai_commands_handler.OpenAIService') as mock_service_class:
        mock_instance = mock_service_class.return_value
        mock_instance.generate_explanation.return_value = "This is a mock explanation."
        mock_instance.generate_definition.return_value = "This is a mock definition."
        yield mock_service_class

@pytest.fixture
def mock_reading_data():
    """Mocks the function that loads reading practice data."""
    with patch('handlers.practice_handler.load_reading_data') as mock_load:
        mock_load.return_value = {
            "passages": [{
                "id": "rs1",
                "passage": "This is a test passage.",
                "questions": [{
                    "question_id": "rs1_q1",
                    "question_text": "What is this?",
                    "options": ["A test", "A real thing", "Not sure"],
                    "correct_option_index": 0
                }]
            }]
        }
        yield mock_load

@pytest.fixture(scope="session", autouse=True)
def _translations():
    """Load translations once for the entire test session."""
    TranslationSystem.load_translations()

# @pytest.fixture
# def sample_teacher(session, approved_teacher_user):
#     """Create a sample teacher for testing."""
#     teacher = Teacher(user_id=approved_teacher_user.id, is_approved=True)
#     session.add(teacher)
#     session.flush()
#     return teacher

@pytest.fixture
def sample_teacher_with_group(session, approved_teacher_user):
    """Create a sample teacher with a group for testing."""
    group = Group(
        name="Test Group",
        description="A group for testing",
        teacher_id=approved_teacher_user.id
    )
    session.add(group)
    session.commit()
    # Refresh the teacher object to load the new group relationship
    session.refresh(approved_teacher_user)
    print(f"approved_teacher_user: {approved_teacher_user.teacher_profile}")
    print(f"approved_teacher_user.teacher_profile.groups: {approved_teacher_user.teacher_profile.groups}")
    return approved_teacher_user

@pytest.fixture
def sample_teacher_with_group_and_exercise(session, sample_teacher_with_group):
    """Create a teacher with a group and a published exercise."""
    exercise = TeacherExercise(
        title="Test Exercise",
        description="An exercise for testing homework.",
        exercise_type="reading",
        content={"question": "What is the main idea?"},
        difficulty="medium",
        creator_id=sample_teacher_with_group.teacher_profile.id,
        is_published=True
    )
    session.add(exercise)
    session.commit()
    session.refresh(sample_teacher_with_group)
    return sample_teacher_with_group

@pytest.fixture
def sample_exercise(db_session, sample_teacher):
    """Create a sample published exercise for testing."""
    # Implementation of this fixture is not provided in the original file or the new code block
    # This fixture is assumed to exist as it's called in the new code block
    pass

@pytest.fixture
def botmaster_user(session):
    """Create a botmaster user for testing."""
    user = User(
        user_id=111,
        first_name="Bot",
        last_name="Master",
        username="botmaster",
        is_botmaster=True
    )
    session.add(user)
    session.commit()
    return user

@pytest.fixture
def pending_teacher_user(session):
    """Create a user who has a teacher profile but is not yet approved."""
    user = User(
        user_id=222,
        first_name="Pending",
        last_name="Teacher",
        username="pendingteacher"
    )
    session.add(user)
    session.flush()

    teacher = Teacher(
        user_id=user.id,
        is_approved=False
    )
    session.add(teacher)
    session.commit()
    return user

@pytest.fixture
def sample_teacher(db_session):
    """Create a sample teacher for testing."""
    user = User(
        user_id=777,
        first_name="Approved",
        last_name="Teacher",
        username="approvedteacher",
        is_admin=True
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope="function")
def another_teacher_user(session):
    """Create a second approved teacher for auth tests."""
    user = User(
        user_id=777,
        first_name="Another",
        last_name="Teacher",
        username="anotherteacher"
    )
    session.add(user)
    session.flush() # Ensure user.id is available

    teacher = Teacher(
        user_id=user.id,
        api_token=AuthService.generate_api_token(),
        is_approved=True
    )
    session.add(teacher)
    session.commit()
    
    yield user
    
    # Teardown: clean up the created objects
    session.delete(teacher)
    session.delete(user)
    session.commit()