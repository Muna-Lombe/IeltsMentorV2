# IELTS Preparation Bot - API Reference

## Telegram Bot API Commands

### Student Commands

#### `/start`
**Description**: Initialize bot interaction and user registration
**Usage**: `/start`
**Response**: Welcome message with language detection and user profile creation
**Permissions**: Public

#### `/practice [section]`
**Description**: Access adaptive practice exercises
**Usage**: 
- `/practice` - Show section selection menu
- `/practice speaking` - Direct to speaking practice
- `/practice writing` - Direct to writing practice
- `/practice reading` - Direct to reading practice
- `/practice listening` - Direct to listening practice
**Response**: Interactive practice session with adaptive questions
**Permissions**: Registered users

#### `/explain [query]`
**Description**: Get AI-powered explanations for IELTS concepts
**Usage**: 
- `/explain` - Interactive explanation mode
- `/explain grammar present perfect` - Direct grammar explanation
- `/explain vocabulary academic` - Vocabulary explanations
**Response**: Detailed explanation with examples and usage
**Permissions**: Registered users

#### `/define [word]`
**Description**: Get word definitions and usage examples
**Usage**: 
- `/define` - Interactive definition mode
- `/define elaborate` - Direct word definition
**Response**: Definition, pronunciation, examples, and synonyms
**Permissions**: Registered users

#### `/stats`
**Description**: View personal progress statistics
**Usage**: `/stats`
**Response**: Comprehensive performance analytics across all sections
**Permissions**: Registered users

### Teacher Commands

#### `/create_group [name]`
**Description**: Create new student learning group
**Usage**: 
- `/create_group` - Interactive group creation
- `/create_group "Advanced IELTS Class"` - Direct group creation
**Response**: Group creation confirmation with management options
**Permissions**: Approved teachers

#### `/my_exercises`
**Description**: Manage created exercises
**Usage**: `/my_exercises`
**Response**: List of created exercises with edit/publish options
**Permissions**: Approved teachers

#### `/create_exercise`
**Description**: Create custom practice exercises
**Usage**: `/create_exercise`
**Response**: Interactive exercise creation wizard
**Permissions**: Approved teachers

#### `/assign_homework [group] [exercise]`
**Description**: Assign exercises to student groups
**Usage**: 
- `/assign_homework` - Interactive assignment
- `/assign_homework "Group 1" "Writing Task 1"` - Direct assignment
**Response**: Assignment confirmation with deadline options
**Permissions**: Approved teachers

#### `/group_analytics [group]`
**Description**: View detailed group performance reports
**Usage**: 
- `/group_analytics` - Group selection menu
- `/group_analytics "Advanced Class"` - Direct group analytics
**Response**: Comprehensive group performance dashboard
**Permissions**: Approved teachers (own groups only)

#### `/student_progress [student]`
**Description**: View individual student progress
**Usage**: 
- `/student_progress` - Student selection from groups
- `/student_progress @username` - Direct student lookup
**Response**: Detailed individual progress report
**Permissions**: Approved teachers (own students only)

### Administrator Commands

#### `/approve_teacher [user]`
**Description**: Approve teacher account requests
**Usage**: 
- `/approve_teacher` - Show pending requests
- `/approve_teacher @username` - Direct approval
**Response**: Teacher approval confirmation
**Permissions**: Botmasters only

#### `/system_stats`
**Description**: View platform-wide analytics
**Usage**: `/system_stats`
**Response**: Comprehensive system usage statistics
**Permissions**: Botmasters only

#### `/manage_content`
**Description**: Content moderation interface
**Usage**: `/manage_content`
**Response**: Content review and moderation tools
**Permissions**: Botmasters only

## Web Interface API Endpoints

### Authentication Endpoints

#### `POST /api/auth/login`
**Description**: Teacher authentication via API token
**Parameters**:
- `api_token` (string): Teacher API token
**Response**: Authentication status and session creation
**Headers**: `Content-Type: application/json`

#### `POST /api/auth/logout`
**Description**: Terminate authenticated session
**Response**: Logout confirmation
**Authentication**: Required

### Student Management Endpoints

#### `GET /api/students`
**Description**: List students in teacher's groups
**Parameters**:
- `group_id` (optional): Filter by specific group
- `page` (optional): Pagination page number
- `limit` (optional): Results per page (default: 20)
**Response**: Paginated student list with basic information
**Authentication**: Teacher required

#### `GET /api/students/{student_id}`
**Description**: Get detailed student information
**Parameters**:
- `student_id` (integer): Student database ID
**Response**: Complete student profile and progress data
**Authentication**: Teacher required (must have access to student)

#### `GET /api/students/{student_id}/progress`
**Description**: Get student progress analytics
**Parameters**:
- `student_id` (integer): Student database ID
- `section` (optional): Filter by IELTS section
- `timeframe` (optional): Date range for analytics
**Response**: Detailed progress statistics and performance trends
**Authentication**: Teacher required

### Group Management Endpoints

#### `GET /api/groups`
**Description**: List teacher's groups
**Response**: Array of group objects with member counts
**Authentication**: Teacher required

