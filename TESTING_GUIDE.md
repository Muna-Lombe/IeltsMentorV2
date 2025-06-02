# IELTS Preparation Bot - Testing Guide

## Testing Framework Overview

The IELTS Preparation Bot uses a comprehensive testing strategy covering unit tests, integration tests, and end-to-end testing to ensure reliability and functionality across all components.

## Test Structure

### Directory Organization
```
tests/
├── unit/
│   ├── test_models.py           # Database model tests
│   ├── test_handlers.py         # Bot handler tests
│   ├── test_services.py         # Service layer tests
│   └── test_utils.py            # Utility function tests
├── integration/
│   ├── test_database.py         # Database integration tests
│   ├── test_telegram_api.py     # Telegram API integration
│   ├── test_openai_integration.py # OpenAI API integration
│   └── test_web_interface.py    # Web interface tests
├── e2e/
│   ├── test_user_workflows.py   # Complete user journey tests
│   └── test_teacher_workflows.py # Teacher workflow tests
├── fixtures/
│   ├── sample_data.py           # Test data fixtures
│   └── mock_responses.py        # API response mocks
└── conftest.py                  # Pytest configuration
```

## Unit Testing

### Model Testing
```python
# test_models.py
import pytest
from models import User, TeacherExercise, Group
from datetime import datetime

class TestUserModel:
    def test_user_creation(self, db_session):
        """Test basic user creation and validation"""
        user = User(
            user_id=123456789,
            first_name="Test",
            last_name="User",
            username="testuser"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.joined_at is not None
        assert user.is_admin is False
        assert user.is_botmaster is False

    def test_user_stats_initialization(self, db_session):
        """Test that user stats are properly initialized"""
        user = User(user_id=123456789, first_name="Test")
        db_session.add(user)
        db_session.commit()
        
        stats = user.get_stats()
        assert 'vocabulary' in stats
        assert 'grammar' in stats
        assert stats['vocabulary']['correct'] == 0

    def test_user_language_detection(self, db_session):
        """Test automatic language detection for users"""
        user = User(user_id=123456789, first_name="Test")
        user.preferred_language = 'es'
        
        assert user.get_preferred_language() == 'es'

class TestTeacherExerciseModel:
    def test_exercise_creation(self, db_session, sample_teacher):
        """Test exercise creation with proper validation"""
        exercise = TeacherExercise(
            creator_id=sample_teacher.id,
            title="Test Exercise",
            description="A test exercise",
            exercise_type="vocabulary",
            content={"questions": [{"text": "Define 'elaborate'"}]},
            difficulty="medium"
        )
        db_session.add(exercise)
        db_session.commit()
        
        assert exercise.id is not None
        assert exercise.created_at is not None
        assert exercise.is_published is False

    def test_exercise_content_validation(self, db_session, sample_teacher):
        """Test that exercise content is properly validated"""
        exercise = TeacherExercise(
            creator_id=sample_teacher.id,
            title="Test Exercise",
            description="Test",
            exercise_type="vocabulary",
            content={"questions": [], "answers": []},
            difficulty="easy"
        )
        
        content = exercise.get_content()
        assert isinstance(content, dict)
        assert 'questions' in content
```

### Handler Testing
```python
# test_handlers.py
import pytest
from unittest.mock import Mock, patch
from telegram import Update, Message, User as TelegramUser
from handlers.practice_handler import practice_command

class TestPracticeHandler:
    def test_practice_command_authenticated_user(self, mock_update, mock_context):
        """Test practice command for authenticated users"""
        mock_update.effective_user.id = 123456789
        mock_update.message = Mock()
        
        with patch('handlers.practice_handler.User.query') as mock_query:
            mock_user = Mock()
            mock_user.is_admin = False
            mock_query.filter_by.return_value.first.return_value = mock_user
            
            practice_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()

    def test_practice_command_unauthenticated_user(self, mock_update, mock_context):
        """Test practice command for new users"""
        mock_update.effective_user.id = 999999999
        
        with patch('handlers.practice_handler.User.query') as mock_query:
            mock_query.filter_by.return_value.first.return_value = None
            
            practice_command(mock_update, mock_context)
            
            # Should trigger user registration
            assert mock_update.message.reply_text.called

class TestTranslationIntegration:
    def test_message_localization(self):
        """Test that messages are properly localized"""
        from utils.translation_system import get_message
        
        english_msg = get_message('practice', 'welcome', 'en')
        spanish_msg = get_message('practice', 'welcome', 'es')
        
        assert english_msg != spanish_msg
        assert isinstance(english_msg, str)
        assert len(english_msg) > 0

    def test_language_detection(self):
        """Test automatic language detection"""
        from utils.translation_system import detect_language
        
        user_data = {'language_code': 'es'}
        detected = detect_language(user_data)
        
        assert detected == 'es'
```

