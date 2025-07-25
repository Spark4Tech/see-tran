# app/utils_logging.py
from flask import g, current_app, has_app_context
from flask_login import current_user
import functools

def log_with_context(level, message, **context):
    """Log a message with contextual information."""
    from flask import g, has_request_context
    
    # Get tenant ID - handle both dict and object cases
    tenant_id = None
    if hasattr(g, 'tenant') and g.tenant:
        if hasattr(g.tenant, 'id'):
            # g.tenant is a Tenant object
            tenant_id = g.tenant.id
        elif isinstance(g.tenant, dict):
            # g.tenant is a dictionary
            tenant_id = g.tenant.get('id')
    
    # Add tenant_id to context if available
    if tenant_id:
        context['tenant_id'] = tenant_id
    
    # Get user ID if available
    if hasattr(g, 'current_user') and g.current_user and hasattr(g.current_user, 'id'):
        context['user_id'] = g.current_user.id
    
    # Format the message with context
    if context:
        context_str = ' | '.join([f"{k}: {v}" for k, v in context.items()])
        formatted_message = f"{message} | {context_str}"
    else:
        formatted_message = message
    
    # Log at the appropriate level
    from flask import current_app
    logger = current_app.logger
    
    if level == 'debug':
        logger.debug(formatted_message)
    elif level == 'info':
        logger.info(formatted_message)
    elif level == 'warning':
        logger.warning(formatted_message)
    elif level == 'error':
        logger.error(formatted_message)
    else:
        logger.info(formatted_message)

# Convenience functions
def log_info(message, **context):
    log_with_context('info', message, **context)

def log_debug(message, **context):
    log_with_context('debug', message, **context)

def log_warning(message, **context):
    log_with_context('warning', message, **context)

def log_error(message, **context):
    log_with_context('error', message, **context)

def log_sms_event(event_type, phone_number, message, **context):
    """Specialized logging for SMS events."""
    masked_phone = phone_number[-4:].rjust(len(phone_number), '*') if phone_number else 'unknown'
    log_info(
        f"SMS_{event_type.upper()}: {masked_phone} | {message}",
        event=event_type,
        **context
    )