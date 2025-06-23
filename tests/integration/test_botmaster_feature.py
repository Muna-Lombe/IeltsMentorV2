import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.ext import ConversationHandler
from unittest.mock import patch

from handlers.botmaster_handler import (
    approve_teacher_start,
    patched_get_user_to_approve,
    cancel,
    SELECTING_USER,
    system_stats,
    manage_content_start,
    manage_content_action,
    SELECTING_CONTENT_ACTION,
)
from models import User, Teacher, TeacherExercise

@pytest.mark.asyncio
async def test_approve_teacher_start_as_botmaster(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User
):
    """Test that a botmaster can start the approve_teacher conversation."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = botmaster_user.user_id

    result = await approve_teacher_start(mock_update, mock_context)

    assert result == SELECTING_USER
    mock_update.message.reply_text.assert_called_once_with(
        text="Please enter the Telegram User ID or @username of the teacher you want to approve."
    )

@pytest.mark.asyncio
async def test_approve_teacher_start_as_non_botmaster(
    mock_update: MagicMock, mock_context: MagicMock, regular_user: User
):
    """Test that a non-botmaster cannot start the approve_teacher conversation."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = regular_user.user_id

    result = await approve_teacher_start(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once_with(
        text="Sorry, this command is restricted to Botmasters only."
    )

@pytest.mark.asyncio
async def test_approve_pending_teacher_success(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User, pending_teacher_user: User, session
):
    """Test successfully approving a teacher who is pending."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = botmaster_user.user_id
    mock_update.message.text = pending_teacher_user.username
    mock_context.user_data = {}

    assert pending_teacher_user.teacher_profile.is_approved is False

    # Inject the test session into the handler's context
    with patch('handlers.botmaster_handler.db.session', session):
        result = await patched_get_user_to_approve(mock_update, mock_context)

    assert result == ConversationHandler.END
    # Refresh the object to get the latest state from the database
    session.refresh(pending_teacher_user.teacher_profile)
    assert pending_teacher_user.teacher_profile.is_approved is True
    mock_update.message.reply_text.assert_called_once_with(
        text=f"✅ Success! Teacher {pending_teacher_user.username} has been approved."
    )

@pytest.mark.asyncio
async def test_approve_already_approved_teacher(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User, approved_teacher_user: User
):
    """Test trying to approve a teacher who is already approved."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = botmaster_user.user_id
    mock_update.message.text = str(approved_teacher_user.user_id)
    mock_context.user_data = {}

    result = await patched_get_user_to_approve(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once_with(
        text="This teacher has already been approved."
    )

@pytest.mark.asyncio
async def test_approve_non_teacher_applicant(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User, regular_user: User
):
    """Test trying to approve a user who has not applied to be a teacher."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = botmaster_user.user_id
    mock_update.message.text = regular_user.username
    mock_context.user_data = {}

    result = await patched_get_user_to_approve(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once_with(
        text="This user has not registered as a teacher and cannot be approved."
    )

@pytest.mark.asyncio
async def test_approve_user_not_found(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User
):
    """Test trying to approve a user that does not exist."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = botmaster_user.user_id
    mock_update.message.text = "nonexistentuser"
    mock_context.user_data = {}

    result = await patched_get_user_to_approve(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once_with(
        text="Sorry, I could not find a user with that ID or username."
    )

@pytest.mark.asyncio
async def test_cancel_approval_flow(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User
):
    """Test cancelling the teacher approval conversation."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = botmaster_user.user_id

    result = await cancel(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once_with(
        text="Action cancelled."
    )

@pytest.mark.asyncio
async def test_system_stats_as_botmaster(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User
):
    """Test that a botmaster can view system stats."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = botmaster_user.user_id

    # We don't need to patch the session here, as the decorator handles it.
    await system_stats(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_text = mock_update.message.reply_text.call_args[0][0]
    assert "System Statistics" in call_text
    assert "Total Users:" in call_text

@pytest.mark.asyncio
async def test_system_stats_as_non_botmaster(
    mock_update: MagicMock, mock_context: MagicMock, regular_user: User
):
    """Test that a non-botmaster cannot view system stats."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = regular_user.user_id

    await system_stats(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        text="Sorry, this command is restricted to Botmasters only."
    )

@pytest.mark.asyncio
async def test_manage_content_start_with_exercises(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User, approved_teacher_user: User, session
):
    """Test starting the content management flow when exercises exist."""
    # Create exercises for the teacher
    exercise1 = TeacherExercise(creator_id=approved_teacher_user.id, title="Test Exercise 1", exercise_type="reading", difficulty="medium", content={"q": "1"})
    exercise2 = TeacherExercise(creator_id=approved_teacher_user.id, title="Test Exercise 2", exercise_type="writing", difficulty="hard", content={"q": "2"})
    session.add_all([exercise1, exercise2])
    session.commit()

    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = botmaster_user.user_id

    result = await manage_content_start(mock_update, mock_context)
    
    assert result == SELECTING_CONTENT_ACTION
    mock_update.message.reply_text.assert_called_once()
    call_kwargs = mock_update.message.reply_text.call_args.kwargs
    assert "Select an exercise to manage" in call_kwargs['text']
    assert len(call_kwargs['reply_markup'].inline_keyboard) == 2

@pytest.mark.asyncio
async def test_manage_content_toggle_status(
    mock_update: MagicMock, mock_context: MagicMock, botmaster_user: User, approved_teacher_user: User, session
):
    """Test toggling the publication status of an exercise."""
    from models import TeacherExercise
    exercise = TeacherExercise(creator_id=approved_teacher_user.id, title="Toggle Test", is_published=False, exercise_type="reading", difficulty="medium", content={"q": "1"})
    session.add(exercise)
    session.commit()
    
    assert exercise.is_published is False
    
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()
    mock_update.callback_query.data = f"content_{exercise.id}"
    mock_update.effective_user.id = botmaster_user.user_id

    result = await manage_content_action(mock_update, mock_context)
    
    assert result == ConversationHandler.END
    session.refresh(exercise)
    assert exercise.is_published is True
    
    mock_update.callback_query.edit_message_text.assert_called_once()
    assert "Status for 'Toggle Test' has been updated to: **Published**" in mock_update.callback_query.edit_message_text.call_args.kwargs['text'] 