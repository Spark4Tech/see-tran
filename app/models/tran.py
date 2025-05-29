# models/tran.py

from datetime import datetime
from app import db
import enum

# Association Tables
component_integration = db.Table(
    'component_integration',
    db.Column('component_id', db.Integer, db.ForeignKey('components.id'), primary_key=True),
    db.Column('integration_point_id', db.Integer, db.ForeignKey('integration_points.id'), primary_key=True)
)

function_component = db.Table(
    'function_component',
    db.Column('function_id', db.Integer, db.ForeignKey('functions.id'), primary_key=True),
    db.Column('component_id', db.Integer, db.ForeignKey('components.id'), primary_key=True)
)

component_tag = db.Table(
    'component_tag',
    db.Column('component_id', db.Integer, db.ForeignKey('components.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

integration_tag = db.Table(
    'integration_tag',
    db.Column('integration_point_id', db.Integer, db.ForeignKey('integration_points.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

integration_standard = db.Table(
    'integration_standard',
    db.Column('integration_point_id', db.Integer, db.ForeignKey('integration_points.id'), primary_key=True),
    db.Column('standard_id', db.Integer, db.ForeignKey('standards.id'), primary_key=True)
)

# Enums
class Criticality(enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"

# Core Models
class Agency(db.Model):
    __tablename__ = 'agencies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100))
    description = db.Column(db.String(500))
    website = db.Column(db.String(255))
    ceo = db.Column(db.String(128))
    address_hq = db.Column(db.String(256))
    phone_number = db.Column(db.String(64))
    transit_map_link = db.Column(db.String(256))
    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(50))
    contact_name = db.Column(db.String(100))
    additional_metadata = db.Column(db.JSON)
    __table_args__ = (
        db.UniqueConstraint('name', name='uq_transit_system_name'),
    )

    function_implementations = db.relationship('AgencyFunctionImplementation', back_populates='agency', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Agency(name={self.name}, location={self.location})>"

class FunctionalArea(db.Model):
    __tablename__ = 'functional_areas'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))

    functions = db.relationship('Function', back_populates='functional_area', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<FunctionalArea(name={self.name})>"

class Function(db.Model):
    __tablename__ = 'functions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    criticality = db.Column(db.Enum(Criticality), default=Criticality.medium, nullable=False)

    functional_area_id = db.Column(db.Integer, db.ForeignKey('functional_areas.id'), nullable=False)
    functional_area = db.relationship('FunctionalArea', back_populates='functions')

    components = db.relationship('Component', secondary='function_component', back_populates='functions')
    agency_implementations = db.relationship('AgencyFunctionImplementation', back_populates='function', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Function(name={self.name}, criticality={self.criticality.value})>"

class Vendor(db.Model):
    __tablename__ = 'vendors'
    __table_args__ = (
        db.UniqueConstraint('name', name='uq_vendor_name'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    website = db.Column(db.String(255))
    vendor_email = db.Column(db.String(255))
    vendor_phone = db.Column(db.String(50))
    contact_name = db.Column(db.String(100))
    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(50))
    description = db.Column(db.String(500))

    components = db.relationship('Component', back_populates='vendor', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Vendor(name={self.name})>"
    
    @property
    def contact_info(self):
        """
        Consolidated contact information for backward compatibility
        """
        if self.contact_email:
            return self.contact_email
        elif self.contact_name:
            return self.contact_name
        elif self.contact_phone:
            return self.contact_phone
        elif self.vendor_email:
            return self.vendor_email
        elif self.vendor_phone:
            return self.vendor_phone
        else:
            return None

class Component(db.Model):
    __tablename__ = 'components'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(1000))
    version = db.Column(db.String(50))
    deployment_date = db.Column(db.Date)
    update_frequency = db.Column(db.String(50))
    known_issues = db.Column(db.String(500))
    additional_metadata = db.Column(db.JSON)
    # Component nesting functionality
    parent_component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    parent_component = db.relationship('Component', remote_side=[id], backref='child_components')
    is_composite = db.Column(db.Boolean, default=False, nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=True)

    vendor = db.relationship('Vendor', back_populates='components')
    functions = db.relationship('Function', secondary='function_component', back_populates='components')
    integration_points = db.relationship('IntegrationPoint', secondary='component_integration', back_populates='components')
    tags = db.relationship('Tag', secondary='component_tag', back_populates='components')
    user_roles = db.relationship('UserRole', back_populates='component', cascade='all, delete-orphan')
    update_logs = db.relationship('UpdateLog', back_populates='component', cascade='all, delete-orphan')
    agency_usages = db.relationship('AgencyFunctionImplementation', back_populates='component', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Component(name={self.name}, version={self.version})>"
    
class AgencyFunctionImplementation(db.Model):
    __tablename__ = 'agency_function_implementations'
    
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=False)
    function_id = db.Column(db.Integer, db.ForeignKey('functions.id'), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    
    # Agency-specific deployment details
    deployment_date = db.Column(db.Date)
    version = db.Column(db.String(50))
    deployment_notes = db.Column(db.String(1000))
    status = db.Column(db.String(50), default='Active')  # Active, Planned, Retired
    implementation_notes = db.Column(db.String(1000))
    additional_metadata = db.Column(db.JSON)
    
    # Relationships
    agency = db.relationship('Agency', back_populates='function_implementations')
    function = db.relationship('Function', back_populates='agency_implementations')  
    component = db.relationship('Component', back_populates='agency_usages')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('agency_id', 'function_id', 'component_id', 
                          name='uq_agency_function_component'),
    )
    
    def __repr__(self):
        return f"<AgencyFunctionImplementation(agency={self.agency.name if self.agency else None}, function={self.function.name if self.function else None}, component={self.component.name if self.component else None})>"

class IntegrationPoint(db.Model):
    __tablename__ = 'integration_points'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    website = db.Column(db.String(255))

    standards = db.relationship('Standard', secondary=integration_standard, back_populates='integration_points')
    components = db.relationship('Component', secondary='component_integration', back_populates='integration_points')
    tags = db.relationship('Tag', secondary=integration_tag, back_populates='integration_points')

    def __repr__(self):
        return f"<IntegrationPoint(name={self.name})>"

class Standard(db.Model):
    __tablename__ = 'standards'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500))
    version = db.Column(db.String(50))
    standard_url = db.Column(db.String(255))

    integration_points = db.relationship('IntegrationPoint', secondary=integration_standard, back_populates='standards')

    def __repr__(self):
        return f"<Standard(name={self.name}, version={self.version})>"

class TagGroup(db.Model):
    __tablename__ = 'tag_groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500))

    tags = db.relationship('Tag', back_populates='tag_group', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<TagGroup(name={self.name})>"

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    color = db.Column(db.String(20))

    tag_group_id = db.Column(db.Integer, db.ForeignKey('tag_groups.id'), nullable=False)
    tag_group = db.relationship('TagGroup', back_populates='tags')

    components = db.relationship('Component', secondary='component_tag', back_populates='tags')
    integration_points = db.relationship('IntegrationPoint', secondary=integration_tag, back_populates='tags')

    def __repr__(self):
        return f"<Tag(name={self.name})>"
    
class UserRole(db.Model):
    __tablename__ = 'user_roles'

    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))

    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    component = db.relationship('Component', back_populates='user_roles')

    def __repr__(self):
        return f"<UserRole(role_name={self.role_name})>"

class UpdateLog(db.Model):
    __tablename__ = 'update_logs'

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=False)
    updated_by = db.Column(db.String(100), nullable=False)
    update_date = db.Column(db.DateTime, default=datetime.utcnow)
    change_summary = db.Column(db.String(1000))

    component = db.relationship('Component', back_populates='update_logs')

    def __repr__(self):
        return f"<UpdateLog(component_id={self.component_id}, updated_by={self.updated_by})>"
