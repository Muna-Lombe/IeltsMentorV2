# IELTS Preparation Bot - Development Rules & Guidelines

## Core Development Principles

### 1. Database Integrity Rules

#### Schema Consistency
- **Always use actual column names**: Match database schema exactly (e.g., `creator_id` not `created_by_id`)
- **Foreign Key Validation**: Verify FK relationships before deployment
- **Migration Strategy**: Use ORM migrations, never manual SQL schema changes
- **Backup Before Changes**: Always backup database before major schema modifications

#### Data Safety
- **No Destructive Operations**: Avoid DELETE/UPDATE without explicit user confirmation
- **Transaction Wrapping**: Use database transactions for multi-step operations
- **Constraint Validation**: Ensure all database constraints are properly defined
- **Rollback Capability**: Design operations to be reversible

### 2. Security Framework Rules

#### Authentication & Authorization
- **Role-Based Access Control**: Implement proper permission checks for all operations
- **Input Validation**: Sanitize and validate all user inputs before processing
- **SQL Injection Prevention**: Use parameterized queries exclusively
- **API Token Security**: Implement secure token generation and validation

#### Data Protection
- **Sensitive Data Handling**: Encrypt passwords and personal information
- **Audit Logging**: Log all security-relevant operations
- **Rate Limiting**: Implement protection against abuse and spam
- **Error Information**: Never expose internal system details in error messages

### 3. Translation System Rules

#### Message Standardization
- **Template Usage**: Always use translation templates for user-facing messages
- **Language Detection**: Implement automatic language detection for new users
- **Fallback Mechanisms**: Provide English fallback for missing translations
- **Dynamic Content**: Use template variables for dynamic message content

#### Implementation Standards
```python
# CORRECT: Use translation system
message = get_message('practice', 'session_complete', user_language, score=user_score)

# INCORRECT: Hardcoded English text
message = f"Practice session complete! Your score: {user_score}"
```

### 4. Error Handling Rules

#### Comprehensive Error Management
- **Safe Handlers**: Wrap all bot handlers with error catching decorators
- **User-Friendly Messages**: Provide clear, actionable error messages
- **Logging Requirements**: Log all errors with context and user information
- **Graceful Degradation**: Ensure system continues functioning despite partial failures

#### Error Recovery
- **Retry Mechanisms**: Implement automatic retry for transient failures
- **Fallback Options**: Provide alternative paths when primary systems fail
- **State Preservation**: Maintain user state during error conditions
- **Clear Recovery**: Guide users on how to recover from error states

### 5. AI Integration Rules

#### OpenAI Usage Standards
- **Model Selection**: Use GPT-4o for optimal performance and latest features
- **Response Formatting**: Request JSON responses for structured data
- **Context Management**: Maintain conversation context appropriately
- **Rate Limiting**: Respect API rate limits and implement queuing

#### Content Quality
- **Response Validation**: Verify AI responses before sending to users
- **Content Filtering**: Ensure appropriate content for educational context
- **Accuracy Checks**: Validate factual information in AI responses
- **User Privacy**: Never send personal information to external APIs

### 6. Code Organization Rules

#### File Structure Standards
- **Separation of Concerns**: Keep handlers, services, and models separate
- **Naming Conventions**: Use clear, descriptive names for functions and variables
- **Import Organization**: Group imports logically (stdlib, third-party, local)
- **Documentation**: Include docstrings for all public functions and classes

#### Handler Implementation
```python
# CORRECT: Secure handler with proper error handling
@safe_handler(error_message=get_error_message('general'))
def my_command(update: Update, context: CallbackContext) -> None:
    user_id = InputValidator.validate_user_id(update.effective_user.id)
    if not user_id:
        return
    # Handler logic here

# INCORRECT: Unsafe handler without validation
def my_command(update, context):
    user_id = update.effective_user.id
    # Direct database access without validation
```

### 7. Performance Rules

#### Database Optimization
- **Query Efficiency**: Use appropriate indexes and limit result sets
- **Connection Management**: Implement proper connection pooling
- **Bulk Operations**: Use bulk inserts/updates for large datasets
- **Query Monitoring**: Log slow queries for optimization

#### Memory Management
- **Resource Cleanup**: Properly close files and database connections
- **Memory Limits**: Avoid loading large datasets into memory
- **Caching Strategy**: Implement appropriate caching for frequently accessed data
- **Garbage Collection**: Ensure proper cleanup of temporary resources

