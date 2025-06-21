import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update
from telegram.ext import ConversationHandler

from handlers.writing_practice_handler import (
    start_writing_practice,
    handle_task_selection,
    handle_essay,
    SELECTING_TASK,
    AWAITING_ESSAY,
)
from models import User, PracticeSession


@pytest.mark.asyncio
async def test_start_writing_practice(session, mock_update, mock_context):
    """Test the start of the writing practice session."""
    user = User(user_id=mock_update.effective_user.id, preferred_language='en')
    session.add(user)
    session.commit()
    
    mock_update.callback_query.data = "practice_writing"
    
    result = await start_writing_practice(mock_update, mock_context)
    
    assert result == SELECTING_TASK
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args
    assert "Welcome to Writing Practice!" in call_args.kwargs['text']
    assert "Task 1: Report" in str(call_args.kwargs['reply_markup'])


@pytest.mark.asyncio
async def test_handle_task_selection(session, mock_update, mock_context):
    """Test the handling of a task selection."""
    user = User(user_id=mock_update.effective_user.id, preferred_language='en')
    session.add(user)
    session.commit()

    mock_update.callback_query.data = "wp_task_2"
    
    with patch('handlers.writing_practice_handler.OpenAIService') as mock_openai_service:
        mock_openai_service.return_value.generate_writing_task.return_value = {
            "task_type": 2,
            "question": "This is a test essay question.",
            "image_url": None
        }
        
        result = await handle_task_selection(mock_update, mock_context)
        
        assert result == AWAITING_ESSAY
        mock_update.callback_query.edit_message_text.assert_called_once_with(text="Generating your writing task, please wait...")
        mock_context.bot.send_message.assert_any_call(chat_id=mock_update.callback_query.message.chat_id, text="This is a test essay question.")
        assert "writing_session_id" in mock_context.user_data


@pytest.mark.asyncio
async def test_handle_essay(session, mock_update, mock_context):
    """Test the handling of a submitted essay."""
    # Step 1: Create and commit the user to get a valid ID
    user = User(user_id=mock_update.effective_user.id, preferred_language='en')
    session.add(user)
    session.commit()

    # Step 2: Now that user.id is not None, create the practice session
    practice_session = PracticeSession(user_id=user.id, section="writing_task_2", total_questions=1)
    session.add(practice_session)
    session.commit()

    mock_context.user_data = {"writing_session_id": practice_session.id, "writing_question": "Test question"}
    mock_update.message.text = "This is my essay."
    
    with patch('handlers.writing_practice_handler.db.session.query') as mock_query, \
         patch('handlers.writing_practice_handler.OpenAIService') as mock_openai_service, \
         patch('sqlalchemy.orm.attributes.flag_modified'):
        
        # Make the mock query return our mock session and user
        mock_query.return_value.filter_by.return_value.first.side_effect = [
            practice_session,
            user
        ]
        
        mock_openai_service.return_value.provide_writing_feedback.return_value = {
            "estimated_band": 7.5,
            "strengths": ["Good structure."],
            "areas_for_improvement": ["More complex vocabulary needed."],
            "task_achievement": "Achieved",
            "coherence_cohesion": "Cohesive",
            "lexical_resource": "Good",
            "grammatical_range_accuracy": "Accurate"
        }
        
        result = await handle_essay(mock_update, mock_context)
        
        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_any_call("Thank you. Analyzing your essay now, this may take a moment...")
        
        # Check that the mock session object was updated
        assert practice_session.score == 7.5
        assert mock_context.user_data == {}


@pytest.mark.asyncio
@patch("handlers.writing_practice_handler._get_recommendation", return_value="listening")
async def test_handle_essay_sends_recommendation(
    mock_get_recommendation, session, mock_update, mock_context
):
    """Tests that a recommendation is sent after the writing practice ends."""
    user = User(user_id=mock_update.effective_user.id, preferred_language="en")
    session.add(user)
    session.commit()

    practice_session = PracticeSession(
        user_id=user.id, section="writing_task_2", total_questions=1
    )
    session.add(practice_session)
    session.commit()

    mock_context.user_data = {
        "writing_session_id": practice_session.id,
        "writing_question": "Test question",
    }
    mock_update.message.text = "This is my essay."

    with patch("handlers.writing_practice_handler.db.session.query") as mock_query, patch(
        "handlers.writing_practice_handler.OpenAIService"
    ) as mock_openai_service, patch("sqlalchemy.orm.attributes.flag_modified"):
        mock_query.return_value.filter_by.return_value.first.side_effect = [
            practice_session,
            user,
        ]
        mock_openai_service.return_value.provide_writing_feedback.return_value = {
            "estimated_band": 7.0
        }

        result = await handle_essay(mock_update, mock_context)

        assert result == ConversationHandler.END
        mock_get_recommendation.assert_called_once()

        # The last call should be the recommendation
        last_call = mock_update.message.reply_text.call_args_list[-1].kwargs
        assert (
            "challenge yourself with a Listening practice next" in last_call["text"]
        )
        reply_markup = last_call["reply_markup"]
        assert len(reply_markup.inline_keyboard) == 1
        assert reply_markup.inline_keyboard[0][0].text == "Start Listening Practice"
        assert (
            reply_markup.inline_keyboard[0][0].callback_data == "practice_listening"
        ) 