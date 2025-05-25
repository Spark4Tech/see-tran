# models/tran.py

from datetime import datetime
from app import db
import enum

# Association Tables
system_integration = db.Table(
    'system_integration',
    db.Column('system_id', db.Integer, db.ForeignKey('systems.id'), primary_key=True),
    db.Column('integration_point_id', db.Integer, db.ForeignKey('integration_points.id'), primary_key=True)
)

system_function = db.Table(
    'system_function',
    db.Column('system_id', db.Integer, db.ForeignKey('systems.id'), primary_key=True),
    db.Column('function_id', db.Integer, db.ForeignKey('functions.id'), primary_key=True)
)

system_tag = db.Table(
    'system_tag',
    db.Column('system_id', db.Integer, db.ForeignKey('systems.id'), primary_key=True),
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
class TransitSystem(db.Model):
    __tablename__ = 'transit_systems'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100))
    description = db.Column(db.String(500))

    functional_areas = db.relationship('FunctionalArea', back_populates='transit_system', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<TransitSystem(name={self.name}, location={self.location})>"

class FunctionalArea(db.Model):
    __tablename__ = 'functional_areas'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))

    transit_system_id = db.Column(db.Integer, db.ForeignKey('transit_systems.id'), nullable=False)
    transit_system = db.relationship('TransitSystem', back_populates='functional_areas')

    categories = db.relationship('Category', back_populates='functional_area', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<FunctionalArea(name={self.name})>"

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))

    functional_area_id = db.Column(db.Integer, db.ForeignKey('functional_areas.id'), nullable=False)
    functional_area = db.relationship('FunctionalArea', back_populates='categories')

    functions = db.relationship('Function', back_populates='category', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Category(name={self.name})>"

class Function(db.Model):
    __tablename__ = 'functions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    criticality = db.Column(db.Enum(Criticality), default=Criticality.medium, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    category = db.relationship('Category', back_populates='functions')

    systems = db.relationship('System', secondary=system_function, back_populates='functions')

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

    systems = db.relationship('System', back_populates='vendor', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Vendor(name={self.name})>"


class System(db.Model):
    __tablename__ = 'systems'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(50))
    deployment_date = db.Column(db.Date)
    update_frequency = db.Column(db.String(50))
    known_issues = db.Column(db.String(500))
    additional_metadata = db.Column(db.JSON)

    functional_area_id = db.Column(db.Integer, db.ForeignKey('functional_areas.id'))
    functional_area = db.relationship('FunctionalArea')

    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    vendor = db.relationship('Vendor', back_populates='systems')

    functions = db.relationship('Function', secondary=system_function, back_populates='systems')
    integration_points = db.relationship('IntegrationPoint', secondary=system_integration, back_populates='systems')
    tags = db.relationship('Tag', secondary=system_tag, back_populates='systems')

    user_roles = db.relationship('UserRole', back_populates='system', cascade='all, delete-orphan')
    update_logs = db.relationship('UpdateLog', back_populates='system', cascade='all, delete-orphan')

    def add_metadata(self, key: str, value: str):
        if not self.additional_metadata:
            self.additional_metadata = {}
        self.additional_metadata[key] = value

    def __repr__(self):
        return f"<System(name={self.name}, version={self.version})>"

class IntegrationPoint(db.Model):
    __tablename__ = 'integration_points'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))

    standards = db.relationship('Standard', secondary=integration_standard, back_populates='integration_points')
    systems = db.relationship('System', secondary=system_integration, back_populates='integration_points')
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

    systems = db.relationship('System', secondary=system_tag, back_populates='tags')
    integration_points = db.relationship('IntegrationPoint', secondary=integration_tag, back_populates='tags')

    def __repr__(self):
        return f"<Tag(name={self.name})>"
    
class UserRole(db.Model):
    __tablename__ = 'user_roles'

    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))

    system_id = db.Column(db.Integer, db.ForeignKey('systems.id'))
    system = db.relationship('System', back_populates='user_roles')

    def __repr__(self):
        return f"<UserRole(role_name={self.role_name})>"

class UpdateLog(db.Model):
    __tablename__ = 'update_logs'

    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.Integer, db.ForeignKey('systems.id'), nullable=False)
    updated_by = db.Column(db.String(100), nullable=False)
    update_date = db.Column(db.DateTime, default=datetime.utcnow)
    change_summary = db.Column(db.String(1000))

    system = db.relationship('System', back_populates='update_logs')

    def __repr__(self):
        return f"<UpdateLog(system_id={self.system_id}, updated_by={self.updated_by})>"
