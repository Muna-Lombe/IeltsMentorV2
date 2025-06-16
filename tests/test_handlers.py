import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from telegram import InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Handlers to test
from handlers.core_handlers import start, stats_command, unknown_command
from handlers.practice_handler import (
    practice_command,
    practice_section_callback,
    PRACTICE_CALLBACK_READING,
)
from handlers.ai_commands_handler import explain_command, define_command
from handlers.teacher_handler import (
    create_group_start,
    get_group_name,
    get_group_description,
    cancel_group_creation,
    GET_GROUP_NAME,
    GET_GROUP_DESCRIPTION
)
from handlers.exercise_management_handler import (
    my_exercises_command,
    create_exercise_start,
    get_title,
    get_description,
    get_type,
    get_difficulty,
    get_content,
    cancel_exercise_creation,
    GET_TITLE,
    GET_DESCRIPTION,
    GET_TYPE,
    GET_DIFFICULTY,
    GET_CONTENT,
)

# Models and Services
from models.user import User
from utils.translation_system import TranslationSystem
from models import PracticeSession, Group, TeacherExercise

@pytest.mark.asyncio
async def test_start_new_user(session, mock_update, mock_context):
    """Test the /start command for a new user."""
    # The user_id from mock_update (12345) does not exist yet.
    await start(mock_update, mock_context)
    
    # Verify a new user was created
    new_user = session.query(User).filter_by(user_id=12345).first()
    assert new_user is not None
    assert new_user.first_name == "Test"
    
    # Verify the welcome message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "Welcome to the IELTS Mentor Bot" in call_args.kwargs['text']

@pytest.mark.asyncio
async def test_start_existing_user(sample_user, mock_update, mock_context, session):
    """Test the /start command for an existing user."""
    # sample_user fixture provides a user with user_id=12345
    await start(mock_update, mock_context)
    
    # Verify the welcome back message was sent
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "Welcome back" in call_args.kwargs['text']

@pytest.mark.asyncio
async def test_stats_command_with_stats(sample_user, mock_update, mock_context):
    """Test the /stats command for a user with existing stats."""
    await stats_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "Here are your current stats" in call_args.kwargs['text']
    assert "_Reading_: *5*/*10*" in call_args.kwargs['text']

@pytest.mark.asyncio
async def test_stats_command_no_stats(session, mock_update, mock_context):
    """Test the /stats command for a new user with default 0 stats."""
    # Create a user who will have the default stats from the model
    user = User(user_id=54321, first_name="Newbie")
    mock_update.effective_user.id = 54321 # Ensure the update matches this user
    session.add(user)
    session.flush()

    await stats_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "You don't have any stats yet" in call_args.kwargs['text']

