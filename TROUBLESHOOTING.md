# IELTS Preparation Bot - Troubleshooting Guide

## Common Issues and Solutions

### Database Issues

#### Connection Errors
**Symptom**: Application fails to start with database connection errors
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**Solutions**:
1. Verify PostgreSQL service is running:
   ```bash
   sudo systemctl status postgresql
   sudo systemctl start postgresql
   ```

2. Check database credentials in environment variables:
   ```bash
   echo $DATABASE_URL
   psql $DATABASE_URL -c "SELECT version();"
   ```

3. Verify database exists and user has permissions:
   ```sql
   -- Connect as postgres user
   sudo -u postgres psql
   \l  -- List databases
   \du -- List users
   ```

#### Schema Mismatch Errors
**Symptom**: AttributeError about missing columns or wrong column names
```
AttributeError: Entity namespace for "teacher_exercises" has no property "created_by_id"
```

**Solutions**:
1. Check actual database schema:
   ```sql
   \d teacher_exercises
   SELECT column_name FROM information_schema.columns WHERE table_name = 'teacher_exercises';
   ```

2. Run pending migrations:
   ```bash
   python migrations.py
   ```

3. Verify model definitions match database schema in `models.py`

#### Migration Failures
**Symptom**: Migration scripts fail to execute
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```

**Solutions**:
1. Reset migration history:
   ```bash
   # Backup database first
   pg_dump $DATABASE_URL > backup.sql
   
   # Reset migrations
   python reset_database.py
   python migrations.py
   ```

2. Manual schema verification:
   ```bash
   python -c "from models import db; db.create_all(); print('Schema created')"
   ```

### Telegram Bot Issues

#### Webhook Configuration Problems
**Symptom**: Bot doesn't respond to messages
```
Error: Webhook not set or returning errors
```

**Solutions**:
1. Check webhook status:
   ```bash
   curl -X GET "https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
   ```

2. Reset webhook:
   ```bash
   # Delete existing webhook
   curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
   
   # Set new webhook
   curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://yourdomain.com/webhook"}'
   ```

3. Verify SSL certificate is valid:
   ```bash
   curl -I https://yourdomain.com/webhook
   ```

#### Permission Errors
**Symptom**: Bot commands fail with permission errors
```
handlers.teacher_handler - ERROR - User lacks admin permission
```

**Solutions**:
1. Check user permissions in database:
   ```sql
   SELECT user_id, is_admin, is_botmaster FROM users WHERE user_id = 123456789;
   ```

2. Update user permissions:
   ```sql
   UPDATE users SET is_admin = true WHERE user_id = 123456789;
   ```

3. Verify teacher approval status:
   ```sql
   SELECT t.*, u.first_name FROM teachers t 
   JOIN users u ON t.user_id = u.id 
   WHERE u.user_id = 123456789;
   ```

#### Message Translation Issues
**Symptom**: Messages appear in wrong language or English fallback
```
Translation key 'practice.welcome' not found for language 'es'
```

**Solutions**:
1. Check translation files exist:
   ```bash
   ls translations/
   cat translations/es.json | grep -A 5 "practice"
   ```

2. Verify language detection:
   ```python
   from utils.translation_system import detect_language
   user_data = {'language_code': 'es'}
   print(detect_language(user_data))
   ```

3. Add missing translation keys:
   ```json
   // In translations/es.json
   {
     "practice": {
       "welcome": "Bienvenido al sistema de práctica"
     }
   }
   ```

### OpenAI Integration Issues

#### API Key Problems
**Symptom**: OpenAI requests fail with authentication errors
```
openai.error.AuthenticationError: Incorrect API key provided
```

**Solutions**:
1. Verify API key is set correctly:
   ```bash
   echo $OPENAI_API_KEY | head -c 20
   ```

2. Test API key manually:
   ```bash
   curl https://api.openai.com/v1/models \
        -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. Check API key permissions and usage limits in OpenAI dashboard

#### Rate Limiting
**Symptom**: API requests fail with rate limit errors
```
openai.error.RateLimitError: Rate limit reached
```

**Solutions**:
1. Implement request queuing in `services/openai_service.py`:
   ```python
   import time
   from functools import wraps
   
   def rate_limit(calls_per_second=1):
       min_interval = 1.0 / calls_per_second
       last_called = [0.0]
       
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               elapsed = time.time() - last_called[0]
               left_to_wait = min_interval - elapsed
               if left_to_wait > 0:
                   time.sleep(left_to_wait)
               ret = func(*args, **kwargs)
               last_called[0] = time.time()
               return ret
           return wrapper
       return decorator
   ```

2. Monitor usage in OpenAI dashboard and upgrade plan if needed

#### Model Availability
**Symptom**: Requests fail due to model unavailability
```
openai.error.InvalidRequestError: The model 'gpt-4o' does not exist
```

**Solutions**:
1. Check available models:
   ```bash
   curl https://api.openai.com/v1/models \
        -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data[].id'
   ```

2. Update model name in configuration:
   ```python
   # In services/openai_service.py
   MODEL_NAME = "gpt-4o"  # Update to available model
   ```

### Performance Issues

#### Slow Response Times
**Symptom**: Bot responds slowly to user interactions
```
Request timeout after 30 seconds
```

**Solutions**:
1. Monitor database query performance:
   ```sql
   -- Enable query logging
   ALTER SYSTEM SET log_statement = 'all';
   SELECT pg_reload_conf();
   
   -- Check slow queries
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 10;
   ```

