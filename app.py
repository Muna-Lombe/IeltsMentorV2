import asyncio
import os
import logging
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime

from extensions import db, migrate
from config import config
from handlers import (
    core_handlers, 
    practice_handler, 
    ai_commands_handler, 
    teacher_handler, 
    exercise_management_handler,
    speaking_practice_handler,
    writing_practice_handler,
    listening_practice_handler,
    botmaster_handler,
)
from handlers.reading_practice_handler import reading_practice_conv_handler
from handlers.speaking_practice_handler import speaking_practice_conv_handler
from handlers.writing_practice_handler import writing_practice_conv_handler
from handlers.listening_practice_handler import listening_practice_conv_handler
from utils.translation_system import TranslationSystem
from services.auth_service import AuthService
from extensions import db
from models.user import User
from models.teacher import Teacher
from models.group import Group, GroupMembership
from models.exercise import TeacherExercise
from models.practice_session import PracticeSession
from models.homework import Homework, HomeworkSubmission

# New Imports for Bot Initialization
import time
import json
import requests
from flask_wtf.csrf import CSRFProtect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define a class for bot status to support attribute access
class BotStatus:

    def __init__(self):
        # Default attributes
        self._attrs = {
            'running': False,
            'start_time': None,
            'error': None,
            'telegram_bot_username': None,
            'bot_instance': None,
            'instance_id': None,
            'webhook_url': None
        }

    def __getattr__(self, name):
        # Allow dynamic attribute access
        if name in self._attrs:
            return self._attrs[name]
        raise AttributeError(f"'BotStatus' has no attribute '{name}'")

    def __setattr__(self, name, value):
        # For setting attributes dynamically
        if name == '_attrs':
            super().__setattr__(name, value)
        else:
            self._attrs[name] = value

    def get(self, key, default=None):
        return self._attrs.get(key, default)

    # For compatibility with jsonify
    def __iter__(self):
        # Skip the bot instance object for serialization
        for key, value in self._attrs.items():
            if key != 'bot_instance':
                yield key, value

# Global variable to track bot status
bot_status = BotStatus()

# Helper function to get bot info
async def get_bot_info():
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_bot_token:
        return None

    bot = application.bot  # Use the existing application.bot instance
    
    try:
        # Fetch bot info using the bot instance
        bot_user = await bot.get_me()
        return {
            "username": bot_user.username,
            "id": bot_user.id,
            "bot": bot  # Store the bot instance
        }
    except Exception as e:
        logger.error(f"Error fetching bot info: {e}")
        return None

# Helper function to process updates
async def process_update(update_data):
    try:
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")

# Initialize the Telegram Bot Application
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
if not telegram_bot_token:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

application = Application.builder().token(telegram_bot_token).build()

# Register handlers
application.add_handler(CommandHandler("start", core_handlers.start))
application.add_handler(CommandHandler("stats", core_handlers.stats_command))
application.add_handler(CommandHandler("practice", practice_handler.practice_command))
application.add_handler(CommandHandler("explain", ai_commands_handler.explain_command))
application.add_handler(CommandHandler("define", ai_commands_handler.define_command))
application.add_handler(teacher_handler.create_group_conv_handler)
application.add_handler(teacher_handler.assign_homework_conv_handler)
application.add_handler(CommandHandler("my_exercises", exercise_management_handler.my_exercises_command))
application.add_handler(exercise_management_handler.create_exercise_conv_handler)
application.add_handler(reading_practice_conv_handler)
application.add_handler(speaking_practice_conv_handler)
application.add_handler(writing_practice_conv_handler)
application.add_handler(listening_practice_conv_handler)
application.add_handler(botmaster_handler.approve_teacher_conv_handler)
application.add_handler(CommandHandler("system_stats", botmaster_handler.system_stats))
application.add_handler(teacher_handler.group_analytics_conv_handler)
application.add_handler(teacher_handler.student_progress_conv_handler)
application.add_handler(botmaster_handler.manage_content_conv_handler)

# Register error handler
application.add_error_handler(core_handlers.error_handler)

