# app/forms.py (create this file)
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, EmailField, URLField, TelField, FieldList, FormField
from wtforms.validators import DataRequired, Email, URL, Optional, Length
from wtforms.widgets import TextArea

class MetadataField(FlaskForm):
    """Sub-form for metadata key-value pairs"""
    key = StringField('Key', validators=[Optional(), Length(max=100)])
    value = StringField('Value', validators=[Optional(), Length(max=500)])

class AgencyForm(FlaskForm):
    """Form for creating and editing transit agencies"""
    # Basic Information
    name = StringField('Agency Name', 
                      validators=[DataRequired(message="Agency name is required"), 
                                Length(max=100, message="Name must be less than 100 characters")])
    location = StringField('Location', 
                          validators=[Optional(), Length(max=100)])
    description = TextAreaField('Description', 
                               validators=[Optional(), Length(max=500)],
                               widget=TextArea())
    address_hq = TextAreaField('Headquarters Address', 
                              validators=[Optional(), Length(max=256)],
                              widget=TextArea())
    ceo = StringField('Chief Executive Officer', 
                     validators=[Optional(), Length(max=128)])
    contact_name = StringField('Primary Contact Name', 
                              validators=[Optional(), Length(max=100)])
    contact_email = EmailField('Primary Contact Email', 
                              validators=[Optional(), Email(message="Please enter a valid email address")])
    contact_phone = TelField('Primary Contact Phone', 
                            validators=[Optional(), Length(max=50)])
    phone_number = TelField('Main Phone Number', 
                           validators=[Optional(), Length(max=64)])
    website = URLField('Official Website', 
                      validators=[Optional(), URL(message="Please enter a valid URL")])
    transit_map_link = URLField('Transit Map URL', 
                              validators=[Optional(), URL(message="Please enter a valid URL")])
    email_domain = StringField('Agency Email Domain', validators=[Optional(), Length(max=255)])
    
    # Dynamic metadata fields will be handled separately in the template and route
    def populate_from_agency(self, agency):
        """Populate form with data from agency model"""
        self.name.data = agency.name
        self.location.data = agency.location
        self.description.data = agency.description
        self.address_hq.data = agency.address_hq
        self.ceo.data = agency.ceo
        self.contact_name.data = agency.contact_name
        self.contact_email.data = agency.contact_email
        self.contact_phone.data = agency.contact_phone
        self.phone_number.data = agency.phone_number
        self.website.data = agency.website
        self.transit_map_link.data = agency.transit_map_link
        self.email_domain.data = agency.email_domain
    
    def populate_agency(self, agency):
        """Populate agency model with form data"""
        agency.name = self.name.data
        agency.location = self.location.data or None
        agency.description = self.description.data or None
        agency.address_hq = self.address_hq.data or None
        agency.ceo = self.ceo.data or None
        agency.contact_name = self.contact_name.data or None
        agency.contact_email = self.contact_email.data or None
        agency.contact_phone = self.contact_phone.data or None
        agency.phone_number = self.phone_number.data or None
        agency.website = self.website.data or None
        agency.transit_map_link = self.transit_map_link.data or None
        agency.email_domain = (self.email_domain.data or None)

