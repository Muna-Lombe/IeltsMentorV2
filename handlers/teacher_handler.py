from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from models import User, Group, TeacherExercise, Homework
from extensions import db
from utils.translation_system import TranslationSystem
from .decorators import error_handler, teacher_required

# Initialize translation system
trans = TranslationSystem()

# Define states for group creation ConversationHandler
GET_GROUP_NAME, GET_GROUP_DESCRIPTION = range(2)

# Define states for homework assignment ConversationHandler
SELECTING_GROUP, SELECTING_EXERCISE = range(2, 4)

@error_handler
@teacher_required
async def create_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Starts the group creation conversation."""
    context.user_data['user_id'] = user.user_id  # Pass user_id to context
    await update.message.reply_text(text=trans.get_message('teacher', 'create_group_start', user.preferred_language))
    return GET_GROUP_NAME

@error_handler
async def get_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the group name and asks for the description."""
    user_id = update.effective_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()
    
    group_name = update.message.text
    if not group_name or len(group_name) < 3:
        await update.message.reply_text(text=trans.get_message('teacher', 'create_group_invalid_name', user.preferred_language))
        return GET_GROUP_NAME
        
    context.user_data['group_name'] = group_name
    
    await update.message.reply_text(text=trans.get_message('teacher', 'create_group_ask_description', user.preferred_language))
    return GET_GROUP_DESCRIPTION

@error_handler
async def get_group_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the description, creates the group, and ends the conversation."""
    user_id = update.effective_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()

    group_name = context.user_data.get('group_name')
    group_description = update.message.text

    # Find the teacher profile associated with the user
    teacher = user.teacher_profile
    if not teacher:
        await update.message.reply_text(text=trans.get_message('teacher', 'teacher_profile_not_found', user.preferred_language))
        return ConversationHandler.END

    new_group = Group(
        name=group_name,
        description=group_description,
        teacher_id=teacher.id  # Use the teacher's ID
    )
    db.session.add(new_group)
    db.session.commit()  # Commit the changes to the database

    await update.message.reply_text(text=trans.get_message('teacher', 'create_group_success', user.preferred_language, group_name=group_name))
    
    del context.user_data['group_name']
    return ConversationHandler.END

@error_handler
async def cancel_group_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the group creation process."""
    user_id = update.effective_user.id
    user = db.session.query(User).filter(User.user_id == user_id).first()
    
    if 'group_name' in context.user_data:
        del context.user_data['group_name']
        
    await update.message.reply_text(text=trans.get_message('teacher', 'create_group_cancel', user.preferred_language))
    return ConversationHandler.END

# Define the conversation handler for creating a group
create_group_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('create_group', create_group_start)],
    states={
        GET_GROUP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_group_name)],
        GET_GROUP_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_group_description)],
    },
    fallbacks=[CommandHandler('cancel', cancel_group_creation)],
    per_user=True,
    per_chat=True,
)

@error_handler
@teacher_required
async def assign_homework_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Starts the homework assignment conversation by listing the teacher's groups."""
    print(f"user: {user}")
    teacher = user.teacher_profile
    print(f"is teacher: {teacher}")

    if not teacher or not teacher.groups:
        await update.message.reply_text(text=trans.get_message('teacher', 'no_groups_for_homework', user.preferred_language))
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(group.name, callback_data=f"hw_group_{group.id}")]
        for group in teacher.groups
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text=trans.get_message('teacher', 'assign_homework_select_group', user.preferred_language),
        reply_markup=reply_markup
    )
    return SELECTING_GROUP

@error_handler
async def select_group_for_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles group selection and lists the teacher's exercises."""
    query = update.callback_query
    await query.answer()

    group_id = int(query.data.split('_')[-1])
    context.user_data['homework_group_id'] = group_id
    
    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()
    teacher = user.teacher_profile

    if not teacher.created_exercises:
        await query.edit_message_text(text=trans.get_message('teacher', 'no_exercises_to_assign', user.preferred_language))
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(ex.title, callback_data=f"hw_ex_{ex.id}")]
        for ex in teacher.created_exercises if ex.is_published
    ]
    if not keyboard:
        await query.edit_message_text(text=trans.get_message('teacher', 'no_published_exercises_to_assign', user.preferred_language))
        return ConversationHandler.END

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=trans.get_message('teacher', 'assign_homework_select_exercise', user.preferred_language),
        reply_markup=reply_markup
    )
    return SELECTING_EXERCISE

@error_handler
async def select_exercise_for_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles exercise selection, creates the homework, and ends."""
    query = update.callback_query
    await query.answer()

    exercise_id = int(query.data.split('_')[-1])
    group_id = context.user_data['homework_group_id']

    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()
    teacher = user.teacher_profile

    # Create homework record
    new_homework = Homework(
        exercise_id=exercise_id,
        group_id=group_id,
        assigned_by_id=teacher.id
    )
    db.session.add(new_homework)
    db.session.commit()

    group = db.session.query(Group).filter_by(id=group_id).first()
    exercise = db.session.query(TeacherExercise).filter_by(id=exercise_id).first()

    await query.edit_message_text(
        text=trans.get_message(
            'teacher', 
            'assign_homework_success', 
            user.preferred_language, 
            exercise_title=exercise.title, 
            group_name=group.name
        )
    )

    context.user_data.pop('homework_group_id', None)
    return ConversationHandler.END

@error_handler
async def cancel_homework_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the homework assignment process."""
    query = update.callback_query
    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()
    
    await query.answer()
    await query.edit_message_text(
        text=trans.get_message('teacher', 'assign_homework_cancel', user.preferred_language)
    )
    context.user_data.pop('homework_group_id', None)
    return ConversationHandler.END

# Define the conversation handler for assigning homework
assign_homework_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('assign_homework', assign_homework_start)],
    states={
        SELECTING_GROUP: [CallbackQueryHandler(select_group_for_homework, pattern='^hw_group_')],
        SELECTING_EXERCISE: [CallbackQueryHandler(select_exercise_for_homework, pattern='^hw_ex_')],
    },
    fallbacks=[CallbackQueryHandler(cancel_homework_assignment, pattern='^cancel_hw$')],
    per_user=True,
    per_chat=True,
) 