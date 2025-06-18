from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from models import User, TeacherExercise
from .decorators import error_handler, teacher_required
from utils.translation_system import TranslationSystem
from extensions import db
from utils.input_validator import InputValidator

trans = TranslationSystem()

# Conversation states
(
    GET_TITLE,
    GET_DESCRIPTION,
    GET_TYPE,
    GET_DIFFICULTY,
    GET_CONTENT,
    CONFIRMATION,
) = range(6)


@error_handler
@teacher_required
async def create_exercise_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Starts the exercise creation conversation."""
    await update.message.reply_text(
        text=trans.get_message(
            "teacher_exercise", "create_start", user.preferred_language
        )
    )
    return GET_TITLE


@error_handler
async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the exercise title and asks for the description."""
    context.user_data["title"] = update.message.text
    user_id = update.effective_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()

    await update.message.reply_text(
        text=trans.get_message(
            "teacher_exercise", "ask_for_description", user.preferred_language
        )
    )
    return GET_DESCRIPTION


@error_handler
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the description and asks for the exercise type."""
    context.user_data["description"] = update.message.text
    user_id = update.effective_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()

    keyboard = [
        [
            InlineKeyboardButton("Vocabulary", callback_data="type_vocabulary"),
            InlineKeyboardButton("Grammar", callback_data="type_grammar"),
        ],
        [
            InlineKeyboardButton("Reading", callback_data="type_reading"),
            InlineKeyboardButton("Writing", callback_data="type_writing"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text=trans.get_message(
            "teacher_exercise", "ask_for_type", user.preferred_language
        ),
        reply_markup=reply_markup,
    )
    return GET_TYPE


@error_handler
async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the exercise type and asks for the difficulty."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query
    
    # The callback_data is 'type_vocabulary', 'type_grammar', etc.
    exercise_type = query.data.split('_')[1]
    context.user_data["type"] = exercise_type
    
    user_id = query.from_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()

    keyboard = [
        [
            InlineKeyboardButton("Beginner", callback_data="difficulty_beginner"),
            InlineKeyboardButton("Intermediate", callback_data="difficulty_intermediate"),
            InlineKeyboardButton("Advanced", callback_data="difficulty_advanced"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=trans.get_message(
            "teacher_exercise", "ask_for_difficulty", user.preferred_language
        ),
        reply_markup=reply_markup
    )
    return GET_DIFFICULTY


@error_handler
async def get_difficulty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the difficulty and asks for the exercise content."""
    query = update.callback_query
    await query.answer()

    difficulty = query.data.split('_')[1]
    context.user_data["difficulty"] = difficulty

    user_id = query.from_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()

    await query.edit_message_text(
        text=trans.get_message(
            "teacher_exercise", "ask_for_content", user.preferred_language
        )
    )
    return GET_CONTENT


@error_handler
async def get_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the content and creates the exercise, with validation."""
    user_id = update.effective_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()
    
    content = InputValidator.validate_exercise_content(update.message.text)
    
    if content is None:
        await update.message.reply_text(
            text=trans.get_message(
                "teacher_exercise", "invalid_content", user.preferred_language
            )
        )
        return GET_CONTENT # Stay in the same state to allow user to retry

    context.user_data["content"] = content
    
    # Find the teacher profile associated with the user
    teacher = user.teacher_profile
    if not teacher:
        await update.message.reply_text(text=trans.get_message('teacher', 'teacher_profile_not_found', user.preferred_language))
        return ConversationHandler.END

    # All data collected, create the exercise
    exercise_data = context.user_data
    new_exercise = TeacherExercise(
        creator_id=teacher.id,  # Use the teacher's ID
        title=exercise_data["title"],
        description=exercise_data["description"],
        exercise_type=exercise_data["type"],
        difficulty=exercise_data["difficulty"],
        content=exercise_data["content"],
    )
    db.session.add(new_exercise)
    db.session.commit()  # Commit the changes to the database

    await update.message.reply_text(
        text=trans.get_message(
            "teacher_exercise", "create_success", user.preferred_language, title=exercise_data["title"]
        )
    )
    
    # Clean up user_data
    context.user_data.clear()
    
    return ConversationHandler.END


@error_handler
async def cancel_exercise_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the exercise creation process."""
    user_id = update.effective_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()
    
    context.user_data.clear()
        
    await update.message.reply_text(
        text=trans.get_message(
            "teacher_exercise", "create_cancel", user.preferred_language
        )
    )
    return ConversationHandler.END


@error_handler
@teacher_required
async def my_exercises_command(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Handles the /my_exercises command for teachers, listing their created exercises."""
    
    exercises = db.session.query(TeacherExercise).filter_by(creator_id=user.id).all()
    
    language = user.preferred_language
    
    if not exercises:
        message = trans.get_message('teacher', 'my_exercises_none', language)
    else:
        message = trans.get_message('teacher', 'my_exercises_list_title', language) + "\\n\\n"
        exercise_list = []
        for ex in exercises:
            status_key = 'published' if ex.is_published else 'draft'
            status = trans.get_message('teacher', f'exercise_status_{status_key}', language)
            exercise_list.append(
                f"📝 *{ex.title}* ({ex.exercise_type}, {ex.difficulty})\\n"
                f"   Status: {status}\\n"
                f"   /view_exercise_{ex.id}"
            )
        message += "\\n\\n".join(exercise_list)

    await update.message.reply_text(text=message, parse_mode='Markdown') 


# Conversation handler for creating an exercise
create_exercise_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("create_exercise", create_exercise_start)],
    states={
        GET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        GET_DESCRIPTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)
        ],
        GET_TYPE: [CallbackQueryHandler(get_type, pattern="^type_")],
        GET_DIFFICULTY: [
            CallbackQueryHandler(get_difficulty, pattern="^difficulty_")
        ],
        GET_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_content)],
    },
    fallbacks=[CommandHandler("cancel", cancel_exercise_creation)],
    per_user=True,
    per_chat=True
) 