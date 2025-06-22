from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from models import User, Group, TeacherExercise, Homework, GroupMembership
from extensions import db
from utils.translation_system import TranslationSystem
from .decorators import error_handler, teacher_required
from sqlalchemy.orm import joinedload
from models import PracticeSession

# Initialize translation system
trans = TranslationSystem()

# Define states for group creation ConversationHandler
GET_GROUP_NAME, GET_GROUP_DESCRIPTION = range(2)

# Define states for homework assignment ConversationHandler
SELECTING_GROUP, SELECTING_EXERCISE = range(2, 4)

# Define state for group analytics
SELECTING_GROUP_ANALYTICS = range(4, 5)

# Define states for student progress
SELECT_GROUP_FOR_PROGRESS, SELECT_STUDENT_FOR_PROGRESS = range(5, 7)

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
    """Starts the homework assignment conversation by listing the teacher's taught_groups."""
    # print(f"user: {user}")
    teacher = user.teacher_profile
    # print(f"is teacher: {teacher}")

    if not teacher or not teacher.taught_groups:
        await update.message.reply_text(text=trans.get_message('teacher', 'no_groups_for_homework', user.preferred_language))
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(group.name, callback_data=f"hw_group_{group.id}")]
        for group in teacher.taught_groups
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

    if not teacher.exercises:
        await query.edit_message_text(text=trans.get_message('teacher', 'no_exercises_to_assign', user.preferred_language))
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(ex.title, callback_data=f"hw_ex_{ex.id}")]
        for ex in teacher.exercises if ex.is_published
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

@error_handler
@teacher_required
async def group_analytics_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Starts the group analytics process by listing the teacher's groups."""
    teacher = user.teacher_profile
    if not teacher:
        await update.message.reply_text(
            text=trans.get_message('teacher', 'teacher_profile_not_found', user.preferred_language)
        )
        return ConversationHandler.END

    # Explicitly query for groups to ensure the session has the latest data
    taught_groups = db.session.query(Group).filter_by(teacher_id=teacher.id).all()

    if not taught_groups:
        await update.message.reply_text(
            text=trans.get_message('teacher', 'no_groups_for_analytics', user.preferred_language)
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(group.name, callback_data=f"ga_group_{group.id}")]
        for group in taught_groups
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text=trans.get_message('teacher', 'select_group_for_analytics', user.preferred_language),
        reply_markup=reply_markup
    )
    return SELECTING_GROUP_ANALYTICS

@error_handler
async def show_group_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and displays analytics for the selected group."""
    query = update.callback_query
    await query.answer()

    group_id = int(query.data.split('_')[-1])
    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()

    group = db.session.query(Group).options(joinedload(Group.memberships).joinedload(GroupMembership.student)).filter_by(id=group_id).first()
    
    if not group or group.teacher_id != user.teacher_profile.id:
        await query.edit_message_text(text=trans.get_message('errors', 'unauthorized', user.preferred_language))
        return ConversationHandler.END

    member_ids = [m.student_id for m in group.memberships]
    analytics_summary = "No analytics data available for this group yet."

    if member_ids:
        sessions = db.session.query(PracticeSession).filter(PracticeSession.user_id.in_(member_ids)).all()
        
        if sessions:
            total_sessions = len(sessions)
            reading_scores, writing_scores, speaking_scores, listening_scores = [], [], [], []

            for s in sessions:
                if s.score is not None:
                    if 'reading' in s.section: reading_scores.append(s.score)
                    elif 'writing' in s.section: writing_scores.append(s.score)
                    elif 'speaking' in s.section: speaking_scores.append(s.score)
                    elif 'listening' in s.section: listening_scores.append(s.score)
            
            analytics = {
                "total_sessions": total_sessions,
                "members_count": len(member_ids),
                "reading_avg": sum(reading_scores) / len(reading_scores) if reading_scores else 0,
                "writing_avg": sum(writing_scores) / len(writing_scores) if writing_scores else 0,
                "speaking_avg": sum(speaking_scores) / len(speaking_scores) if speaking_scores else 0,
                "listening_avg": sum(listening_scores) / len(listening_scores) if listening_scores else 0,
            }

            analytics_summary = trans.get_message(
                'teacher', 
                'group_analytics_summary',
                user.preferred_language,
                group_name=group.name,
                **analytics
            )

    await query.edit_message_text(text=analytics_summary, parse_mode='Markdown')
    return ConversationHandler.END

# Define the conversation handler for group analytics
group_analytics_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('group_analytics', group_analytics_start)],
    states={
        SELECTING_GROUP_ANALYTICS: [CallbackQueryHandler(show_group_analytics, pattern='^ga_group_')],
    },
    fallbacks=[CommandHandler('cancel', cancel_group_creation)], # Can reuse cancel logic
)

@error_handler
@teacher_required
async def student_progress_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Starts the student progress check by listing the teacher's groups."""
    teacher = user.teacher_profile
    if not teacher:
        await update.message.reply_text(trans.get_message('teacher', 'teacher_profile_not_found', user.preferred_language))
        return ConversationHandler.END

    taught_groups = db.session.query(Group).filter_by(teacher_id=teacher.id).all()
    if not taught_groups:
        await update.message.reply_text(trans.get_message('teacher', 'no_groups_for_student_progress', user.preferred_language))
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(g.name, callback_data=f"sp_group_{g.id}")] for g in taught_groups]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text=trans.get_message('teacher', 'select_group_for_student_progress', user.preferred_language),
        reply_markup=reply_markup
    )
    return SELECT_GROUP_FOR_PROGRESS

