from flask import Blueprint, render_template
from app.auth import super_admin_required

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
@super_admin_required
def dashboard():
    return render_template('admin/dashboard.html')
