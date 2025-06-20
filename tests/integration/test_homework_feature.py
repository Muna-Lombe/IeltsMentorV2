import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.ext import ConversationHandler

from handlers.teacher_handler import (
    assign_homework_start,
    select_group_for_homework,
    select_exercise_for_homework,
    cancel_homework_assignment,
    SELECTING_GROUP,
    SELECTING_EXERCISE,
)
from models import User, Teacher, Group, TeacherExercise, Homework


@pytest.mark.asyncio
async def test_assign_homework_start_with_groups(
    mock_update: MagicMock, mock_context: MagicMock, sample_teacher_with_group: User
):
    """Test that the assign_homework conversation starts correctly when a teacher has groups."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = sample_teacher_with_group.user_id

    # The decorator will fetch the user, so we don't pass it in.
    result = await assign_homework_start(mock_update, mock_context)

    assert result == SELECTING_GROUP
    mock_update.message.reply_text.assert_called_once()
    assert "select a group" in mock_update.message.reply_text.call_args[1]['text'].lower()


@pytest.mark.asyncio
async def test_assign_homework_start_no_groups(
    mock_update: MagicMock, mock_context: MagicMock, approved_teacher_user: User
):
    """Test that the assign_homework conversation ends if the teacher has no groups."""
    mock_update.message.reply_text = AsyncMock()
    mock_update.effective_user.id = approved_teacher_user.user_id

    # The decorator will fetch the user.
    result = await assign_homework_start(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once()
    assert "you have not created any groups" in mock_update.message.reply_text.call_args[1]['text'].lower()


@pytest.mark.asyncio
async def test_select_group_for_homework_with_exercises(
    mock_update: MagicMock, mock_context: MagicMock, sample_teacher_with_group_and_exercise: User
):
    """Test selecting a group and seeing a list of exercises."""
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()
    
    group = sample_teacher_with_group_and_exercise.teacher_profile.groups[0]
    mock_update.callback_query.data = f"hw_group_{group.id}"
    mock_update.callback_query.from_user.id = sample_teacher_with_group_and_exercise.user_id

    result = await select_group_for_homework(mock_update, mock_context)

    assert result == SELECTING_EXERCISE
    mock_update.callback_query.edit_message_text.assert_called_once()
    assert "select an exercise" in mock_update.callback_query.edit_message_text.call_args[1]['text'].lower()


@pytest.mark.asyncio
async def test_select_exercise_and_create_homework(
    mock_update: MagicMock, mock_context: MagicMock, session: MagicMock, sample_teacher_with_group_and_exercise: User
):
    """Test selecting an exercise and successfully creating the homework assignment."""
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()
    
    teacher = sample_teacher_with_group_and_exercise.teacher_profile
    group = teacher.groups[0]
    exercise = teacher.created_exercises[0]

    mock_update.callback_query.data = f"hw_ex_{exercise.id}"
    mock_update.callback_query.from_user.id = sample_teacher_with_group_and_exercise.user_id
    mock_context.user_data = {'homework_group_id': group.id}

    result = await select_exercise_for_homework(mock_update, mock_context)

    assert result == ConversationHandler.END
    homework = session.query(Homework).filter_by(group_id=group.id, exercise_id=exercise.id).first()
    assert homework is not None
    mock_update.callback_query.edit_message_text.assert_called_once()
    assert "homework assigned successfully" in mock_update.callback_query.edit_message_text.call_args[1]['text'].lower()

@pytest.mark.asyncio
async def test_cancel_homework_assignment(
    mock_update: MagicMock, mock_context: MagicMock, approved_teacher_user: User
):
    """Test that the homework assignment can be cancelled."""
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()
    mock_update.callback_query.from_user.id = approved_teacher_user.user_id
    mock_context.user_data = {'homework_group_id': 1}
    
    result = await cancel_homework_assignment(mock_update, mock_context)

    assert result == ConversationHandler.END
    assert "homework_group_id" not in mock_context.user_data
    assert "assignment has been cancelled" in mock_update.callback_query.edit_message_text.call_args[1]['text'].lower() 