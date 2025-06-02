# Botmaster Guide

## Overview
The botmaster feature provides a special administrative role in the IELTS Preparation Bot. Botmasters have special privileges to:

- View and manage pending role elevation requests
- Look up users and manage their roles
- View system statistics and usage analytics 
- Monitor system status

## Commands

### /botmaster
This command opens the main botmaster control panel. The command is only available to users who have the botmaster role.

## Features

### Role Elevation Requests
- View pending requests for teacher role elevation
- Approve or reject requests
- Add notes during approval/rejection
- Automatic notification to users when requests are processed

### User Management
- Look up users by Telegram ID, username, or name
- View user details including:
  - Role information
  - Group memberships
  - Pending requests
- Directly elevate users to teacher role

### Usage Analytics
- User growth over time
- Practice statistics by category
- Group activity metrics
- Teacher performance metrics

### System Status
- Database statistics
- Server status
- User counts by role type
- Database size

## How Role Elevation Works
1. A user requests to become a teacher using the `/register_as_teacher` command
2. The user provides a reason for the request
3. Botmasters are notified of the pending request
4. A botmaster reviews and approves or rejects the request
5. The user is notified of the decision

## Botmaster Privilege Management
The botmaster role is initially assigned to the user "@MunaLombe" in the database. 

To add additional botmasters:
1. A current botmaster must look up the user to be promoted
2. The botmaster must have the user's database entry modified to set `is_botmaster = TRUE`

## Security Considerations
- Botmaster privileges should only be granted to trusted administrators
- All botmaster actions are logged for accountability
- Role elevation requests create a permanent record in the database