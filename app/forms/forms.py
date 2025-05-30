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
    
    # Address & Location
    address_hq = TextAreaField('Headquarters Address', 
                              validators=[Optional(), Length(max=256)],
                              widget=TextArea())
    
    # Leadership
    ceo = StringField('Chief Executive Officer', 
                     validators=[Optional(), Length(max=128)])
    
    # Contact Information
    contact_name = StringField('Primary Contact Name', 
                              validators=[Optional(), Length(max=100)])
    
    contact_email = EmailField('Primary Contact Email', 
                              validators=[Optional(), Email(message="Please enter a valid email address")])
    
    contact_phone = TelField('Primary Contact Phone', 
                            validators=[Optional(), Length(max=50)])
    
    phone_number = TelField('Main Phone Number', 
                           validators=[Optional(), Length(max=64)])
    
    # Web & Resources
    website = URLField('Official Website', 
                      validators=[Optional(), URL(message="Please enter a valid URL")])
    
    agency_map_link = URLField('Transit Map URL', 
                              validators=[Optional(), URL(message="Please enter a valid URL")])
    
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
        self.agency_map_link.data = agency.agency_map_link
    
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
        agency.agency_map_link = self.agency_map_link.data or None