class VendorForm(FlaskForm):
    name = StringField('Vendor Name', validators=[DataRequired(), Length(min=2, max=100)])
    short_name = StringField('Short Name', validators=[Length(max=50)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    website = URLField('Website', validators=[Optional(), URL()])
    vendor_email = StringField('General Email', validators=[Optional(), Email(), Length(max=255)])
    vendor_phone = StringField('General Phone', validators=[Optional(), Length(max=50)])
    
    def populate_from_vendor(self, vendor):
        """Populate form fields from vendor object"""
        self.name.data = vendor.name
        self.short_name.data = vendor.short_name
        self.description.data = vendor.description
        self.website.data = vendor.website
        self.vendor_email.data = vendor.vendor_email
        self.vendor_phone.data = vendor.vendor_phone
    
    def populate_vendor(self, vendor):
        """Populate vendor object from form data"""
        vendor.name = self.name.data
        vendor.short_name = self.short_name.data
        vendor.description = self.description.data
        vendor.website = self.website.data
        vendor.vendor_email = self.vendor_email.data
        vendor.vendor_phone = self.vendor_phone.data

class ComponentForm(FlaskForm):
    name = StringField('Component Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])

    def populate_from_component(self, component):
        self.name.data = component.name
        self.description.data = component.description

    def populate_component(self, component):
        component.name = self.name.data
        component.description = self.description.data or None

# =============================
# Phase 3 ADDITIVE NEW FORMS
# =============================

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(min=2, max=150)])
    vendor_id = StringField('Vendor', validators=[Optional(), Length(max=10)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    parent_product_id = StringField('Parent Product', validators=[Optional(), Length(max=10)])
    lifecycle_stage = StringField('Lifecycle Stage', validators=[Optional(), Length(max=50)])
    additional_metadata = TextAreaField('Additional Metadata (JSON)', validators=[Optional(), Length(max=5000)])

    def populate_from_product(self, product):
        self.name.data = product.name
        self.vendor_id.data = str(product.vendor_id) if product.vendor_id else ''
        self.description.data = product.description
        self.parent_product_id.data = str(product.parent_product_id) if product.parent_product_id else ''
        self.lifecycle_stage.data = product.lifecycle_stage.value if getattr(product, 'lifecycle_stage', None) else ''
        if product.additional_metadata:
            import json
            try:
                self.additional_metadata.data = json.dumps(product.additional_metadata, indent=2)
            except Exception:
                self.additional_metadata.data = ''

    def populate_product(self, product):
        product.name = self.name.data
        product.vendor_id = int(self.vendor_id.data) if self.vendor_id.data else None
        product.description = self.description.data or None
        product.parent_product_id = int(self.parent_product_id.data) if self.parent_product_id.data else None
        from app.models.tran import LifecycleStage
        if self.lifecycle_stage.data:
            try:
                product.lifecycle_stage = LifecycleStage(self.lifecycle_stage.data)
            except Exception:
                product.lifecycle_stage = None
        if self.additional_metadata.data:
            import json
            try:
                product.additional_metadata = json.loads(self.additional_metadata.data)
            except Exception:
                product.additional_metadata = None
        else:
            product.additional_metadata = None

class ProductVersionForm(FlaskForm):
    product_id = StringField('Product', validators=[DataRequired(), Length(max=10)])
    version = StringField('Version', validators=[DataRequired(), Length(max=100)])
    release_date = StringField('Release Date', validators=[Optional(), Length(max=10)])  # YYYY-MM-DD
    support_end_date = StringField('Support End Date', validators=[Optional(), Length(max=10)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=1000)])

    def populate_from_version(self, pv):
        self.product_id.data = str(pv.product_id)
        self.version.data = pv.version
        self.release_date.data = pv.release_date.strftime('%Y-%m-%d') if pv.release_date else ''
        self.support_end_date.data = pv.support_end_date.strftime('%Y-%m-%d') if pv.support_end_date else ''
        self.notes.data = pv.notes

    def populate_version(self, pv):
        pv.product_id = int(self.product_id.data)
        pv.version = self.version.data
        from datetime import datetime
        if self.release_date.data:
            try:
                pv.release_date = datetime.strptime(self.release_date.data, '%Y-%m-%d').date()
            except ValueError:
                pass
        if self.support_end_date.data:
            try:
                pv.support_end_date = datetime.strptime(self.support_end_date.data, '%Y-%m-%d').date()
            except ValueError:
                pass
        pv.notes = self.notes.data or None

class ConfigurationForm(FlaskForm):
    agency_id = StringField('Agency', validators=[DataRequired(), Length(max=10)])
    function_id = StringField('Function', validators=[DataRequired(), Length(max=10)])
    component_id = StringField('Component', validators=[DataRequired(), Length(max=10)])
    status = StringField('Status', validators=[Optional(), Length(max=50)])
    deployment_date = StringField('Deployment Date', validators=[Optional(), Length(max=10)])
    version_label = StringField('Version Label', validators=[Optional(), Length(max=100)])
    implementation_notes = TextAreaField('Implementation Notes', validators=[Optional(), Length(max=1000)])
    security_review_date = StringField('Security Review Date', validators=[Optional(), Length(max=10)])
    additional_metadata = TextAreaField('Additional Metadata (JSON)', validators=[Optional(), Length(max=5000)])

    def populate_from_configuration(self, c):
        self.agency_id.data = str(c.agency_id)
        self.function_id.data = str(c.function_id)
        self.component_id.data = str(c.component_id)
        self.status.data = c.status
        self.deployment_date.data = c.deployment_date.strftime('%Y-%m-%d') if c.deployment_date else ''
        self.version_label.data = c.version_label
        self.implementation_notes.data = c.implementation_notes
        self.security_review_date.data = c.security_review_date.strftime('%Y-%m-%d') if c.security_review_date else ''
        if c.additional_metadata:
            import json
            try:
                self.additional_metadata.data = json.dumps(c.additional_metadata, indent=2)
            except Exception:
                self.additional_metadata.data = ''

    def populate_configuration(self, c):
        c.agency_id = int(self.agency_id.data)
        c.function_id = int(self.function_id.data)
        c.component_id = int(self.component_id.data)
        c.status = self.status.data or 'Active'
        from datetime import datetime
        if self.deployment_date.data:
            try:
                c.deployment_date = datetime.strptime(self.deployment_date.data, '%Y-%m-%d').date()
            except ValueError:
                pass
        c.version_label = self.version_label.data or None
        c.implementation_notes = self.implementation_notes.data or None
        if self.security_review_date.data:
            try:
                c.security_review_date = datetime.strptime(self.security_review_date.data, '%Y-%m-%d').date()
            except ValueError:
                pass
        if self.additional_metadata.data:
            import json
            try:
                c.additional_metadata = json.loads(self.additional_metadata.data)
            except Exception:
                c.additional_metadata = None
        else:
            c.additional_metadata = None

class ConfigurationProductForm(FlaskForm):
    configuration_id = StringField('Configuration', validators=[Optional(), Length(max=10)])  # may come from URL
    product_id = StringField('Product', validators=[DataRequired(), Length(max=10)])
    product_version_id = StringField('Product Version', validators=[Optional(), Length(max=10)])
    status = StringField('Status', validators=[Optional(), Length(max=50)])
    deployment_date = StringField('Deployment Date', validators=[Optional(), Length(max=10)])
    settings = TextAreaField('Settings (JSON)', validators=[Optional(), Length(max=5000)])

    def populate_from_configuration_product(self, cp):
        self.configuration_id.data = str(cp.configuration_id)
        self.product_id.data = str(cp.product_id)
        self.product_version_id.data = str(cp.product_version_id) if cp.product_version_id else ''
        self.status.data = cp.status
        self.deployment_date.data = cp.deployment_date.strftime('%Y-%m-%d') if cp.deployment_date else ''
        if cp.settings:
            import json
            try:
                self.settings.data = json.dumps(cp.settings, indent=2)
            except Exception:
                self.settings.data = ''

    def populate_configuration_product(self, cp):
        if self.configuration_id.data:
            cp.configuration_id = int(self.configuration_id.data)
        cp.product_id = int(self.product_id.data)
        cp.product_version_id = self.product_version_id.data if self.product_version_id.data else None
        cp.status = self.status.data or 'Active'
        from datetime import datetime
        if self.deployment_date.data:
            try:
                cp.deployment_date = datetime.strptime(self.deployment_date.data, '%Y-%m-%d').date()
            except ValueError:
                pass
        if self.settings.data:
            import json
            try:
                cp.settings = json.loads(self.settings.data)
            except Exception:
                cp.settings = None
        else:
            cp.settings = None

# =============================
# End Phase 3 additions
# =============================