@pytest.mark.asyncio
async def test_practice_command(mock_update, mock_context):
    """Test the /practice command sends the selection keyboard."""
    await practice_command(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "Please select a section to practice" in call_args.kwargs['text']
    assert isinstance(call_args.kwargs["reply_markup"], InlineKeyboardMarkup)

@pytest.mark.asyncio
async def test_practice_section_callback(sample_user, mock_update, mock_context):
    """Test the practice section callback."""
    # Simulate the callback query
    mock_update.callback_query.data = PRACTICE_CALLBACK_READING
    await practice_section_callback(mock_update, mock_context)

    # Verify the message was edited
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args
    assert "Practice sessions for Reading are still under development" in call_args.kwargs["text"]

@pytest.mark.asyncio
@patch("handlers.ai_commands_handler.OpenAIService")
async def test_explain_command(mock_openai_service_class, mock_update, mock_context):
    """Test the /explain command with a mocked AI service."""
    mock_service_instance = mock_openai_service_class.return_value
    mock_service_instance.generate_explanation.return_value = "This is a mock explanation."

    mock_context.args = ["grammar", "present", "perfect"]
    await explain_command(mock_update, mock_context)

    # Check that the processing message was sent and then edited
    mock_update.message.reply_text.assert_called_once_with("🤔 Thinking... Please wait a moment.")
    mock_update.message.reply_text.return_value.edit_text.assert_called_once_with(
        "🔍 Here's an explanation for *present perfect*:\n\nThis is a mock explanation."
    )
    mock_service_instance.generate_explanation.assert_called_once_with(
        query="present perfect", context="grammar", language="en"
    )

@pytest.mark.asyncio
@patch("handlers.ai_commands_handler.OpenAIService")
async def test_define_command(mock_openai_service_class, mock_update, mock_context):
    """Test the /define command with a mocked AI service."""
    mock_service_instance = mock_openai_service_class.return_value
    mock_service_instance.generate_definition.return_value = "This is a mock definition."

    mock_context.args = ["elaborate"]
    await define_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with("🤔 Thinking... Please wait a moment.")
    mock_update.message.reply_text.return_value.edit_text.assert_called_once_with(
        "📖 Here's the definition for *elaborate*:\n\nThis is a mock definition."
    )
    mock_service_instance.generate_definition.assert_called_once_with(
        word="elaborate", language="en"
    )

@pytest.mark.asyncio
async def test_unknown_command(mock_update, mock_context):
    """Test the unknown command handler."""
    await unknown_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "Sorry, I didn't understand that command" in call_args.kwargs['text']

# Tests for Teacher Handlers and Decorators
@pytest.mark.asyncio
async def test_create_group_command_as_approved_teacher(mock_update, mock_context, approved_teacher_user):
    """Test that an approved teacher can start the create group conversation."""
    # This test now checks the entry point of the conversation
    mock_update.effective_user.id = approved_teacher_user.user_id

    # The decorator handles passing the user, so we don't pass it here.
    result_state = await create_group_start(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    # The actual text is now in the 'text' keyword argument
    assert "To create a group, please reply with the group name." in mock_update.message.reply_text.call_args.kwargs['text']
    assert result_state == GET_GROUP_NAME

@pytest.mark.asyncio
async def test_create_group_command_as_non_approved_teacher(mock_update, mock_context, non_approved_teacher_user):
    """Test that a non-approved teacher is denied access."""
    mock_update.effective_user.id = non_approved_teacher_user.user_id
    
    result = await create_group_start(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "This command is only available to approved teachers" in mock_update.message.reply_text.call_args.kwargs['text']
    assert result == ConversationHandler.END # Decorator should stop the handler

@pytest.mark.asyncio
async def test_create_group_command_as_regular_user(mock_update, mock_context, regular_user):
    """Test that a regular user is denied access."""
    mock_update.effective_user.id = regular_user.user_id
    
    result = await create_group_start(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "This command is only available to approved teachers" in mock_update.message.reply_text.call_args.kwargs['text']
    assert result == ConversationHandler.END # Decorator should stop the handler

@pytest.mark.asyncio
async def test_create_group_command_as_unknown_user(mock_update, mock_context):
    """Test that a user not in the database is denied access."""
    mock_update.effective_user.id = 999999  # An ID that doesn't exist
    
    result = await create_group_start(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "Could not find your user profile" in mock_update.message.reply_text.call_args.kwargs['text']
    assert result == ConversationHandler.END # Decorator should stop the handler

@pytest.mark.asyncio
async def test_get_group_name_handler(mock_update, mock_context, approved_teacher_user):
    """Test the handler for receiving the group name."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    mock_update.message.text = "My New Awesome Group"
    mock_context.user_data = {} # Simulate clean user_data
    
    result_state = await get_group_name(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "please provide a short description" in mock_update.message.reply_text.call_args.kwargs['text']
    assert mock_context.user_data['group_name'] == "My New Awesome Group"
    assert result_state == GET_GROUP_DESCRIPTION

@pytest.mark.asyncio
async def test_get_group_description_handler(session, mock_update, mock_context, approved_teacher_user):
    """Test the handler for receiving the description and creating the group."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    mock_update.message.text = "A group for practicing advanced writing."
    mock_context.user_data = {'group_name': 'Advanced Writers'}

    result_state = await get_group_description(mock_update, mock_context)
    
    # Check that the success message was sent
    mock_update.message.reply_text.assert_called_once()
    assert "Group 'Advanced Writers' has been created successfully!" in mock_update.message.reply_text.call_args.kwargs['text']
    
    # Check that the group was actually created in the DB
    new_group = session.query(Group).filter_by(name='Advanced Writers').first()
    assert new_group is not None
    assert new_group.teacher_id == approved_teacher_user.id
    assert new_group.description == "A group for practicing advanced writing."
    
    # Check that state was cleaned up and conversation ended
    assert 'group_name' not in mock_context.user_data
    assert result_state == ConversationHandler.END

@pytest.mark.asyncio
async def test_cancel_group_creation_handler(mock_update, mock_context, approved_teacher_user):
    """Test the cancellation of the group creation flow."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    mock_context.user_data = {'group_name': 'A Group To Be Cancelled'}

    result_state = await cancel_group_creation(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(text="Group creation has been cancelled.")
    assert 'group_name' not in mock_context.user_data
    assert result_state == ConversationHandler.END 

@pytest.mark.asyncio
async def test_my_exercises_command_with_exercises(mock_update, mock_context, approved_teacher_with_exercises):
    """Test the /my_exercises command for a teacher who has created exercises."""
    mock_update.effective_user.id = approved_teacher_with_exercises.user_id

    await my_exercises_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    response_text = mock_update.message.reply_text.call_args.kwargs['text']
    
    assert "Here are your created exercises:" in response_text
    assert "Grammar Test 1" in response_text
    assert "Vocabulary Quiz" in response_text
    assert "Published" in response_text
    assert "Draft" in response_text

@pytest.mark.asyncio
async def test_my_exercises_command_no_exercises(mock_update, mock_context, approved_teacher_user):
    """Test the /my_exercises command for a teacher with no exercises."""
    mock_update.effective_user.id = approved_teacher_user.user_id

    await my_exercises_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    response_text = mock_update.message.reply_text.call_args.kwargs['text']

    assert "You have not created any exercises yet" in response_text

# Tests for /create_exercise ConversationHandler
@pytest.mark.asyncio
async def test_create_exercise_start_command(mock_update, mock_context, approved_teacher_user):
    """Test the start of the /create_exercise conversation."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    
    result = await create_exercise_start(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "First, what is the title" in mock_update.message.reply_text.call_args.kwargs['text']
    assert result == GET_TITLE

@pytest.mark.asyncio
async def test_create_exercise_get_title(mock_update, mock_context, approved_teacher_user):
    """Test the get_title step of the conversation."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    mock_update.message.text = "My First Exercise"
    mock_context.user_data = {}
    
    result = await get_title(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "provide a short description" in mock_update.message.reply_text.call_args.kwargs['text']
    assert mock_context.user_data['title'] == "My First Exercise"
    assert result == GET_DESCRIPTION

@pytest.mark.asyncio
async def test_create_exercise_get_description(mock_update, mock_context, approved_teacher_user):
    """Test the get_description step of the conversation."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    mock_update.message.text = "A simple exercise."
    mock_context.user_data = {"title": "My First Exercise"}

    result = await get_description(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "select the exercise type" in mock_update.message.reply_text.call_args.kwargs['text']
    assert isinstance(mock_update.message.reply_text.call_args.kwargs['reply_markup'], InlineKeyboardMarkup)
    assert mock_context.user_data['description'] == "A simple exercise."
    assert result == GET_TYPE

@pytest.mark.asyncio
async def test_create_exercise_get_type(mock_update, mock_context, approved_teacher_user):
    """Test the get_type step of the conversation."""
    mock_context.user_data = {"title": "My First Exercise", "description": "A simple exercise."}
    
    # Simulate a callback query
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "type_grammar"
    mock_update.callback_query.from_user.id = approved_teacher_user.user_id
    
    result = await get_type(mock_update, mock_context)
    
    mock_update.callback_query.answer.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()
    assert "difficulty level" in mock_update.callback_query.edit_message_text.call_args.kwargs['text']
    assert mock_context.user_data['type'] == "grammar"
    assert result == GET_DIFFICULTY

@pytest.mark.asyncio
async def test_create_exercise_get_difficulty(mock_update, mock_context, approved_teacher_user):
    """Test the get_difficulty step of the conversation."""
    mock_context.user_data = {"title": "My First Exercise", "description": "A simple exercise.", "type": "grammar"}

    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.data = "difficulty_intermediate"
    mock_update.callback_query.from_user.id = approved_teacher_user.user_id

    result = await get_difficulty(mock_update, mock_context)

    mock_update.callback_query.answer.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()
    assert "provide the exercise content" in mock_update.callback_query.edit_message_text.call_args.kwargs['text']
    assert mock_context.user_data['difficulty'] == "intermediate"
    assert result == GET_CONTENT

@pytest.mark.asyncio
async def test_create_exercise_get_content_and_create(session, mock_update, mock_context, approved_teacher_user):
    """Test the final step of creating the exercise with valid content."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    mock_update.message.text = '{"questions": [{"text": "This is a valid question."}]}'
    mock_context.user_data = {
        "title": "My First Exercise", 
        "description": "A simple exercise.", 
        "type": "grammar", 
        "difficulty": "intermediate"
    }

    result = await get_content(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "Exercise created successfully" in mock_update.message.reply_text.call_args.kwargs['text']
    
    # Verify in DB
    exercise = session.query(TeacherExercise).filter_by(title="My First Exercise").first()
    assert exercise is not None
    assert exercise.creator_id == approved_teacher_user.id
    assert exercise.content['questions'][0]['text'] == "This is a valid question."
    
    assert result == ConversationHandler.END
    assert not mock_context.user_data # user_data should be cleared

@pytest.mark.asyncio
async def test_create_exercise_get_content_invalid(mock_update, mock_context, approved_teacher_user):
    """Test providing invalid content for an exercise."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    mock_update.message.text = "This is not valid JSON."
    mock_context.user_data = {
        "title": "My First Exercise", 
        "description": "A simple exercise.", 
        "type": "grammar", 
        "difficulty": "intermediate"
    }
    
    result = await get_content(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    assert "The content format is invalid" in mock_update.message.reply_text.call_args.kwargs['text']
    assert result == GET_CONTENT # Should stay in the same state

@pytest.mark.asyncio
async def test_create_exercise_cancel(mock_update, mock_context, approved_teacher_user):
    """Test the cancellation of the /create_exercise conversation."""
    mock_update.effective_user.id = approved_teacher_user.user_id
    mock_context.user_data = {"title": "An exercise to be cancelled"}

    result = await cancel_exercise_creation(mock_update, mock_context)
    
    mock_update.message.reply_text.assert_called_once()
    assert "Exercise creation has been cancelled" in mock_update.message.reply_text.call_args.kwargs['text']
    assert not mock_context.user_data
    assert result == ConversationHandler.END 