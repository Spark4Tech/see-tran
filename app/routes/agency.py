from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models.tran import Agency
from app.forms.forms import AgencyForm

agency_bp = Blueprint('agency', __name__, url_prefix='/agencies')

@agency_bp.route('/new', methods=['GET', 'POST'])
def add_agency():
    form = AgencyForm()
    if form.validate_on_submit():
        # Check for duplicate agency name
        existing = Agency.query.filter_by(name=form.name.data).first()
        if existing:
            flash('An agency with this name already exists.', 'danger')
            return render_template('fragments/agency_form.html', form=form)
        agency = Agency()
        form.populate_agency(agency)
        db.session.add(agency)
        try:
            db.session.commit()
            flash('Agency added successfully!', 'success')
            return redirect(url_for('main.index'))  # Adjust as needed
        except Exception as e:
            db.session.rollback()
            flash('Error adding agency: {}'.format(str(e)), 'danger')
    return render_template('fragments/agency_form.html', form=form)
