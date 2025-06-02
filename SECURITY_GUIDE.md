# IELTS Preparation Bot - Security Guide

## Security Architecture Overview

The IELTS Preparation Bot implements a multi-layered security framework designed to protect user data, prevent unauthorized access, and ensure safe operation in educational environments.

## Authentication & Authorization

### Role-Based Access Control (RBAC)

#### User Roles
1. **Students**: Basic users with access to practice exercises and progress tracking
2. **Teachers**: Elevated privileges for group management, exercise creation, and student monitoring
3. **Botmasters**: Administrative access to system configuration and teacher approval

#### Permission Matrix
| Feature | Student | Teacher | Botmaster |
|---------|---------|---------|-----------|
| Practice Exercises | ✓ | ✓ | ✓ |
| Progress Viewing | Own Only | Own + Students | All |
| Group Creation | ✗ | ✓ | ✓ |
| Exercise Creation | ✗ | ✓ | ✓ |
| User Management | ✗ | Students Only | All |
| System Configuration | ✗ | ✗ | ✓ |

### Authentication Implementation

#### API Token System for Teachers
```python
class AuthService:
    @staticmethod
    def generate_api_token():
        """Generate secure API token for teacher authentication"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_token(token):
        """Validate API token and return associated user"""
        teacher = Teacher.query.filter_by(api_token=token).first()
        if teacher and teacher.is_approved:
            return User.query.get(teacher.user_id)
        return None
```

#### Session Management
```python
# Secure session configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)
```

## Input Validation & Sanitization

### User Input Validation
```python
class InputValidator:
    @staticmethod
    def validate_user_id(user_id):
        """Validate Telegram user ID format and range"""
        if not isinstance(user_id, int):
            return None
        if user_id < 1 or user_id > 2147483647:  # Valid Telegram ID range
            return None
        return user_id
    
    @staticmethod
    def sanitize_text_input(text, max_length=1000):
        """Sanitize text input for database storage"""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove potentially dangerous characters
        cleaned = re.sub(r'[<>"\']', '', text)
        # Limit length
        return cleaned[:max_length].strip()
    
    @staticmethod
    def validate_exercise_content(content):
        """Validate exercise content structure"""
        if not isinstance(content, dict):
            return False
        
        required_fields = ['questions']
        for field in required_fields:
            if field not in content:
                return False
        
        # Validate questions structure
        questions = content.get('questions', [])
        if not isinstance(questions, list):
            return False
        
        for question in questions:
            if not isinstance(question, dict):
                return False
            if 'text' not in question:
                return False
        
        return True
```

### SQL Injection Prevention
```python
# CORRECT: Using ORM with parameterized queries
user = User.query.filter_by(user_id=user_id).first()

# CORRECT: Using text() with bound parameters
result = db.session.execute(
    text("SELECT * FROM users WHERE user_id = :user_id"),
    {"user_id": user_id}
)

# DANGEROUS: Never use string concatenation
# query = f"SELECT * FROM users WHERE user_id = {user_id}"
```

## Data Protection

### Sensitive Data Handling
```python
class DataProtection:
    @staticmethod
    def hash_sensitive_data(data):
        """Hash sensitive data using secure algorithms"""
        salt = os.urandom(32)
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                     data.encode('utf-8'), 
                                     salt, 
                                     100000)
        return salt + pwdhash
    
    @staticmethod
    def verify_sensitive_data(stored_data, provided_data):
        """Verify hashed sensitive data"""
        salt = stored_data[:32]
        stored_hash = stored_data[32:]
        pwdhash = hashlib.pbkdf2_hmac('sha256',
                                     provided_data.encode('utf-8'),
                                     salt,
                                     100000)
        return pwdhash == stored_hash
```

### Personal Information Protection
- **Minimal Data Collection**: Only collect necessary information for functionality
- **Data Anonymization**: Remove personal identifiers from analytics data
- **Secure Storage**: Encrypt sensitive data at rest
- **Access Logging**: Track all access to personal information

## API Security

### Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

# Apply specific limits to sensitive endpoints
@app.route('/api/exercises', methods=['POST'])
@limiter.limit("10 per minute")
def create_exercise():
    # Exercise creation logic
    pass

