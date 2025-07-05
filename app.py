import os
import logging
import json
from datetime import timedelta
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from bot import setup_bot, get_application, process_update, set_webhook
from config import config
from extensions import db, migrate
from models.user import User
from models.teacher import Teacher
from models.group import Group, GroupMembership
from models.exercise import TeacherExercise
from models.homework import Homework, HomeworkSubmission
from services.auth_service import AuthService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize bot
    with app.app_context():
        setup_bot()

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize CSRF protection
    CSRFProtect(app)

    with app.app_context():
        # Import models and register routes within the app context
        # This ensures they have access to the app and its configurations

        # WEB INTERFACE ROUTES
        @app.route('/')
        def landing():
            if 'teacher_id' in session:
                return redirect(url_for('dashboard'))
            return render_template('landing.html')

        @app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                token = request.form.get('api_token')
                teacher_user = AuthService.validate_token(token)
                if teacher_user:
                    session['user_id'] = teacher_user.id
                    teacher = Teacher.query.filter_by(user_id=teacher_user.id).first()
                    if teacher:
                        session['teacher_id'] = teacher.id
                        return redirect(url_for('dashboard'))
                return render_template('login.html', error="Invalid API token")
            return render_template('login.html')

        @app.route('/logout')
        def logout():
            session.clear()
            return redirect(url_for('landing'))

        @app.route('/dashboard')
        def dashboard():
            if 'teacher_id' not in session:
                return redirect(url_for('login'))
            return render_template('dashboard.html')
        
        @app.route('/group/<int:group_id>')
        def group_details(group_id):
            if 'teacher_id' not in session:
                return redirect(url_for('login'))
            # In a real app, you'd fetch group data here
            return render_template('group_details.html', group_id=group_id)

        @app.route('/student/<int:student_id>')
        def student_details(student_id):
            if 'teacher_id' not in session:
                return redirect(url_for('login'))
            return render_template('student_details.html', student_id=student_id)

        @app.route('/homework')
        def homework_page():
            if 'teacher_id' not in session:
                return redirect(url_for('login'))
            return render_template('homework.html')

        # API ROUTES
        @app.route('/api/auth/login', methods=['POST'])
        def api_login():
            data = request.json
            token = data.get('api_token')
            teacher_user = AuthService.validate_token(token)
            if teacher_user:
                session['user_id'] = teacher_user.id
                teacher = Teacher.query.filter_by(user_id=teacher_user.id).first()
                if teacher:
                    session['teacher_id'] = teacher.id
                    return jsonify({"success": True, "message": "Login successful"})
            return jsonify({"success": False, "error": "Invalid API token"}), 401

        @app.route('/api/groups', methods=['GET', 'POST'])
        def handle_groups():
            if 'teacher_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401

            teacher_id = session['teacher_id']
            teacher = Teacher.query.get(teacher_id)
            if not teacher:
                return jsonify({"success": False, "error": "Teacher not found"}), 404
            
            user_id = teacher.user_id

            if request.method == 'POST':
                data = request.json
                name = data.get('name')
                description = data.get('description')
                if not name:
                    return jsonify({"success": False, "error": "Group name is required"}), 400
                
                new_group = Group(name=name, description=description, teacher_id=user_id)
                db.session.add(new_group)
                db.session.commit()
                return jsonify({"success": True, "data": new_group.to_dict()}), 201

            groups = Group.query.filter_by(teacher_id=user_id).all()
            return jsonify({"success": True, "data": [group.to_dict() for group in groups]})

        @app.route('/api/groups/<int:group_id>', methods=['GET', 'PUT'])
        def handle_specific_group(group_id):
            if 'teacher_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
            
            teacher = Teacher.query.get(session['teacher_id'])
            group = Group.query.filter_by(id=group_id, teacher_id=teacher.user_id).first()
            if not group:
                return jsonify({"success": False, "error": "Group not found or not owned by teacher"}), 404

            if request.method == 'GET':
                return jsonify({"success": True, "data": group.to_dict(include_members=True)})

            if request.method == 'PUT':
                data = request.json
                group.name = data.get('name', group.name)
                group.description = data.get('description', group.description)
                db.session.commit()
                return jsonify({"success": True, "data": group.to_dict()})

        @app.route('/api/groups/<int:group_id>/members', methods=['POST'])
        def add_group_member(group_id):
            if 'teacher_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401

            teacher = Teacher.query.get(session['teacher_id'])
            group = Group.query.filter_by(id=group_id, teacher_id=teacher.user_id).first()
            if not group:
                return jsonify({"success": False, "error": "Group not found"}), 404
            
            data = request.json
            student_user_id = data.get('student_user_id')
            student = User.query.filter_by(user_id=student_user_id).first()

            if not student:
                return jsonify({"success": False, "error": "Student not found"}), 404
            
            existing_membership = GroupMembership.query.filter_by(group_id=group.id, student_id=student.id).first()
            if existing_membership:
                return jsonify({"success": False, "error": "Student already in group"}), 400

            membership = GroupMembership(group_id=group.id, student_id=student.id)
            db.session.add(membership)
            db.session.commit()

            return jsonify({"success": True, "message": "Member added"})
        
        @app.route('/api/groups/<int:group_id>/members/<int:student_id>', methods=['DELETE'])
        def remove_group_member(group_id, student_id):
            if 'teacher_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401

            teacher = Teacher.query.get(session['teacher_id'])
            group = Group.query.filter_by(id=group_id, teacher_id=teacher.user_id).first()
            if not group:
                return jsonify({"success": False, "error": "Group not found"}), 404
            
            membership = GroupMembership.query.filter_by(group_id=group.id, student_id=student_id).first()
            if not membership:
                return jsonify({"success": False, "error": "Student not in group"}), 404

            db.session.delete(membership)
            db.session.commit()

            return jsonify({"success": True, "message": "Member removed"})

        @app.route('/api/exercises', methods=['GET', 'POST'])
        def handle_exercises():
            if 'user_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
            
            user_id = session['user_id']

            if request.method == 'POST':
                data = request.json
                new_exercise = TeacherExercise(
                    creator_id=user_id,
                    title=data.get('title'),
                    description=data.get('description'),
                    exercise_type=data.get('type'),
                    content=data.get('content'),
                    difficulty=data.get('difficulty')
                )
                db.session.add(new_exercise)
                db.session.commit()
                return jsonify({"success": True, "data": new_exercise.to_dict()}), 201

            exercises = TeacherExercise.query.filter_by(creator_id=user_id).all()
            return jsonify({"success": True, "data": [ex.to_dict() for ex in exercises]})
        
        @app.route('/api/exercises/<int:exercise_id>', methods=['GET', 'PUT'])
        def handle_specific_exercise(exercise_id):
            if 'user_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
            
            exercise = TeacherExercise.query.filter_by(id=exercise_id, creator_id=session['user_id']).first()
            if not exercise:
                return jsonify({"success": False, "error": "Exercise not found or not owned by user"}), 404

            if request.method == 'GET':
                return jsonify({"success": True, "data": exercise.to_dict()})

            if request.method == 'PUT':
                data = request.json
                exercise.title = data.get('title', exercise.title)
                exercise.description = data.get('description', exercise.description)
                exercise.content = data.get('content', exercise.content)
                db.session.commit()
                return jsonify({"success": True, "data": exercise.to_dict()})

        @app.route('/api/exercises/<int:exercise_id>/publish', methods=['POST'])
        def publish_exercise(exercise_id):
            if 'user_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
            
            exercise = TeacherExercise.query.filter_by(id=exercise_id, creator_id=session['user_id']).first()
            if not exercise:
                return jsonify({"success": False, "error": "Exercise not found or not owned by user"}), 404
            
            exercise.is_published = True
            db.session.commit()
            return jsonify({"success": True, "message": "Exercise published"})

        @app.route('/api/students/<int:student_id>', methods=['GET'])
        def get_student_details(student_id):
            if 'teacher_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
            
            teacher = Teacher.query.get(session['teacher_id'])
            student = User.query.get(student_id)
            if not student or not AuthService.is_teacher_authorized_for_student(teacher.user_id, student.id):
                 return jsonify({"success": False, "error": "Student not found or access denied"}), 404

            return jsonify({"success": True, "data": student.to_dict(include_stats=True)})

        @app.route('/api/students/<int:student_id>/progress', methods=['GET'])
        def get_student_progress(student_id):
            if 'teacher_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401

            teacher = Teacher.query.get(session['teacher_id'])
            student = User.query.get(student_id)
            if not student or not AuthService.is_teacher_authorized_for_student(teacher.user_id, student.id):
                return jsonify({"success": False, "error": "Student not found or access denied"}), 404

            # This is a placeholder for a more complex progress aggregation logic
            progress_data = {
                "overall_skill": student.skill_level,
                "stats": student.stats,
            }
            return jsonify({"success": True, "data": progress_data})

        @app.route('/api/homework', methods=['GET', 'POST'])
        def handle_homework():
            if 'teacher_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
            
            teacher = Teacher.query.get(session['teacher_id'])
            
            if request.method == 'POST':
                data = request.json
                homework = Homework(
                    exercise_id=data.get('exercise_id'),
                    group_id=data.get('group_id'),
                    assigned_by=teacher.user_id,
                    due_date=data.get('due_date'), # Assuming ISO format string
                    instructions=data.get('instructions')
                )
                db.session.add(homework)
                db.session.commit()
                return jsonify({"success": True, "data": homework.to_dict()}), 201

            homework_assignments = Homework.query.filter_by(assigned_by=teacher.user_id).all()
            return jsonify({"success": True, "data": [h.to_dict() for h in homework_assignments]})
        
        @app.route('/api/homework/<int:homework_id>/submissions')
        def get_homework_submissions(homework_id):
            if 'teacher_id' not in session:
                return jsonify({"success": False, "error": "Unauthorized"}), 401
            
            teacher = Teacher.query.get(session['teacher_id'])
            homework = Homework.query.filter_by(id=homework_id, assigned_by=teacher.user_id).first()
            if not homework:
                return jsonify({"success": False, "error": "Homework not found"}), 404

            submissions = HomeworkSubmission.query.filter_by(homework_id=homework.id).all()
            return jsonify({"success": True, "data": [s.to_dict() for s in submissions]})

        @app.route('/api/analytics/groups/<int:group_id>')
        def get_group_analytics(group_id):
            # Placeholder for analytics logic
            return jsonify({"success": True, "data": {"message": "Analytics for group " + str(group_id)}})

        @app.route('/api/analytics/exercises/<int:exercise_id>')
        def get_exercise_analytics(exercise_id):
            # Placeholder for analytics logic
            return jsonify({"success": True, "data": {"message": "Analytics for exercise " + str(exercise_id)}})

        # BOT WEBHOOK ROUTES
        @app.route("/webhook", methods=["POST"])
        async def webhook():
            try:
                update_data = request.get_json(force=True)
                await process_update(update_data)
                return jsonify({"status": "ok"})
            except Exception as e:
                logger.error(f"Error in webhook: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return jsonify({"status": "error", "error": str(e)}), 500
        
        @app.route('/set_webhook', methods=['GET'])
        def set_webhook_route():
            success, result = set_webhook()
            if success:
                return jsonify({
                    "success": True,
                    "result": result
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result,
                }), 400

        @app.route('/health', methods=['GET'])
        def health_check():
            application = get_application()
            status = "ok" if application else "error"
            return jsonify({"status": status}), 200

        # ERROR HANDLERS
        @app.errorhandler(404)
        def not_found_error(error):
            return jsonify({"success": False, "error": "Not Found"}), 404

        @app.errorhandler(500)
        def internal_error(error):
            import traceback
            logger.error(f"Internal Server Error: {error}\n{traceback.format_exc()}")
            return jsonify({"success": False, "error": "Internal Server Error"}), 500

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