### 8. Testing Requirements

#### Test Coverage Standards
- **Unit Tests**: Test all business logic functions
- **Integration Tests**: Test database operations and external API calls
- **Security Tests**: Verify authentication and authorization mechanisms
- **Performance Tests**: Ensure acceptable response times under load

#### Test Data Management
- **Isolation**: Each test should be independent and repeatable
- **Cleanup**: Remove test data after test completion
- **Realistic Data**: Use representative test data without personal information
- **Mock External APIs**: Never test against production external services

## Common Pitfalls to Avoid

### 1. Database-Related Pitfalls

#### Schema Mismatches
```python
# DANGEROUS: Assuming column names without verification
exercise = TeacherExercise.query.filter_by(created_by_id=user.id)  # Wrong column name

# SAFE: Use actual schema column names
exercise = TeacherExercise.query.filter_by(creator_id=user.id)  # Correct column name
```

#### Transaction Handling
```python
# DANGEROUS: Operations without transaction protection
user.stats = new_stats
db.session.commit()  # Could fail leaving inconsistent state

# SAFE: Proper transaction handling
try:
    user.stats = new_stats
    db.session.commit()
except Exception as e:
    db.session.rollback()
    raise
```

### 2. Security Pitfalls

#### Input Validation
```python
# DANGEROUS: Direct use of user input
user_id = update.effective_user.id
user = User.query.filter_by(user_id=user_id).first()  # Could be None

# SAFE: Proper validation
user_id = InputValidator.validate_user_id(update.effective_user.id)
if not user_id:
    return
user = get_user_safely(user_id)
```

#### Permission Checks
```python
# DANGEROUS: No permission verification
def admin_function(update, context):
    # Direct admin operations without checking permissions

# SAFE: Proper authorization
@admin_required
def admin_function(update: Update, context: CallbackContext) -> None:
    # Operations only after permission verification
```

### 3. Translation Pitfalls

#### Hardcoded Messages
```python
# DANGEROUS: English-only messages
update.message.reply_text("Exercise created successfully!")

# SAFE: Localized messages
user_language = detect_language(update.effective_user.to_dict())
message = get_success_message('exercise_created', user_language)
update.message.reply_text(message)
```

### 4. Error Handling Pitfalls

#### Unhandled Exceptions
```python
# DANGEROUS: No error handling
def risky_operation(update, context):
    result = external_api_call()  # Could fail
    return result

# SAFE: Comprehensive error handling
@safe_handler(error_message="Operation failed. Please try again.")
def safe_operation(update: Update, context: CallbackContext) -> None:
    try:
        result = external_api_call()
        return result
    except APIException as e:
        logger.error(f"API call failed: {e}")
        # Handle gracefully
```

## Development Workflow

### 1. Before Making Changes
- Review existing code structure and patterns
- Check database schema documentation
- Verify translation keys exist for new messages
- Plan error handling strategy

### 2. During Development
- Follow established naming conventions
- Implement proper error handling
- Add appropriate logging
- Validate all user inputs

### 3. Before Deployment
- Test all new functionality thoroughly
- Verify database schema matches code expectations
- Check translation completeness
- Review security implications

### 4. After Deployment
- Monitor error logs for new issues
- Verify user-facing functionality works correctly
- Check performance metrics
- Gather user feedback

## Code Review Checklist

### Security Review
- [ ] All user inputs are validated and sanitized
- [ ] Permission checks are implemented correctly
- [ ] No sensitive information is logged or exposed
- [ ] SQL injection prevention measures are in place

### Database Review
- [ ] Column names match actual database schema
- [ ] Foreign key relationships are correct
- [ ] Transactions are used appropriately
- [ ] Query performance is acceptable

### Translation Review
- [ ] All user-facing messages use translation system
- [ ] Template variables are used for dynamic content
- [ ] Fallback mechanisms are implemented
- [ ] Language detection works correctly

### Error Handling Review
- [ ] All handlers use error catching decorators
- [ ] Error messages are user-friendly and localized
- [ ] Logging provides sufficient debugging information
- [ ] Graceful degradation is implemented

This comprehensive ruleset ensures consistent, secure, and maintainable development practices for the IELTS Preparation Bot platform.