@app.route('/webhook', methods=['POST'])
@limiter.limit("1000 per minute")
def webhook():
    # Webhook processing
    pass
```

### Request Validation
```python
def validate_webhook_request(request):
    """Validate incoming webhook requests from Telegram"""
    # Verify request is from Telegram
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        return False
    
    # Check request signature if available
    signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    expected_signature = os.getenv('WEBHOOK_SECRET_TOKEN')
    
    if expected_signature and signature != expected_signature:
        return False
    
    return True
```

### CORS Configuration
```python
from flask_cors import CORS

CORS(app, 
     origins=['https://yourdomain.com'],
     methods=['GET', 'POST'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)
```

## Database Security

### Connection Security
```python
# Secure database connection configuration
DATABASE_CONFIG = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'connect_args': {
        'sslmode': 'require',
        'sslcert': '/path/to/client-cert.pem',
        'sslkey': '/path/to/client-key.pem',
        'sslrootcert': '/path/to/ca-cert.pem'
    }
}
```

### Query Security
```python
class SecureQueries:
    @staticmethod
    def get_user_exercises(user_id, limit=20):
        """Secure query for user exercises with proper authorization"""
        # Validate user_id
        user_id = InputValidator.validate_user_id(user_id)
        if not user_id:
            raise ValueError("Invalid user ID")
        
        # Check user exists and has permissions
        user = User.query.filter_by(user_id=user_id).first()
        if not user or not user.is_admin:
            raise PermissionError("User not authorized for this operation")
        
        # Secure query with limits
        return TeacherExercise.query.filter_by(
            creator_id=user.id
        ).order_by(
            TeacherExercise.created_at.desc()
        ).limit(limit).all()
```

### Data Backup Security
```bash
#!/bin/bash
# secure_backup.sh
set -e

BACKUP_DIR="/secure/backups"
ENCRYPTION_KEY="/secure/keys/backup.key"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create encrypted backup
pg_dump $DATABASE_URL | \
gpg --symmetric --cipher-algo AES256 \
    --passphrase-file $ENCRYPTION_KEY \
    --output "$BACKUP_DIR/backup_${TIMESTAMP}.sql.gpg"

# Set secure permissions
chmod 600 "$BACKUP_DIR/backup_${TIMESTAMP}.sql.gpg"

# Verify backup integrity
gpg --quiet --batch --decrypt \
    --passphrase-file $ENCRYPTION_KEY \
    "$BACKUP_DIR/backup_${TIMESTAMP}.sql.gpg" | \
head -n 1 | grep -q "PostgreSQL database dump"

echo "Secure backup created: backup_${TIMESTAMP}.sql.gpg"
```

## Security Monitoring

### Audit Logging
```python
class SecurityLogger:
    @staticmethod
    def log_authentication_attempt(user_id, success, ip_address=None):
        """Log authentication attempts for security monitoring"""
        logger.warning(f"Auth attempt - User: {user_id}, Success: {success}, IP: {ip_address}")
    
    @staticmethod
    def log_permission_violation(user_id, attempted_action, resource=None):
        """Log unauthorized access attempts"""
        logger.error(f"Permission violation - User: {user_id}, Action: {attempted_action}, Resource: {resource}")
    
    @staticmethod
    def log_suspicious_activity(user_id, activity_type, details):
        """Log potentially suspicious user activity"""
        logger.warning(f"Suspicious activity - User: {user_id}, Type: {activity_type}, Details: {details}")
```

### Intrusion Detection
```python
class IntrusionDetection:
    failed_attempts = {}
    
    @classmethod
    def check_brute_force(cls, user_id, ip_address):
        """Check for brute force attack patterns"""
        key = f"{user_id}:{ip_address}"
        current_time = time.time()
        
        if key not in cls.failed_attempts:
            cls.failed_attempts[key] = []
        
        # Clean old attempts (older than 1 hour)
        cls.failed_attempts[key] = [
            attempt_time for attempt_time in cls.failed_attempts[key]
            if current_time - attempt_time < 3600
        ]
        
        # Check if too many recent failures
        if len(cls.failed_attempts[key]) >= 5:
            SecurityLogger.log_suspicious_activity(
                user_id, 
                "brute_force_attempt", 
                f"IP: {ip_address}, Attempts: {len(cls.failed_attempts[key])}"
            )
            return True
        
        return False
    
    @classmethod
    def record_failed_attempt(cls, user_id, ip_address):
        """Record failed authentication attempt"""
        key = f"{user_id}:{ip_address}"
        if key not in cls.failed_attempts:
            cls.failed_attempts[key] = []
        cls.failed_attempts[key].append(time.time())
