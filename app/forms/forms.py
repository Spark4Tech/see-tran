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