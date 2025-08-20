# Local Authentication System

This document describes the local authentication system implemented to replace Supabase Auth for self-hosted Suna deployments.

## Overview

The local authentication system provides:
- JWT-based authentication with access and refresh tokens
- Password hashing using bcrypt
- Role-based access control (RBAC)
- User tier management
- Session management with refresh token rotation
- Admin interface for user management

## Components

### 1. Authentication Service (`services/auth.py`)
Core authentication logic including:
- User registration and login
- Password hashing and verification
- JWT token generation and validation
- User management (CRUD operations)
- Role-based permission checking

### 2. Authentication Middleware (`services/auth_middleware.py`)
FastAPI middleware and dependencies for:
- JWT token validation
- User context injection
- Role-based route protection
- Optional authentication support

### 3. Authentication API (`services/auth_api.py`)
REST API endpoints for:
- User registration and login
- Token refresh and logout
- User profile management
- Admin user management

### 4. Admin Interface (`services/admin_interface.py`)
Web-based admin interface for:
- User management dashboard
- User creation and editing
- System statistics
- User role and tier management

## Database Schema

The system uses the following tables:

### `users`
- `id` (UUID, Primary Key)
- `email` (VARCHAR, Unique)
- `password_hash` (VARCHAR)
- `role` (VARCHAR: 'user', 'moderator', 'admin')
- `tier` (VARCHAR: 'free', 'pro', 'enterprise')
- `is_active` (BOOLEAN)
- `created_at`, `updated_at` (TIMESTAMP)

### `user_sessions`
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key)
- `token_hash` (VARCHAR)
- `expires_at` (TIMESTAMP)
- `created_at` (TIMESTAMP)

### `user_tiers`
- Configuration table for user tiers
- Defines limits and features for each tier

### `usage_logs`
- Tracks user resource usage
- Replaces Stripe billing data

## Setup Instructions

### 1. Database Migration

Run the database migration to create the required tables:

```sql
-- Execute the SQL in backend/database/migrations/001_create_auth_tables.sql
-- This creates all necessary tables and indexes
```

### 2. Environment Configuration

Add to your `.env` file:

```bash
# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here-change-in-production
```

### 3. Initialize Authentication System

Run the initialization script:

```bash
cd backend
python database/init_auth.py
```

This will:
- Verify the database tables exist
- Create a default admin user (admin@localhost / Admin123!)

### 4. Test the System

Run the test script to verify everything works:

```bash
cd backend
python test_auth_system.py
```

## API Endpoints

### Authentication Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user info
- `PUT /api/auth/me` - Update current user
- `POST /api/auth/change-password` - Change password
- `GET /api/auth/validate-token` - Validate token

### Admin Endpoints (Require Admin Role)

- `GET /api/auth/users` - List all users
- `POST /api/auth/users` - Create user (admin)
- `GET /api/auth/users/{user_id}` - Get user by ID
- `PUT /api/auth/users/{user_id}` - Update user
- `DELETE /api/auth/users/{user_id}` - Delete user

### Admin Interface

- `GET /api/admin/` - Admin dashboard
- `GET /api/admin/users` - User management interface
- `GET /api/admin/users/create` - Create user form
- `GET /api/admin/users/{user_id}` - User detail/edit form
- `GET /api/admin/stats` - System statistics

## Usage Examples

### 1. User Registration

```python
import httpx

response = httpx.post("http://localhost:8000/api/auth/register", json={
    "email": "user@example.com",
    "password": "SecurePass123!",
    "role": "user",
    "tier": "free"
})
```

### 2. User Login

```python
response = httpx.post("http://localhost:8000/api/auth/login", json={
    "email": "user@example.com",
    "password": "SecurePass123!"
})

tokens = response.json()
access_token = tokens["access_token"]
```

### 3. Authenticated Request

```python
headers = {"Authorization": f"Bearer {access_token}"}
response = httpx.get("http://localhost:8000/api/auth/me", headers=headers)
```

### 4. Using Dependencies in FastAPI Routes

```python
from fastapi import Depends
from services.auth_middleware import get_current_active_user, require_admin
from services.auth import User

@app.get("/protected")
async def protected_route(user: User = Depends(get_current_active_user)):
    return {"message": f"Hello {user.email}"}

@app.get("/admin-only")
async def admin_route(admin: User = Depends(require_admin)):
    return {"message": "Admin access granted"}
```

## Security Features

### Password Security
- Minimum 8 characters
- Must contain uppercase, lowercase, number, and special character
- Hashed using bcrypt with salt

### JWT Security
- Access tokens expire in 30 minutes
- Refresh tokens expire in 7 days
- Tokens include user ID, email, role, and tier
- Refresh tokens are hashed and stored in database

### Session Management
- Refresh token rotation on use
- Automatic cleanup of expired tokens
- Secure httpOnly cookies for refresh tokens

### Role-Based Access Control
- Three roles: user, moderator, admin
- Hierarchical permissions (admin > moderator > user)
- Route-level protection via dependencies

## Configuration

### JWT Settings
- `JWT_SECRET_KEY`: Secret key for signing tokens (required)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiry (default: 30)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiry (default: 7)

### Password Policy
Configurable in `services/auth.py`:
- Minimum length
- Character requirements
- Complexity rules

### User Tiers
Defined in database `user_tiers` table:
- `free`: Basic tier with limited features
- `pro`: Enhanced tier with more features
- `enterprise`: Full access tier

## Migration from Supabase Auth

To migrate from Supabase Auth:

1. Export user data from Supabase
2. Run the database migration
3. Import users using the admin API
4. Update frontend to use new auth endpoints
5. Replace Supabase client calls with local auth

## Troubleshooting

### Common Issues

1. **JWT_SECRET_KEY not set**
   - Add JWT_SECRET_KEY to your .env file
   - Generate a secure random key

2. **Database tables don't exist**
   - Run the migration SQL manually
   - Check database connection settings

3. **Default admin user not created**
   - Run `python database/init_auth.py`
   - Check database permissions

4. **Token validation fails**
   - Verify JWT_SECRET_KEY matches
   - Check token expiry
   - Ensure proper Authorization header format

### Logs

Check application logs for authentication errors:
- User creation failures
- Login attempts
- Token validation issues
- Permission denied errors

## Production Considerations

1. **Change default admin password immediately**
2. **Use a strong JWT_SECRET_KEY**
3. **Enable HTTPS for secure cookie transmission**
4. **Set up proper database backups**
5. **Monitor authentication logs**
6. **Implement rate limiting on auth endpoints**
7. **Regular security updates**

## Future Enhancements

Potential improvements:
- Two-factor authentication (2FA)
- OAuth integration
- Password reset via email
- Account lockout after failed attempts
- Audit logging
- API key authentication
- Single sign-on (SSO)