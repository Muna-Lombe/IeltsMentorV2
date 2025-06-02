# IELTS Preparation Bot - Deployment Guide

## Prerequisites

### System Requirements
- Python 3.11+
- PostgreSQL 12+
- Redis (optional, for caching)
- SSL certificate for webhook endpoints
- Domain name for web interface

### Required API Keys and Tokens
- Telegram Bot Token (from @BotFather)
- OpenAI API Key (for AI features)
- Database connection credentials

## Environment Setup

### Environment Variables
Create a `.env` file with the following variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database_name
PGHOST=localhost
PGPORT=5432
PGUSER=ielts_bot
PGPASSWORD=secure_password
PGDATABASE=ielts_preparation

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://yourdomain.com/webhook

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Flask Configuration
FLASK_SECRET_KEY=your_secure_secret_key
SESSION_SECRET=your_session_secret_key
FLASK_ENV=production

# Security Configuration
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ORIGINS=https://yourdomain.com

# Optional: Redis Configuration
REDIS_URL=redis://localhost:6379/0
```

### Database Setup

#### PostgreSQL Installation and Configuration
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE USER ielts_bot WITH PASSWORD 'secure_password';
CREATE DATABASE ielts_preparation OWNER ielts_bot;
GRANT ALL PRIVILEGES ON DATABASE ielts_preparation TO ielts_bot;
\q
```

#### Database Migration
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
python migrations.py

# Verify database setup
python -c "from models import db; print('Database connection successful')"
```

## Local Development Setup

### Virtual Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Development Server
```bash
# Set development environment
export FLASK_ENV=development
export FLASK_DEBUG=1

# Run development server
python main.py

# Alternative: Use Gunicorn for production-like testing
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

### Telegram Bot Setup for Development
```bash
# Set webhook for development (using ngrok)
ngrok http 5000

# Set webhook URL
curl -X POST "https://api.telegram.org/bot{YOUR_BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-ngrok-url.ngrok.io/webhook"}'
```

## Production Deployment

### Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--worker-class", "sync", "--timeout", "120", "main:app"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://ielts_bot:password@db:5432/ielts_preparation
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=ielts_preparation
      - POSTGRES_USER=ielts_bot
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Cloud Platform Deployment

#### Heroku Deployment
```bash
# Install Heroku CLI and login
heroku login

# Create Heroku app
heroku create your-ielts-bot

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:standard-0

# Set environment variables
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set OPENAI_API_KEY=your_key
heroku config:set FLASK_SECRET_KEY=your_secret

# Deploy application
git push heroku main

# Run database migrations
heroku run python migrations.py

# Set webhook
heroku config:set WEBHOOK_URL=https://your-ielts-bot.herokuapp.com/webhook
```

#### AWS ECS Deployment
```bash
# Build and push Docker image
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-west-2.amazonaws.com

docker build -t ielts-bot .
docker tag ielts-bot:latest your-account.dkr.ecr.us-west-2.amazonaws.com/ielts-bot:latest
docker push your-account.dkr.ecr.us-west-2.amazonaws.com/ielts-bot:latest

# Deploy using ECS task definition
aws ecs create-service --cluster ielts-cluster --service-name ielts-bot-service --task-definition ielts-bot-task --desired-count 2
```

### Server Configuration

#### Nginx Configuration
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=webhook:10m rate=100r/s;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /webhook {
        limit_req zone=webhook burst=50 nodelay;
        proxy_pass http://127.0.0.1:5000/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### Systemd Service
```ini
[Unit]
Description=IELTS Preparation Bot
After=network.target postgresql.service

[Service]
Type=exec
User=app
Group=app
WorkingDirectory=/app
Environment=PATH=/app/venv/bin
ExecStart=/app/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 main:app
Restart=always
RestartSec=10

# Security
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/app/logs /app/uploads

[Install]
WantedBy=multi-user.target
```

## Monitoring and Maintenance

### Health Checks
```python
# Add to main.py
@app.route('/health')
def health_check():
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check external services
        response = requests.get('https://api.openai.com/v1/models', 
                              headers={'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'}, 
                              timeout=5)
        
        return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500
```

### Logging Configuration
```python
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### Backup Strategy
```bash
#!/bin/bash
# backup.sh - Database backup script

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="ielts_bot_backup_${TIMESTAMP}.sql"

# Create backup
pg_dump $DATABASE_URL > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

# Remove backups older than 30 days
find $BACKUP_DIR -name "ielts_bot_backup_*.sql.gz" -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 cp "$BACKUP_DIR/$BACKUP_FILE.gz" s3://your-backup-bucket/
```

### Performance Monitoring
```bash
# Monitor application performance
htop
iostat -x 1
netstat -tulpn

# Monitor database performance
sudo -u postgres psql -d ielts_preparation -c "SELECT * FROM pg_stat_activity;"

# Monitor logs
tail -f logs/app.log
journalctl -u ielts-bot -f
```

## Security Considerations

### SSL/TLS Configuration
- Use Let's Encrypt for free SSL certificates
- Implement HTTP Strict Transport Security (HSTS)
- Configure secure cipher suites
- Enable certificate transparency monitoring

### Firewall Configuration
```bash
# UFW firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Regular Security Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Python dependencies
pip list --outdated
pip install --upgrade package_name

# Security audit
pip-audit
```

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database connectivity
psql $DATABASE_URL -c "SELECT version();"

# Check database logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

#### Webhook Issues
```bash
# Check webhook status
curl -X GET "https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"

# Reset webhook
curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
curl -X POST "https://api.telegram.org/bot{BOT_TOKEN}/setWebhook" -d "url=https://yourdomain.com/webhook"
```

#### Performance Issues
```bash
# Monitor resource usage
docker stats
docker logs container_name

# Check application metrics
curl http://localhost:5000/health
```

This deployment guide provides comprehensive instructions for setting up the IELTS Preparation Bot in various environments, from local development to production deployment with monitoring and security considerations.