### Service Testing
```python
# test_services.py
import pytest
from unittest.mock import patch, Mock
from services.auth_service import AuthService
from services.openai_service import OpenAIService

class TestAuthService:
    def test_token_generation(self):
        """Test API token generation for teachers"""
        token = AuthService.generate_api_token()
        
        assert len(token) == 64
        assert token.isalnum()

    def test_token_validation(self, db_session, sample_teacher):
        """Test API token validation"""
        token = "valid_token_12345"
        sample_teacher.api_token = token
        db_session.commit()
        
        user = AuthService.validate_token(token)
        assert user is not None
        assert user.id == sample_teacher.user_id

class TestOpenAIService:
    @patch('services.openai_service.openai.chat.completions.create')
    def test_explanation_generation(self, mock_openai):
        """Test AI explanation generation"""
        mock_response = Mock()
        mock_response.choices[0].message.content = "Grammar explanation here"
        mock_openai.return_value = mock_response
        
        explanation = OpenAIService.generate_explanation("present perfect", "grammar")
        
        assert explanation == "Grammar explanation here"
        mock_openai.assert_called_once()

    @patch('services.openai_service.openai.chat.completions.create')
    def test_practice_question_generation(self, mock_openai):
        """Test practice question generation"""
        mock_response = Mock()
        mock_response.choices[0].message.content = '{"question": "Test question", "options": ["A", "B", "C", "D"], "answer": "A"}'
        mock_openai.return_value = mock_response
        
        question = OpenAIService.generate_practice_question("vocabulary", "medium")
        
        assert "question" in question
        assert "options" in question
        assert "answer" in question
```

## Integration Testing

### Database Integration
```python
# test_database.py
import pytest
from models import db, User, Group, TeacherExercise

class TestDatabaseIntegration:
    def test_user_group_relationship(self, db_session):
        """Test user-group relationships work correctly"""
        teacher = User(user_id=123, first_name="Teacher", is_admin=True)
        student = User(user_id=456, first_name="Student")
        group = Group(name="Test Group", teacher_id=teacher.id)
        
        db_session.add_all([teacher, student, group])
        db_session.commit()
        
        # Test relationships
        assert group.teacher_id == teacher.id
        assert len(teacher.groups_taught) == 1

    def test_exercise_homework_cascade(self, db_session, sample_teacher, sample_group):
        """Test that exercise deletion handles homework properly"""
        exercise = TeacherExercise(
            creator_id=sample_teacher.id,
            title="Test Exercise",
            description="Test",
            exercise_type="vocabulary",
            content={"questions": []}
        )
        db_session.add(exercise)
        db_session.commit()
        
        # Verify exercise exists
        assert TeacherExercise.query.filter_by(id=exercise.id).first() is not None

class TestTransactionHandling:
    def test_rollback_on_error(self, db_session):
        """Test that transactions rollback properly on errors"""
        initial_count = User.query.count()
        
        try:
            user1 = User(user_id=123, first_name="User1")
            user2 = User(user_id=123, first_name="User2")  # Duplicate user_id
            
            db_session.add(user1)
            db_session.add(user2)
            db_session.commit()
        except Exception:
            db_session.rollback()
        
        final_count = User.query.count()
        assert final_count == initial_count
```

### External API Testing
```python
# test_openai_integration.py
import pytest
from unittest.mock import patch
import requests

class TestOpenAIIntegration:
    def test_api_connectivity(self):
        """Test that OpenAI API is accessible"""
        # This test requires actual API key
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OpenAI API key not available")
        
        from services.openai_service import OpenAIService
        
        try:
            response = OpenAIService.test_connection()
            assert response is True
        except Exception as e:
            pytest.fail(f"OpenAI API connection failed: {e}")

    @patch('requests.post')
    def test_api_rate_limiting(self, mock_post):
        """Test that rate limiting is handled properly"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Rate limited")
        
        from services.openai_service import OpenAIService
        
        with pytest.raises(requests.exceptions.ConnectionError):
            OpenAIService.generate_explanation("test", "grammar")

# test_telegram_api.py
class TestTelegramIntegration:
    def test_webhook_setup(self):
        """Test that webhook can be set up properly"""
        if not os.getenv('TELEGRAM_BOT_TOKEN'):
            pytest.skip("Telegram bot token not available")
        
        from bot import setup_webhook
        
        result = setup_webhook("https://example.com/webhook")
        assert result is True

    def test_bot_info_retrieval(self):
        """Test that bot information can be retrieved"""
        if not os.getenv('TELEGRAM_BOT_TOKEN'):
            pytest.skip("Telegram bot token not available")
        
        from bot import get_bot_info
        
        info = get_bot_info()
        assert 'username' in info
        assert info['username'].endswith('bot')
```

## End-to-End Testing