```

## Secure Communication

### HTTPS Configuration
```nginx
# Nginx SSL configuration
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL certificates
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/private.key;
    
    # Strong SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";
}
```

### API Key Management
```python
class KeyManager:
    @staticmethod
    def rotate_api_keys():
        """Rotate API keys for enhanced security"""
        new_token = secrets.token_urlsafe(32)
        
        # Update all teacher tokens
        teachers = Teacher.query.filter_by(is_approved=True).all()
        for teacher in teachers:
            old_token = teacher.api_token
            teacher.api_token = new_token
            
            # Log key rotation
            SecurityLogger.log_security_event(
                "api_key_rotation",
                teacher.user_id,
                f"Token rotated from {old_token[:8]}... to {new_token[:8]}..."
            )
        
        db.session.commit()
        return len(teachers)
```

## Incident Response

### Security Incident Handling
```python
class IncidentResponse:
    @staticmethod
    def handle_security_breach(incident_type, details):
        """Handle security incidents with appropriate response"""
        
        # Log incident
        logger.critical(f"SECURITY INCIDENT: {incident_type} - {details}")
        
        # Immediate response based on incident type
        if incident_type == "unauthorized_access":
            # Temporarily disable affected accounts
            pass
        elif incident_type == "data_breach":
            # Initiate data breach protocol
            pass
        elif incident_type == "system_compromise":
            # Emergency system lockdown
            pass
        
        # Notify administrators
        # send_security_alert(incident_type, details)
    
    @staticmethod
    def emergency_lockdown():
        """Emergency system lockdown procedure"""
        # Disable new user registrations
        # Require re-authentication for all users
        # Increase logging verbosity
        # Alert system administrators
        pass
```

## Compliance & Privacy

### GDPR Compliance
```python
class PrivacyCompliance:
    @staticmethod
    def export_user_data(user_id):
        """Export all user data for GDPR compliance"""
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return None
        
        data = {
            'profile': {
                'user_id': user.user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'joined_at': user.joined_at
            },
            'statistics': user.get_stats(),
            'practice_sessions': [
                session.to_dict() for session in 
                PracticeSession.query.filter_by(user_id=user.id).all()
            ]
        }
        
        return data
    
    @staticmethod
    def delete_user_data(user_id):
        """Delete all user data for GDPR compliance"""
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return False
        
        # Delete related data
        PracticeSession.query.filter_by(user_id=user.id).delete()
        HomeworkSubmission.query.filter_by(student_id=user.id).delete()
        
        # Anonymize user record
        user.first_name = "Deleted User"
        user.last_name = ""
        user.username = ""
        user.stats = {}
        
        db.session.commit()
        return True
```

## Security Testing

### Penetration Testing Checklist
1. **Authentication Testing**
   - Test password policies
   - Verify session management
   - Check for authentication bypass

2. **Authorization Testing**
   - Test role-based access controls
   - Verify horizontal privilege escalation
   - Check vertical privilege escalation

3. **Input Validation Testing**
   - SQL injection testing
   - XSS vulnerability testing
   - Command injection testing

4. **Session Management Testing**
   - Session fixation testing
   - Session timeout verification
   - Cross-site request forgery testing

### Security Audit Script
```bash
#!/bin/bash
# security_audit.sh

echo "Starting security audit..."

# Check for common vulnerabilities
echo "Checking file permissions..."
find . -type f -perm 777 2>/dev/null

echo "Checking for hardcoded secrets..."
grep -r "password\|secret\|key" --include="*.py" . | grep -v "example"

echo "Checking SSL configuration..."
curl -I https://yourdomain.com 2>/dev/null | grep -i "strict-transport-security"

echo "Checking database permissions..."
psql $DATABASE_URL -c "\du" 2>/dev/null

echo "Security audit complete."
```

This security guide provides comprehensive protection measures for the IELTS Preparation Bot, ensuring user data safety and system integrity.