#### `POST /api/groups`
**Description**: Create new student group
**Parameters**:
- `name` (string): Group name
- `description` (string): Group description
**Response**: Created group object with ID
**Authentication**: Teacher required

#### `GET /api/groups/{group_id}`
**Description**: Get detailed group information
**Parameters**:
- `group_id` (integer): Group database ID
**Response**: Group details with member list and analytics
**Authentication**: Teacher required (must be group owner)

#### `PUT /api/groups/{group_id}`
**Description**: Update group information
**Parameters**:
- `group_id` (integer): Group database ID
- `name` (optional): Updated group name
- `description` (optional): Updated description
**Response**: Updated group object
**Authentication**: Teacher required (must be group owner)

#### `POST /api/groups/{group_id}/members`
**Description**: Add student to group
**Parameters**:
- `group_id` (integer): Group database ID
- `student_id` (integer): Student database ID
**Response**: Membership confirmation
**Authentication**: Teacher required (must be group owner)

#### `DELETE /api/groups/{group_id}/members/{student_id}`
**Description**: Remove student from group
**Parameters**:
- `group_id` (integer): Group database ID
- `student_id` (integer): Student database ID
**Response**: Removal confirmation
**Authentication**: Teacher required (must be group owner)

### Exercise Management Endpoints

#### `GET /api/exercises`
**Description**: List teacher's exercises
**Parameters**:
- `type` (optional): Filter by exercise type
- `published` (optional): Filter by publication status
**Response**: Array of exercise objects
**Authentication**: Teacher required

#### `POST /api/exercises`
**Description**: Create new exercise
**Parameters**:
- `title` (string): Exercise title
- `description` (string): Exercise description
- `type` (string): Exercise type (vocabulary, grammar, etc.)
- `content` (object): Exercise questions and answers
- `difficulty` (string): Difficulty level
**Response**: Created exercise object
**Authentication**: Teacher required

#### `GET /api/exercises/{exercise_id}`
**Description**: Get detailed exercise information
**Parameters**:
- `exercise_id` (integer): Exercise database ID
**Response**: Complete exercise object with content
**Authentication**: Teacher required (must be exercise creator)

#### `PUT /api/exercises/{exercise_id}`
**Description**: Update exercise
**Parameters**:
- `exercise_id` (integer): Exercise database ID
- Exercise fields to update
**Response**: Updated exercise object
**Authentication**: Teacher required (must be exercise creator)

#### `POST /api/exercises/{exercise_id}/publish`
**Description**: Publish exercise for assignment
**Parameters**:
- `exercise_id` (integer): Exercise database ID
**Response**: Publication confirmation
**Authentication**: Teacher required (must be exercise creator)

### Homework Management Endpoints

#### `GET /api/homework`
**Description**: List assigned homework
**Parameters**:
- `group_id` (optional): Filter by group
- `status` (optional): Filter by completion status
**Response**: Array of homework assignments
**Authentication**: Teacher required

#### `POST /api/homework`
**Description**: Assign homework to group
**Parameters**:
- `exercise_id` (integer): Exercise to assign
- `group_id` (integer): Target group
- `due_date` (datetime): Assignment deadline
- `instructions` (string): Additional instructions
**Response**: Assignment confirmation
**Authentication**: Teacher required

#### `GET /api/homework/{homework_id}/submissions`
**Description**: View homework submissions
**Parameters**:
- `homework_id` (integer): Homework assignment ID
**Response**: Array of student submissions with scores
**Authentication**: Teacher required (must be assignment creator)

### Analytics Endpoints

#### `GET /api/analytics/groups/{group_id}`
**Description**: Get comprehensive group analytics
**Parameters**:
- `group_id` (integer): Group database ID
- `timeframe` (optional): Analysis period
**Response**: Detailed group performance statistics
**Authentication**: Teacher required (must be group owner)

#### `GET /api/analytics/exercises/{exercise_id}`
**Description**: Get exercise performance analytics
**Parameters**:
- `exercise_id` (integer): Exercise database ID
**Response**: Exercise usage and performance statistics
**Authentication**: Teacher required (must be exercise creator)

#### `GET /api/analytics/system`
**Description**: Get platform-wide analytics
**Response**: System usage and performance metrics
**Authentication**: Botmaster required

## Webhook Endpoints

#### `POST /webhook`
**Description**: Telegram bot webhook endpoint
**Parameters**: Telegram Update object
**Response**: Processing confirmation
**Authentication**: Telegram signature verification

## Response Formats

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional error information"
  }
}
```

### Pagination Response
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 150,
      "pages": 8
    }
  }
}
```

## Error Codes

- `AUTH_REQUIRED` - Authentication required for this endpoint
- `AUTH_INVALID` - Invalid authentication credentials
- `PERMISSION_DENIED` - Insufficient permissions for operation
- `RESOURCE_NOT_FOUND` - Requested resource does not exist
- `VALIDATION_ERROR` - Request validation failed
- `RATE_LIMIT_EXCEEDED` - API rate limit exceeded
- `INTERNAL_ERROR` - Internal server error occurred