### Complete User Workflows
```python
# test_user_workflows.py
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By

class TestStudentWorkflow:
    def test_complete_practice_session(self, telegram_bot_client):
        """Test complete practice session workflow"""
        # Start conversation
        response = telegram_bot_client.send_message("/start")
        assert "welcome" in response.text.lower()
        
        # Begin practice
        response = telegram_bot_client.send_message("/practice")
        assert "section" in response.text.lower()
        
        # Select speaking practice
        response = telegram_bot_client.click_button("speaking")
        assert "speaking" in response.text.lower()
        
        # Complete practice question
        response = telegram_bot_client.send_message("My answer here")
        assert "feedback" in response.text.lower() or "next" in response.text.lower()

    def test_explanation_request(self, telegram_bot_client):
        """Test AI explanation request workflow"""
        response = telegram_bot_client.send_message("/explain present perfect")
        
        # Should receive explanation
        assert len(response.text) > 50
        assert "present perfect" in response.text.lower()

class TestTeacherWorkflow:
    def test_group_creation_and_management(self, web_driver, teacher_credentials):
        """Test teacher group creation workflow"""
        # Login to web interface
        web_driver.get("http://localhost:5000/login")
        web_driver.find_element(By.NAME, "api_token").send_keys(teacher_credentials)
        web_driver.find_element(By.TYPE, "submit").click()
        
        # Create new group
        web_driver.get("http://localhost:5000/groups")
        web_driver.find_element(By.ID, "create-group-btn").click()
        
        web_driver.find_element(By.NAME, "group_name").send_keys("Test Group")
        web_driver.find_element(By.NAME, "description").send_keys("A test group")
        web_driver.find_element(By.TYPE, "submit").click()
        
        # Verify group creation
        assert "Test Group" in web_driver.page_source

    def test_exercise_creation_workflow(self, telegram_bot_client, teacher_user):
        """Test exercise creation through bot"""
        response = telegram_bot_client.send_message("/create_exercise")
        assert "title" in response.text.lower()
        
        # Provide exercise details
        response = telegram_bot_client.send_message("Vocabulary Test")
        response = telegram_bot_client.send_message("Test vocabulary knowledge")
        
        # Should complete exercise creation
        assert "created" in response.text.lower()
```

## Test Configuration

### Pytest Configuration
```python
# conftest.py
import pytest
import os
from models import db, User, Teacher, Group
from app import app

@pytest.fixture(scope="session")
def test_app():
    """Create test application instance"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def db_session(test_app):
    """Create database session for tests"""
    with test_app.app_context():
        db.session.begin()
        yield db.session
        db.session.rollback()

@pytest.fixture
def sample_user(db_session):
    """Create sample user for testing"""
    user = User(
        user_id=123456789,
        first_name="Test",
        last_name="User",
        username="testuser"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_teacher(db_session):
    """Create sample teacher for testing"""
    user = User(
        user_id=987654321,
        first_name="Test",
        last_name="Teacher",
        username="testteacher",
        is_admin=True
    )
    teacher = Teacher(
        user_id=user.id,
        api_token="test_token_12345",
        is_approved=True
    )
    db_session.add_all([user, teacher])
    db_session.commit()
    return teacher

@pytest.fixture
def mock_update():
    """Create mock Telegram update object"""
    from unittest.mock import Mock
    update = Mock()
    update.effective_user.id = 123456789
    update.message = Mock()
    return update

@pytest.fixture
def mock_context():
    """Create mock Telegram context object"""
    from unittest.mock import Mock
    return Mock()
```

## Performance Testing

### Load Testing
```python
# test_performance.py
import pytest
import time
import concurrent.futures
from models import User

class TestPerformance:
    def test_database_query_performance(self, db_session):
        """Test database query performance under load"""
        # Create test data
        users = [
            User(user_id=i, first_name=f"User{i}")
            for i in range(1000, 2000)
        ]
        db_session.add_all(users)
        db_session.commit()
        
        # Test query performance
        start_time = time.time()
        results = User.query.filter(User.user_id.between(1000, 1999)).all()
        end_time = time.time()
        
        assert len(results) == 1000
        assert (end_time - start_time) < 1.0  # Should complete within 1 second

    def test_concurrent_user_handling(self, test_app):
        """Test handling multiple concurrent users"""
        def simulate_user_request():
            with test_app.test_client() as client:
                response = client.post('/webhook', json={
                    'update_id': 1,
                    'message': {
                        'message_id': 1,
                        'from': {'id': 123, 'first_name': 'Test'},
                        'chat': {'id': 123, 'type': 'private'},
                        'text': '/start'
                    }
                })
                return response.status_code
        
        # Simulate 50 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(simulate_user_request) for _ in range(50)]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        assert all(status == 200 for status in results)
```

## Running Tests

### Local Test Execution
```bash
# Install testing dependencies
pip install pytest pytest-cov pytest-mock selenium

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run specific test file
pytest tests/unit/test_models.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_user"
```

### Continuous Integration
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
      run: |
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

This testing guide provides comprehensive coverage for ensuring the reliability and functionality of the IELTS Preparation Bot across all components and user workflows.