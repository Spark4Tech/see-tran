# app/utils/errors.py
from flask import jsonify, render_template_string

def json_error_response(message, status_code=400, details=None):
    """
    Return a JSON error response for API endpoints
    """
    response = {
        'status': 'error',
        'message': message
    }
    if details:
        response['details'] = details
    
    return jsonify(response), status_code

def json_success_response(message="Success", data=None):
    """
    Return a JSON success response for API endpoints
    """
    response = {
        'status': 'success',
        'message': message
    }
    if data:
        response['data'] = data
    
    return jsonify(response)

def json_validation_error_response(message="Validation failed", errors=None):
    """
    Return a JSON validation error response with field-specific errors
    """
    response = {
        'status': 'validation_error',
        'message': message
    }
    if errors:
        response['errors'] = errors
    
    return jsonify(response), 422

def json_form_error_response(form):
    """
    Convert Flask-WTF form errors to JSON response
    """
    errors = {}
    for field_name, field_errors in form.errors.items():
        errors[field_name] = field_errors[0] if field_errors else 'Invalid input'
    
    return json_validation_error_response("Please correct the errors below", errors)

def html_error_fragment(message, title="Error"):
    """
    Return an HTML error fragment for HTMX responses (legacy support)
    """
    template = '''
    <div class="bg-red-900/20 border border-red-700/30 rounded-lg p-4 mb-4">
        <div class="flex items-center space-x-3">
            <svg class="w-5 h-5 text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
            </svg>
            <div>
                <h4 class="text-red-300 font-medium">{{ title }}</h4>
                <p class="text-red-200 text-sm">{{ message }}</p>
            </div>
        </div>
    </div>
    '''
    return render_template_string(template, title=title, message=message)

def html_success_fragment(message, title="Success"):
    """
    Return an HTML success fragment for HTMX responses (legacy support)
    """
    template = '''
    <div class="bg-green-900/20 border border-green-700/30 rounded-lg p-4 mb-4">
        <div class="flex items-center space-x-3">
            <svg class="w-5 h-5 text-green-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
                <h4 class="text-green-300 font-medium">{{ title }}</h4>
                <p class="text-green-200 text-sm">{{ message }}</p>
            </div>
        </div>
    </div>
    '''
    return render_template_string(template, title=title, message=message)