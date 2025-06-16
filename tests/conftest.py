import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from main import create_app
from extensions import db
from models.user import User
from utils.translation_system import TranslationSystem
from models import Teacher, TeacherExercise

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    app = create_app('testing')
    return app

@pytest.fixture(scope='session')
def app_context(app):
    """Provide the app context for the test session."""
    with app.app_context():
        yield

@pytest.fixture(scope='session')
def client(app, app_context):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='session', autouse=True)
def build_db(app_context):
    """Build the database."""
    db.create_all()
    yield
    db.drop_all()

@pytest.fixture(scope='function', autouse=True)
def session(app_context):
    """Creates a new database session for a test and rolls back changes."""
    connection = db.engine.connect()
    transaction = connection.begin()

    # Use the existing db.session which is a scoped_session
    yield db.session

    db.session.remove()
    transaction.rollback()
    connection.close()

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
    session.flush()  # Persist user within the transaction without committing
    return user

@pytest.fixture(scope="session", autouse=True)
def _translations():
    """Load translations once for the entire test session."""
    TranslationSystem.load_translations()

@pytest.fixture
def mock_update():
    """Create a mock Telegram update object."""
    update = MagicMock()
    
    # Mock user
    user_mock = MagicMock()
    user_mock.id = 12345
    user_mock.first_name = "Test"
    user_mock.last_name = "User"
    user_mock.username = "testuser"
    user_mock.language_code = "en"
    user_mock.to_dict.return_value = {
        'id': user_mock.id,
        'first_name': user_mock.first_name,
        'last_name': user_mock.last_name,
        'username': user_mock.username,
        'language_code': user_mock.language_code,
    }
    
    # Mock message
    message_mock = AsyncMock() # Use AsyncMock for message and reply_text
    
    # Mock callback_query
    callback_query_mock = AsyncMock()
    
    update.effective_user = user_mock
    update.message = message_mock
    update.callback_query = callback_query_mock
    update.callback_query.from_user = user_mock # Callback queries also have a user
    
    return update

@pytest.fixture
def mock_context():
    """Create a mock Telegram context object."""
    context = MagicMock()
    context.args = []
    return context

@pytest.fixture
def mock_openai_service():
    """Mock the OpenAIService."""
    with patch('services.openai_service.OpenAIService') as mock:
        instance = mock.return_value
        instance.generate_explanation.return_value = "This is a mock explanation."
        instance.generate_definition.return_value = "This is a mock definition."
        yield mock 

@pytest.fixture
def regular_user(session):
    """Fixture for a regular user who is not an admin."""
    user = User(user_id=111, first_name="Regular", last_name="User", username="regularuser")
    session.add(user)
    session.flush()
    return user

@pytest.fixture
def non_approved_teacher_user(session):
    """Fixture for a user who is an admin but not an approved teacher."""
    user = User(user_id=222, first_name="Admin", last_name="User", username="adminuser", is_admin=True)
    teacher_profile = Teacher(user_id=user.id, is_approved=False)
    user.teacher_profile = teacher_profile
    session.add(user)
    session.flush()
    return user

@pytest.fixture
def approved_teacher_user(session):
    """Fixture for a user who is an admin and an approved teacher."""
    user = User(user_id=333, first_name="Approved", last_name="Teacher", username="approvedteacher", is_admin=True)
    teacher_profile = Teacher(user_id=user.id, is_approved=True)
    user.teacher_profile = teacher_profile
    session.add(user)
    session.flush()
    return user

@pytest.fixture
def approved_teacher_with_exercises(session, approved_teacher_user):
    """Fixture for an approved teacher with some exercises."""
    ex1 = TeacherExercise(creator_id=approved_teacher_user.id, title="Grammar Test 1", exercise_type="grammar", content={}, difficulty="easy", is_published=True)
    ex2 = TeacherExercise(creator_id=approved_teacher_user.id, title="Vocabulary Quiz", exercise_type="vocabulary", content={}, difficulty="medium", is_published=False)
    session.add_all([ex1, ex2])
    session.flush()
    return approved_teacher_user 