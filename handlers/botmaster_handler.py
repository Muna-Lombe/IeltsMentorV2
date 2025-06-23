import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

from handlers.decorators import botmaster_required, error_handler
from models import User, Teacher, Group, TeacherExercise, Homework, PracticeSession
from extensions import db
from utils.translation_system import TranslationSystem
from services.auth_service import AuthService

# Initialize logger and translation system
logger = logging.getLogger(__name__)
trans = TranslationSystem()

# Conversation states
SELECTING_USER, APPROVING_USER = range(2)

# Constants for content management
MANAGE_CONTENT_PAGE_SIZE = 5
SELECTING_CONTENT_ACTION = range(2, 3)

@error_handler
@botmaster_required
async def approve_teacher_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Starts the teacher approval process."""
    await update.message.reply_text(
        text=trans.get_message('botmaster', 'approve_teacher_prompt', user.preferred_language)
    )
    return SELECTING_USER

async def get_user_to_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gets the user to approve and proceeds with approval."""
    botmaster = context.user_data['botmaster'] # We'll need to set this
    language = botmaster.preferred_language
    user_input = update.message.text.strip()
    
    # Simple lookup by username or ID
    if user_input.isdigit():
        user_to_approve = db.session.query(User).filter(User.user_id == int(user_input)).first()
    else:
        username = user_input.lstrip('@')
        user_to_approve = db.session.query(User).filter(User.username == username).first()

    if not user_to_approve:
        await update.message.reply_text(text=trans.get_message('botmaster', 'user_not_found', language))
        return ConversationHandler.END

    if not user_to_approve.teacher_profile:
        # This user hasn't requested to be a teacher
        await update.message.reply_text(text=trans.get_message('botmaster', 'not_a_teacher_applicant', language))
        return ConversationHandler.END

    if user_to_approve.teacher_profile.is_approved:
        await update.message.reply_text(text=trans.get_message('botmaster', 'already_approved', language))
        return ConversationHandler.END

    user_to_approve.teacher_profile.is_approved = True
    # Assign an API token upon approval
    AuthService.assign_token_to_teacher(user_to_approve.teacher_profile)
    db.session.commit()

    await update.message.reply_text(
        text=trans.get_message(
            'botmaster',
            'approve_teacher_success',
            language,
            teacher_name=user_to_approve.username or user_to_approve.first_name
        )
    )
    return ConversationHandler.END

@botmaster_required
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Cancels the conversation."""
    language = user.preferred_language
    await update.message.reply_text(text=trans.get_message('botmaster', 'action_cancelled', language))
    return ConversationHandler.END

@botmaster_required
async def system_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Displays system-wide statistics."""
    language = user.preferred_language
    
    total_users = db.session.query(User).count()
    total_teachers = db.session.query(Teacher).filter_by(is_approved=True).count()
    total_groups = db.session.query(Group).count()
    total_exercises = db.session.query(TeacherExercise).count()
    total_homeworks = db.session.query(Homework).count()

    stats_message = trans.get_message(
        'botmaster',
        'system_stats_message',
        language,
        total_users=total_users,
        total_teachers=total_teachers,
        total_groups=total_groups,
        total_exercises=total_exercises,
        total_homeworks=total_homeworks
    )
    
    await update.message.reply_text(stats_message)

# We need to pass the botmaster user object from the entry point to other states
# A better way would be to refactor the decorator or use a different state management
async def patched_get_user_to_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    botmaster = db.session.query(User).filter(User.user_id == user_id).first()
    context.user_data['botmaster'] = botmaster
    return await get_user_to_approve(update, context)


approve_teacher_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("approve_teacher", approve_teacher_start)],
    states={
        SELECTING_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, patched_get_user_to_approve)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=False,
    per_user=True
)

@error_handler
@botmaster_required
async def manage_content_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Displays the first page of teacher-created exercises for management."""
    context.user_data['content_page'] = 0
    
    exercises = db.session.query(TeacherExercise).order_by(TeacherExercise.created_at.desc()).limit(MANAGE_CONTENT_PAGE_SIZE).all()
    
    if not exercises:
        await update.message.reply_text(trans.get_message('botmaster', 'no_content_to_manage', user.preferred_language))
        return ConversationHandler.END

    message_text = trans.get_message('botmaster', 'manage_content_header', user.preferred_language)
    keyboard = []
    for ex in exercises:
        status = "Published" if ex.is_published else "Draft"
        keyboard.append([InlineKeyboardButton(f"{ex.title} ({status})", callback_data=f"content_{ex.id}")])
    
    # Add navigation buttons if needed
    # For simplicity, we'll start without pagination
    
    await update.message.reply_text(text=message_text, reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_CONTENT_ACTION

@error_handler
@botmaster_required
async def manage_content_action(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Handles actions on a selected piece of content."""
    query = update.callback_query
    await query.answer()
    
    exercise_id = int(query.data.split('_')[1])
    exercise = db.session.query(TeacherExercise).filter_by(id=exercise_id).first()
    
    if not exercise:
        await query.edit_message_text(trans.get_message('botmaster', 'content_not_found', user.preferred_language))
        return ConversationHandler.END
        
    # Toggle publish status
    exercise.is_published = not exercise.is_published
    db.session.commit()
    
    status = "Published" if exercise.is_published else "Draft"
    await query.edit_message_text(
        text=trans.get_message('botmaster', 'content_status_changed', user.preferred_language, title=exercise.title, status=status)
    )
    
    # We can end the conversation here or allow more actions. Ending is simpler.
    return ConversationHandler.END


manage_content_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("manage_content", manage_content_start)],
    states={
        SELECTING_CONTENT_ACTION: [CallbackQueryHandler(manage_content_action, pattern="^content_")],
    },
    fallbacks=[CommandHandler("cancel", cancel)], # Can reuse the same cancel
) 