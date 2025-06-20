import os
import logging
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

    # Import models and register routes within the app context
    with app.app_context():
        @app.route("/")
        def index():
            return "Hello, IELTS Prep Bot is alive! Flask is running."
        
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
            user_first_name = session.get('user_first_name', 'Teacher')
            return render_template("dashboard.html", user={'first_name': user_first_name})

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
                return jsonify({"success": False, "error": "Exercise not found or you are not authorized"}), 404

            data = request.json
            exercise.title = data.get('title', exercise.title)
            exercise.description = data.get('description', exercise.description)
            exercise.exercise_type = data.get('exercise_type', exercise.exercise_type)
            exercise.difficulty = data.get('difficulty', exercise.difficulty)
            exercise.content = data.get('content', exercise.content)
            exercise.is_published = data.get('is_published', exercise.is_published)
            
            db.session.commit()

            return jsonify({"success": True, "message": "Exercise updated successfully"})

        @app.route("/webhook", methods=["POST"])
        async def webhook():
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
            return jsonify({"status": "ok"})

        @app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({"status": "ok"}), 200

        # Error Handlers
        @app.errorhandler(404)
        def not_found(error):
            return jsonify({"success": False, "error": "Not Found"}), 404

        @app.errorhandler(500)
        def internal_error(error):
            return jsonify({"success": False, "error": "Internal Server Error"}), 500

    return app

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    # The bot polling and Flask app running are mutually exclusive in this script.
    # For production, you'd run the Flask app with a WSGI server (like Gunicorn)
    # and set up the Telegram webhook to point to your server's /webhook endpoint.
    # You would not run application.run_polling().
    
    # To run the bot with polling for development (without web interface):
    # import asyncio
    # asyncio.run(application.run_polling())
    
    # To run the Flask app for development (for web interface):
    app.run(port=5000) 