2. Add database indexes for frequently queried columns:
   ```sql
   CREATE INDEX idx_users_user_id ON users(user_id);
   CREATE INDEX idx_teacher_exercises_creator_id ON teacher_exercises(creator_id);
   ```

3. Implement caching for translation messages:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def get_cached_message(category, key, language):
       return get_message(category, key, language)
   ```

#### Memory Usage Issues
**Symptom**: Application consumes excessive memory
```
MemoryError: Unable to allocate memory
```

**Solutions**:
1. Monitor memory usage:
   ```bash
   ps aux | grep python
   htop
   ```

2. Optimize database queries to fetch only needed data:
   ```python
   # Instead of loading all exercises
   exercises = TeacherExercise.query.all()
   
   # Load with pagination
   exercises = TeacherExercise.query.limit(20).offset(page * 20).all()
   ```

3. Implement proper session cleanup:
   ```python
   try:
       # Database operations
       db.session.commit()
   except Exception as e:
       db.session.rollback()
       raise
   finally:
       db.session.close()
   ```

### Web Interface Issues

#### Authentication Failures
**Symptom**: Teachers cannot log in to web interface
```
Error: Invalid API token
```

**Solutions**:
1. Verify teacher API token:
   ```sql
   SELECT api_token FROM teachers WHERE user_id = (
       SELECT id FROM users WHERE user_id = 123456789
   );
   ```

2. Generate new API token:
   ```python
   from services.auth_service import AuthService
   new_token = AuthService.generate_api_token()
   # Update in database
   ```

3. Check session configuration:
   ```python
   # In app.py
   app.secret_key = os.environ.get("SESSION_SECRET")
   app.config['SESSION_COOKIE_SECURE'] = True  # For HTTPS
   app.config['SESSION_COOKIE_HTTPONLY'] = True
   ```

#### Static File Loading Issues
**Symptom**: CSS/JS files not loading properly
```
404 Not Found: /static/css/style.css
```

**Solutions**:
1. Verify static file configuration:
   ```python
   # In app.py
   app = Flask(__name__, static_folder='static', static_url_path='/static')
   ```

2. Check file permissions:
   ```bash
   ls -la static/
   chmod -R 644 static/
   ```

3. Configure web server to serve static files:
   ```nginx
   location /static/ {
       alias /app/static/;
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

## Debugging Techniques

### Logging Analysis
1. **Enable detailed logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Analyze log patterns**:
   ```bash
   # Check error frequency
   grep -c "ERROR" logs/app.log
   
   # Find specific user issues
   grep "user_id: 123456789" logs/app.log
   
   # Monitor real-time logs
   tail -f logs/app.log | grep ERROR
   ```

### Database Debugging
1. **Query performance analysis**:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM users WHERE user_id = 123456789;
   ```

2. **Connection monitoring**:
   ```sql
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   ```

3. **Lock detection**:
   ```sql
   SELECT * FROM pg_locks WHERE NOT granted;
   ```

### Network Debugging
1. **Test webhook connectivity**:
   ```bash
   curl -X POST https://yourdomain.com/webhook \
        -H "Content-Type: application/json" \
        -d '{"test": "data"}'
   ```

2. **SSL certificate verification**:
   ```bash
   openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
   ```

3. **Network latency testing**:
   ```bash
   ping api.telegram.org
   traceroute api.openai.com
   ```

## Emergency Recovery Procedures

### Database Recovery
1. **Restore from backup**:
   ```bash
   # Stop application
   sudo systemctl stop ielts-bot
   
   # Restore database
   psql $DATABASE_URL < backup.sql
   
   # Restart application
   sudo systemctl start ielts-bot
   ```

2. **Repair corrupted data**:
   ```sql
   -- Check for data consistency
   SELECT COUNT(*) FROM users WHERE user_id IS NULL;
   SELECT COUNT(*) FROM teacher_exercises WHERE creator_id NOT IN (SELECT id FROM users);
   
   -- Clean up orphaned records
   DELETE FROM teacher_exercises WHERE creator_id NOT IN (SELECT id FROM users);
   ```

### Service Recovery
1. **Application restart**:
   ```bash
   sudo systemctl restart ielts-bot
   sudo systemctl status ielts-bot
   ```

2. **Clear cache and temporary files**:
   ```bash
   rm -rf temp_audio/*
   rm -rf __pycache__/
   ```

3. **Reset webhook**:
   ```bash
   curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
   sleep 5
   curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/setWebhook" \
        -d "url=https://yourdomain.com/webhook"
   ```

### Monitoring and Alerts
Set up monitoring to catch issues early:

```bash
# System resource monitoring
#!/bin/bash
# monitor.sh
while true; do
    # Check disk space
    df -h | awk '$5 > 80 {print "Disk usage warning: " $5 " full on " $1}'
    
    # Check memory usage
    free | awk 'NR==2{printf "Memory usage: %.2f%%\n", $3*100/$2}'
    
    # Check application status
    if ! pgrep -f "gunicorn.*main:app" > /dev/null; then
        echo "Application not running!"
    fi
    
    sleep 300  # Check every 5 minutes
done
```

This troubleshooting guide covers the most common issues encountered with the IELTS Preparation Bot and provides systematic approaches to diagnosing and resolving them.