@error_handler
async def select_group_for_student_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists students in the selected group."""
    query = update.callback_query
    await query.answer()
    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()

    group_id = int(query.data.split('_')[-1])
    group = db.session.query(Group).options(joinedload(Group.memberships).joinedload(GroupMembership.student)).filter_by(id=group_id).first()

    if not group or group.teacher_id != user.teacher_profile.id:
        await query.edit_message_text(text=trans.get_message('errors', 'unauthorized', user.preferred_language))
        return ConversationHandler.END

    if not group.memberships:
        await query.edit_message_text(text=trans.get_message('teacher', 'no_students_in_group', user.preferred_language))
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(m.student.first_name, callback_data=f"sp_student_{m.student.id}")]
        for m in group.memberships
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=trans.get_message('teacher', 'select_student_for_progress', user.preferred_language, group_name=group.name),
        reply_markup=reply_markup
    )
    return SELECT_STUDENT_FOR_PROGRESS

@error_handler
async def show_student_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the selected student's progress."""
    query = update.callback_query
    await query.answer()
    teacher_user = db.session.query(User).filter_by(user_id=query.from_user.id).first()

    student_user_id = int(query.data.split('_')[-1])
    student = db.session.query(User).filter_by(id=student_user_id).first()
    
    # Basic authorization: check if student is in one of the teacher's groups.
    # A more robust check would be to pass the group_id through context.
    is_authorized = any(
        student.id in [m.student_id for m in g.memberships]
        for g in teacher_user.teacher_profile.taught_groups
    )

    if not student or not is_authorized:
        await query.edit_message_text(text=trans.get_message('errors', 'unauthorized_student', teacher_user.preferred_language))
        return ConversationHandler.END

    stats = student.stats or {}
    progress_report = trans.get_message(
        'teacher', 'student_progress_report', teacher_user.preferred_language,
        student_name=student.first_name,
        skill_level=student.skill_level or "Not Assessed",
        reading_score=f"{stats.get('reading', {}).get('correct', 0)}/{stats.get('reading', {}).get('total', 0)}",
        writing_score=f"{stats.get('writing', {}).get('band', 'N/A')}",
        speaking_score=f"{stats.get('speaking', {}).get('band', 'N/A')}",
        listening_score=f"{stats.get('listening', {}).get('correct', 0)}/{stats.get('listening', {}).get('total', 0)}",
    )
    await query.edit_message_text(text=progress_report, parse_mode='Markdown')
    return ConversationHandler.END

# Define the conversation handler for student progress
student_progress_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('student_progress', student_progress_start)],
    states={
        SELECT_GROUP_FOR_PROGRESS: [CallbackQueryHandler(select_group_for_student_progress, pattern='^sp_group_')],
        SELECT_STUDENT_FOR_PROGRESS: [CallbackQueryHandler(show_student_progress, pattern='^sp_student_')],
    },
    fallbacks=[CommandHandler('cancel', cancel_group_creation)],
) 