# Fallback for unknown commands
application.add_handler(MessageHandler(filters.COMMAND, core_handlers.unknown_command))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def create_app(config_name='development'):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    
    # Load config from config.py
    app.config.from_object(config[config_name])

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)


    # Initialize CSRF protection (if Flask-WTF is installed and configured)
    CSRFProtect(app)

    # Import models and register routes within the app context
    with app.app_context():
        @app.route("/")
        def index():
            return render_template("landing.html")
        
        @app.route("/login", methods=["GET", "POST"])
        def login():
            if request.method == "POST":
                token = request.form.get("api_token")
                user = AuthService.validate_token(token)
                if user:
                    session['user_id'] = user.id
                    session['user_first_name'] = user.first_name
                    return redirect(url_for('dashboard'))
                else:
                    flash("Invalid API Token. Please try again.", "error")
                    return render_template("login.html", error="Invalid API Token.")
            return render_template("login.html")

        @app.route("/dashboard")
        @login_required
        def dashboard():
            user_id = session.get('user_id')
            user = db.session.get(User, user_id)
            return render_template("dashboard.html", user=user)

        @app.route("/homework")
        @login_required
        def homework_page():
            return render_template("homework.html")

        @app.route("/logout")
        def logout():
            session.clear()
            return redirect(url_for('login'))

        @app.route("/groups/<int:group_id>")
        @login_required
        def group_details_page(group_id):
            return render_template("group_details.html", group_id=group_id)

        @app.route("/exercises/new")
        @login_required
        def new_exercise_page():
            return render_template("exercise_details.html", exercise=None)

        @app.route("/exercises/<int:exercise_id>")
        @login_required
        def exercise_details_page(exercise_id):
            # The template will fetch the data, we just need to pass the ID
            return render_template("exercise_details.html", exercise_id=exercise_id)

        @app.route("/students/<int:student_id>")
        @login_required
        def student_details_page(student_id):
            return render_template("student_details.html", student_id=student_id)

        @app.route("/analytics/groups/<int:group_id>")
        @login_required
        def group_analytics_page(group_id):
            return render_template("analytics.html", group_id=group_id)

        @app.route("/student/<int:student_id>")
        @login_required
        def student_details(student_id):
            # No need to fetch student details here, it's done by an API call from the frontend
            return render_template("student_details.html", student_id=student_id)

        # API Endpoints
        @app.route("/api/groups", methods=["GET"])
        @login_required
        def get_groups():
            teacher_user_id = session.get('user_id')
            groups = db.session.query(Group).filter_by(teacher_id=teacher_user_id).all()
            groups_data = [{"id": group.id, "name": group.name, "description": group.description} for group in groups]
            return jsonify({"success": True, "data": groups_data})

        @app.route("/api/groups", methods=["POST"])
        @login_required
        def create_group():
            teacher_user_id = session.get('user_id')
            data = request.json
            name = data.get('name')
            description = data.get('description')

            if not name:
                return jsonify({"success": False, "error": "Group name is required"}), 400

            new_group = Group(name=name, description=description, teacher_id=teacher_user_id)
            db.session.add(new_group)
            db.session.commit()

            return jsonify({"success": True, "data": {"id": new_group.id, "name": new_group.name, "description": new_group.description}}), 201

        @app.route("/api/groups/<int:group_id>", methods=["GET"])
        @login_required
        def get_group(group_id):
            teacher_user_id = session.get('user_id')
            group = db.session.query(Group).filter_by(id=group_id).first()

            if not group:
                return jsonify({"success": False, "error": "Group not found"}), 404

            if group.teacher_id != teacher_user_id:
                return jsonify({"success": False, "error": "Unauthorized"}), 403
            
            members = [{"id": member.id, "first_name": member.first_name, "last_name": member.last_name, "username": member.username} for member in group.members]

            return jsonify({
                "success": True,
                "data": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "members": members
                }
            })

        @app.route("/api/groups/<int:group_id>", methods=["PUT"])
        @login_required
        def update_group(group_id):
            teacher_user_id = session.get('user_id')
            group = db.session.query(Group).filter_by(id=group_id, teacher_id=teacher_user_id).first()

            if not group:
                return jsonify({"success": False, "error": "Group not found or you are not authorized"}), 404

            data = request.json
            group.name = data.get('name', group.name)
            group.description = data.get('description', group.description)
            db.session.commit()

            return jsonify({"success": True, "data": {"id": group.id, "name": group.name, "description": group.description}})

        @app.route("/api/groups/<int:group_id>/members", methods=["POST"])
        @login_required
        def add_group_member(group_id):
            teacher_user_id = session.get('user_id')
            group = db.session.query(Group).filter_by(id=group_id, teacher_id=teacher_user_id).first()

            if not group:
                return jsonify({"success": False, "error": "Group not found or you are not authorized"}), 404

            data = request.json
            student_id = data.get('student_id')

            if not student_id:
                return jsonify({"success": False, "error": "Student ID is required"}), 400

            student = db.session.query(User).filter_by(id=student_id).first()
            if not student:
                return jsonify({"success": False, "error": "Student not found"}), 404
            
            existing_membership = db.session.query(GroupMembership).filter_by(group_id=group.id, student_id=student.id).first()
            if existing_membership:
                return jsonify({"success": False, "error": "Student is already in this group"}), 409

            new_membership = GroupMembership(group_id=group.id, student_id=student.id)
            db.session.add(new_membership)
            db.session.commit()

            return jsonify({"success": True, "message": "Student added to group successfully"}), 201

        @app.route("/api/groups/<int:group_id>/members/<int:student_id>", methods=["DELETE"])
        @login_required
        def remove_group_member(group_id, student_id):
            teacher_user_id = session.get('user_id')
            group = db.session.query(Group).filter_by(id=group_id, teacher_id=teacher_user_id).first()

            if not group:
                return jsonify({"success": False, "error": "Group not found or you are not authorized"}), 404

            membership = db.session.query(GroupMembership).filter_by(group_id=group.id, student_id=student_id).first()

            if not membership:
                return jsonify({"success": False, "error": "Student is not in this group"}), 404

            db.session.delete(membership)
            db.session.commit()

            return jsonify({"success": True, "message": "Student removed from group successfully"})

        @app.route("/api/students/<int:student_id>", methods=["GET"])
        @login_required
        def get_student_details(student_id):
            teacher_user_id = session.get('user_id')
            
            # Authorization check: is the student in any of the teacher's groups?
            is_authorized = db.session.query(GroupMembership).join(Group).filter(
                Group.teacher_id == teacher_user_id,
                GroupMembership.student_id == student_id
            ).first()

            if not is_authorized:
                return jsonify({"success": False, "error": "Unauthorized to view this student"}), 403

            student = db.session.query(User).filter_by(id=student_id).first()
            if not student:
                return jsonify({"success": False, "error": "Student not found"}), 404
            
            return jsonify({"success": True, "data": student.to_dict()})

        @app.route("/api/students/<int:student_id>/progress", methods=["GET"])
        @login_required
        def get_student_progress(student_id):
            teacher_user_id = session.get('user_id')

            # Authorization check
            is_authorized = db.session.query(GroupMembership).join(Group).filter(
                Group.teacher_id == teacher_user_id,
                GroupMembership.student_id == student_id
            ).first()

            if not is_authorized:
                return jsonify({"success": False, "error": "Unauthorized"}), 403

            student = db.session.get(User, student_id)
            if not student:
                return jsonify({"success": False, "error": "Student not found"}), 404

            practice_sessions = db.session.query(PracticeSession).filter_by(user_id=student.id).order_by(PracticeSession.completed_at.desc()).all()
            
            progress_data = {
                "student_id": student.id,
                "full_name": student.get_full_name(),
                "skill_level": student.skill_level,
                "practice_sessions": [ps.to_dict() for ps in practice_sessions]
            }
            
            return jsonify({"success": True, "data": progress_data})

        @app.route("/api/exercises", methods=["GET"])
        @login_required
        def get_exercises():
            teacher_user_id = session.get('user_id')
            exercises = db.session.query(TeacherExercise).filter_by(creator_id=teacher_user_id).all()
            exercises_data = [{"id": ex.id, "title": ex.title, "description": ex.description} for ex in exercises]
            return jsonify({"success": True, "data": exercises_data})

        @app.route("/api/exercises", methods=["POST"])
        @login_required
        def create_exercise():
            teacher_user_id = session.get('user_id')
            data = request.json
            
            title = data.get('title')
            if not title:
                return jsonify({"success": False, "error": "Exercise title is required"}), 400

            new_exercise = TeacherExercise(
                title=title,
                description=data.get('description'),
                creator_id=teacher_user_id,
                exercise_type=data.get('exercise_type', 'vocabulary'),
                difficulty=data.get('difficulty', 'medium'),
                content=data.get('content', {})
            )
            db.session.add(new_exercise)
            db.session.commit()

            return jsonify({"success": True, "data": {"id": new_exercise.id, "title": new_exercise.title, "description": new_exercise.description}}), 201

        @app.route("/api/exercises/<int:exercise_id>", methods=["GET"])
        @login_required
        def get_exercise(exercise_id):
            teacher_user_id = session.get('user_id')
            exercise = db.session.query(TeacherExercise).filter_by(id=exercise_id).first()

            if not exercise:
                return jsonify({"success": False, "error": "Exercise not found"}), 404

            if exercise.creator_id != teacher_user_id:
                return jsonify({"success": False, "error": "Unauthorized"}), 403

            return jsonify({
                "success": True,
                "data": {
                    "id": exercise.id,
                    "title": exercise.title,
                    "description": exercise.description,
                    "exercise_type": exercise.exercise_type,
                    "difficulty": exercise.difficulty,
                    "content": exercise.content,
                    "is_published": exercise.is_published
                }
            })

        @app.route("/api/exercises/<int:exercise_id>", methods=["PUT"])
        @login_required
        def update_exercise(exercise_id):
            teacher_user_id = session.get('user_id')
            exercise = db.session.query(TeacherExercise).filter_by(id=exercise_id, creator_id=teacher_user_id).first()

            if not exercise:
                return jsonify({"success": False, "error": "Exercise not found or not authorized"}), 404

            data = request.json
            exercise.title = data.get('title', exercise.title)
            exercise.description = data.get('description', exercise.description)
            exercise.exercise_type = data.get('exercise_type', exercise.exercise_type)
            exercise.difficulty = data.get('difficulty', exercise.difficulty)
            exercise.content = data.get('content', exercise.content)
            exercise.is_published = data.get('is_published', exercise.is_published)
            
            db.session.commit()
            return jsonify({"success": True, "data": exercise.to_dict()})

        @app.route("/api/exercises/<int:exercise_id>/publish", methods=["POST"])
        @login_required
        def publish_exercise(exercise_id):
            teacher_user_id = session.get('user_id')
            exercise = db.session.query(TeacherExercise).filter_by(id=exercise_id, creator_id=teacher_user_id).first()

            if not exercise:
                return jsonify({"success": False, "error": "Exercise not found or not authorized"}), 404

            exercise.is_published = True
            db.session.commit()
            
            return jsonify({"success": True, "data": exercise.to_dict()})

        @app.route("/api/homework", methods=["POST"])
        @login_required
        def assign_homework():
            teacher_user_id = session.get('user_id')
            data = request.json
            exercise_id = data.get('exercise_id')
            group_id = data.get('group_id')
            due_date_str = data.get('due_date')
            instructions = data.get('instructions')

            # Basic validation
            if not all([exercise_id, group_id]):
                return jsonify({"success": False, "error": "Exercise ID and Group ID are required"}), 400

            # Authorization: Check if teacher owns the group and the exercise
            group = db.session.query(Group).filter_by(id=group_id, teacher_id=teacher_user_id).first()
            exercise = db.session.query(TeacherExercise).filter_by(id=exercise_id, creator_id=teacher_user_id).first()

            if not group or not exercise:
                return jsonify({"success": False, "error": "Unauthorized or resource not found"}), 403

            due_date = datetime.fromisoformat(due_date_str) if due_date_str else None
            
            new_homework = Homework(
                exercise_id=exercise_id,
                group_id=group_id,
                assigned_by_id=teacher_user_id,
                due_date=due_date,
                instructions=instructions
            )
            db.session.add(new_homework)
            db.session.commit()
            
            return jsonify({"success": True, "message": "Homework assigned successfully.", "data": {"id": new_homework.id}}), 201

        @app.route("/api/homework", methods=["GET"])
        @login_required
        def get_homework_assignments():
            teacher_user_id = session.get('user_id')
            assignments = db.session.query(Homework).filter_by(assigned_by_id=teacher_user_id).all()
            
            data = [{
                "id": hw.id,
                "exercise_title": hw.exercise.title,
                "group_name": hw.group.name,
                "assigned_at": hw.assigned_at.isoformat(),
                "due_date": hw.due_date.isoformat() if hw.due_date else None
            } for hw in assignments]

            return jsonify({"success": True, "data": data})

        @app.route("/api/homework/<int:homework_id>/submissions", methods=["GET"])
        @login_required
        def get_homework_submissions(homework_id):
            teacher_user_id = session.get('user_id')
            
            # Authorization check
            homework = db.session.query(Homework).filter_by(id=homework_id, assigned_by_id=teacher_user_id).first()
            if not homework:
                return jsonify({"success": False, "error": "Homework not found or unauthorized"}), 404

            submissions = homework.submissions
            data = [{
                "id": sub.id,
                "student_name": sub.student.get_full_name(),
                "submitted_at": sub.submitted_at.isoformat(),
                "score": sub.score
            } for sub in submissions]

            return jsonify({"success": True, "data": data})

        @app.route("/api/analytics/groups/<int:group_id>", methods=["GET"])
        @login_required
        def get_group_analytics(group_id):
            teacher_user_id = session.get('user_id')
            
            # Authorization: ensure the teacher owns the group
            group = db.session.query(Group).filter_by(id=group_id, teacher_id=teacher_user_id).first()
            if not group:
                return jsonify({"success": False, "error": "Group not found or unauthorized"}), 404

            student_ids = [member.id for member in group.members]
            if not student_ids:
                return jsonify({"success": True, "data": {"message": "No students in this group."}})

            # Calculate average scores from practice sessions
            avg_scores = db.session.query(
                PracticeSession.section,
                db.func.avg(PracticeSession.score)
            ).filter(
                PracticeSession.user_id.in_(student_ids)
            ).group_by(PracticeSession.section).all()

            # Calculate homework stats
            homework_stats = db.session.query(
                db.func.count(Homework.id),
                db.func.count(HomeworkSubmission.id),
                db.func.avg(HomeworkSubmission.score)
            ).select_from(Homework).outerjoin(
                HomeworkSubmission, Homework.id == HomeworkSubmission.homework_id
            ).filter(Homework.group_id == group_id).first()

            analytics_data = {
                "group_name": group.name,
                "member_count": len(student_ids),
                "average_scores_by_section": {section: score for section, score in avg_scores},
                "homework_completion_rate": (homework_stats[1] / homework_stats[0] * 100) if homework_stats[0] > 0 else 0,
                "average_homework_score": homework_stats[2]
            }

            return jsonify({"success": True, "data": analytics_data})

        @app.route("/api/analytics/exercises/<int:exercise_id>", methods=["GET"])
        @login_required
        def get_exercise_analytics(exercise_id):
            teacher_user_id = session.get('user_id')

            # Authorization: ensure the teacher owns the exercise
            exercise = db.session.query(TeacherExercise).filter_by(id=exercise_id, creator_id=teacher_user_id).first()
            if not exercise:
                return jsonify({"success": False, "error": "Exercise not found or unauthorized"}), 404

            # Get all homework assignments for this exercise
            homework_assignments = db.session.query(Homework).filter_by(exercise_id=exercise.id).all()
            if not homework_assignments:
                return jsonify({"success": True, "data": {
                    "exercise_title": exercise.title,
                    "submission_count": 0,
                    "average_score": 0
                }})

            # Get all submission scores
            homework_ids = [hw.id for hw in homework_assignments]
            scores = db.session.query(HomeworkSubmission.score).filter(HomeworkSubmission.homework_id.in_(homework_ids)).all()
            
            total_submissions = len(scores)
            average_score = sum(s[0] for s in scores) / total_submissions if total_submissions > 0 else 0

            analytics_data = {
                "exercise_title": exercise.title,
                "submission_count": total_submissions,
                "average_score": average_score
            }

            return jsonify({"success": True, "data": analytics_data})

        # @app.route("/webhook", methods=["POST"])
        # async def webhook():
        #     try:
        #         update = Update.de_json(request.get_json(force=True), application.bot)
        #         await application.process_update(update)
        #         return jsonify({"status": "ok"})
        #     except Exception as e:
        #         return jsonify({"status": "error", "error": str(e)}), 500
        # bot create webhook
        def create_flask_webhook_route(app, route='/webhook'):
            """Create a webhook route for the Flask app"""

            @app.route(route, methods=['POST'])
            async def webhook(): # Changed to async def for app.process_update
                if request.method == "POST":
                    try:
                        logger.info(f"Webhook request received: {request.data}")
                        update_data = request.get_json(force=True)
                        logger.info(f"Parsed JSON update: {update_data}")
                        if update_data:
                            # Use the global application object to process the update
                            update = Update.de_json(update_data, application.bot)
                            await application.process_update(update)
                        return "OK"
                    except Exception as e:
                        logger.error(f"Error in webhook: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        return "Error", 500
                return "Hello, this is the webhook endpoint for the IELTS Preparation Bot."

            # Create a route to manually set webhook URL
            @app.route('/set_webhook', methods=['GET'])
            def set_webhook_route(): # Renamed to avoid conflict with the function name
                token = os.environ.get("TELEGRAM_BOT_TOKEN")
                if not token:
                    return jsonify({
                        "success": False,
                        "error": "No bot token available"
                    }), 400

                # Use DOMAIN_URL env as requested
                domain_url = os.environ.get("DOMAIN_URL")
                if not domain_url:
                    return jsonify({
                        "success": False,
                        "error": "DOMAIN_URL environment variable not set. Cannot set webhook."
                    }), 400
                
                webhook_url = f"https://{domain_url}/webhook"

                try:
                    # First delete any existing webhook
                    delete_response = requests.get(
                        f"https://api.telegram.org/bot{token}/deleteWebhook")
                    logger.info(f"Deleted existing webhook: {delete_response.json()}")

                    # Define allowed updates including message_reaction and message_reaction_count
                    allowed_updates = [
                        "message", "edited_message", "channel_post",
                        "edited_channel_post", "inline_query", "chosen_inline_result",
                        "callback_query", "shipping_query", "pre_checkout_query",
                        "poll", "poll_answer", "my_chat_member", "chat_member",
                        "message_reaction", "message_reaction_count"
                    ]
                    allowed_updates_json = json.dumps(allowed_updates)

                    # Then set the new webhook with allowed_updates parameter
                    response = requests.get(
                        f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}&allowed_updates={allowed_updates_json}"
                    )
                    result = response.json()
                    logger.info(f"Set webhook response: {result}")

                    if result.get("ok"):
                        return jsonify({
                            "success": True,
                            "webhook_url": webhook_url,
                            "result": result
                        })
                    else:
                        return jsonify({
                            "success": False,
                            "error": result,
                            "webhook_url": webhook_url
                        }), 400
                except Exception as e:
                    logger.error(f"Error setting webhook: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

        @app.route('/health', methods=['GET'])
        def health_check():
            status = "ok" if bot_status.running else "error"
            return jsonify({"status": status, "bot_status": bot_status._attrs}), 200

        # Error Handlers
        @app.errorhandler(404)
        def not_found(error):
            return jsonify({"success": False, "error": "Not Found"}), 404

        @app.errorhandler(500)
        def internal_error(error):
            import traceback
            logger.error(f"Internal Server Error: {error}\n{traceback.format_exc()}")
            return jsonify({"success": False, "error": "Internal Server Error"}), 500
        
        def initialize_webhook_bot():
            """Initialize the webhook-based Telegram bot"""
            global bot_status

            try:
                # Check for API keys
                telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
                if not telegram_token:
                    bot_status.error = "TELEGRAM_BOT_TOKEN environment variable not set!"
                    logging.error(bot_status.error)
                    return False

                openai_api_key = os.environ.get("OPENAI_API_KEY")
                if not openai_api_key:
                    bot_status.error = "OPENAI_API_KEY environment variable not set!"
                    logging.error(bot_status.error)
                    return False

                # Import and setup the simple webhook bot (already done globally earlier)
                from telegram import Bot

                # Update status
                bot_status.running = True
                bot_status.start_time = time.time()
                bot_status.error = None

                # Get the bot username and instance
                # Using the existing `application.bot` from global scope
                bot_user = asyncio.run(application.bot.get_me())
                if bot_user:
                    bot_status.telegram_bot_username = f"https://t.me/{bot_user.username}"
                    bot_status.instance_id = bot_user.id
                    bot_status.bot_instance = application.bot
                else:
                    bot_status.telegram_bot_username = "https://t.me/bot_username"

                # Set up the webhook automatically (if DOMAIN_URL is available)
                try:
                    domain_url = os.environ.get("DOMAIN_URL")
                    if domain_url:
                        webhook_url = f"https://{domain_url}/webhook"

                        # Delete any existing webhook (optional, but good for cleanup)
                        requests.get(f"https://api.telegram.org/bot{telegram_token}/deleteWebhook")

                        # Define allowed updates (as per API_REFERENCE.md)
                        allowed_updates = [
                            "message", "edited_message", "channel_post",
                            "edited_channel_post", "inline_query", "chosen_inline_result",
                            "callback_query", "shipping_query", "pre_checkout_query",
                            "poll", "poll_answer", "my_chat_member", "chat_member",
                            "message_reaction", "message_reaction_count"
                        ]
                        allowed_updates_json = json.dumps(allowed_updates)

                        set_response = requests.get(
                            f"https://api.telegram.org/bot{telegram_token}/setWebhook?url={webhook_url}&allowed_updates={allowed_updates_json}"
                        )
                        result = set_response.json()

                        if result.get("ok"):
                            logging.info(f"Webhook set successfully: {webhook_url}")
                            bot_status.webhook_url = webhook_url
                        else:
                            logging.error(f"Failed to set webhook: {result}")
                            bot_status.error = f"Failed to set webhook: {result}"
                    else:
                        logging.warning("DOMAIN_URL not found. Webhook will not be set automatically.")
                except Exception as e:
                    logging.error(f"Error setting up webhook: {e}")
                    # Don\'t fail the bot initialization if webhook setup fails
                    # It can be set up manually later via /set_webhook endpoint

                return True
            except Exception as e:
                bot_status.running = False
                bot_status.error = str(e)
                logging.error(f"Bot initialization error: {e}")
                return False

    def remove_webhook():
        """Remove the webhook"""
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            return False

        try:
            import requests
            response = requests.get(
                f"https://api.telegram.org/bot{token}/deleteWebhook")
            if not response.ok:
                logging.error(f"Failed to delete webhook: {response.text}")
                return False
            return True
        except Exception as e:
            logging.error(f"Error deleting webhook: {e}")
            return False

    initialize_webhook_bot()
    return app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
# if __name__ == '__main__':
#     # The bot polling and Flask app running are mutually exclusive in this script.
#     # For production, you'd run the Flask app with a WSGI server (like Gunicorn)
#     # and set up the Telegram webhook to point to your server's /webhook endpoint.
#     # You would not run application.run_polling().
    
#     # To run the bot with polling for development (without web interface):
#     # import asyncio
#     # asyncio.run(application.run_polling())
    
#     # To run the Flask app for development (for web interface):
#     app.run(port=5000) 