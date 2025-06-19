import os
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from functools import wraps
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

# Register callback query handlers
# The practice_section_callback is no longer needed as each practice type
# is now a ConversationHandler triggered by its own callback pattern.

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
        from models.user import User
        from models.practice_session import PracticeSession
        from models.group import Group
        from models.exercise import TeacherExercise

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
            # The actual data will be fetched by JS, this just renders the page
            return render_template("group_details.html", group_id=group_id)

        # API Endpoints
        @app.route("/api/groups", methods=["GET"])
        @login_required
        def get_groups():
            teacher_user_id = session.get('user_id')
            teacher = db.session.query(User).filter_by(id=teacher_user_id).first()
            
            if not teacher or not teacher.teacher_profile:
                return jsonify({"success": False, "error": "Teacher profile not found"}), 404

            groups = teacher.teacher_profile.groups
            groups_data = [{"id": group.id, "name": group.name, "description": group.description} for group in groups]
            
            return jsonify({"success": True, "data": groups_data})

        @app.route("/api/groups", methods=["POST"])
        @login_required
        def create_group():
            teacher_user_id = session.get('user_id')
            teacher = db.session.query(User).filter_by(id=teacher_user_id).first()

            if not teacher or not teacher.teacher_profile:
                return jsonify({"success": False, "error": "Teacher profile not found"}), 404

            data = request.json
            name = data.get('name')
            description = data.get('description')

            if not name:
                return jsonify({"success": False, "error": "Group name is required"}), 400

            new_group = Group(
                name=name,
                description=description,
                teacher_id=teacher.id
            )
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

            return jsonify({
                "success": True,
                "data": {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description
                }
            })

        @app.route("/api/groups/<int:group_id>", methods=["PUT"])
        @login_required
        def update_group(group_id):
            teacher_user_id = session.get('user_id')
            group = db.session.query(Group).filter_by(id=group_id).first()

            if not group:
                return jsonify({"success": False, "error": "Group not found"}), 404

            if group.teacher_id != teacher_user_id:
                return jsonify({"success": False, "error": "Unauthorized"}), 403

            data = request.json
            group.name = data.get('name', group.name)
            group.description = data.get('description', group.description)
            db.session.commit()

            return jsonify({"success": True, "data": {"id": group.id, "name": group.name, "description": group.description}})

        @app.route("/api/exercises", methods=["GET"])
        @login_required
        def get_exercises():
            teacher_user_id = session.get('user_id')
            
            exercises = db.session.query(TeacherExercise).filter_by(creator_id=teacher_user_id).all()
            
            exercises_data = [
                {
                    "id": ex.id, 
                    "title": ex.title, 
                    "description": ex.description,
                    "exercise_type": ex.exercise_type,
                    "difficulty": ex.difficulty,
                    "is_published": ex.is_published
                } for ex in exercises
            ]
            
            return jsonify({"success": True, "data": exercises_data})

        @app.route("/api/exercises", methods=["POST"])
        @login_required
        def create_exercise():
            teacher_user_id = session.get('user_id')
            data = request.json

            # Basic validation
            required_fields = ['title', 'description', 'exercise_type', 'difficulty', 'content']
            if not all(field in data for field in required_fields):
                return jsonify({"success": False, "error": "Missing required fields"}), 400

            new_exercise = TeacherExercise(
                creator_id=teacher_user_id,
                title=data['title'],
                description=data['description'],
                exercise_type=data['exercise_type'],
                difficulty=data['difficulty'],
                content=data['content'] # Assuming content is a valid JSON object
            )
            db.session.add(new_exercise)
            db.session.commit()

            return jsonify({
                "success": True, 
                "data": {
                    "id": new_exercise.id,
                    "title": new_exercise.title,
                    "description": new_exercise.description
                }
            }), 201

        @app.route("/webhook", methods=["POST"])
        async def webhook():
            """Webhook endpoint to receive updates from Telegram."""
            if request.is_json:
                update_data = request.get_json()
                update = Update.de_json(update_data, application.bot)
                await application.process_update(update)
                return jsonify(status="ok")
            else:
                return jsonify(status="bad request", error="Request must be JSON"), 400
            
    return app

# The flask command will now call create_app
app = create_app()

# ... (rest of your Telegram bot setup) ... 