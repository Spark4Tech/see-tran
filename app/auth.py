# app/auth.py
from functools import wraps
from flask import request, jsonify, flash

def login_required(f):
    """
    Authentication decorator - currently a no-op stub for development
    Will be enhanced later with actual authentication logic
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For now, just pass through - no authentication required
        # TODO: Add actual authentication logic here
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """
    Get current user context - currently returns stub user
    """
    return {
        'id': 1,
        'username': 'Steve',
        'display_name': '1_Steve'
    }

def get_updated_by():
    """
    Get the updated_by string for audit logging
    """
    user = get_current_user()
    return user['display_name']