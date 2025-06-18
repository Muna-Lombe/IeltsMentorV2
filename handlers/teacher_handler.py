from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from models import User, Group
from extensions import db
from utils.translation_system import TranslationSystem
from .decorators import error_handler, teacher_required

# Initialize translation system
trans = TranslationSystem()

# Define states for ConversationHandler
GET_GROUP_NAME, GET_GROUP_DESCRIPTION = range(2)

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