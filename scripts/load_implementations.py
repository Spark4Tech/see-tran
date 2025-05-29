#!/usr/bin/env python3
"""
Agency Function Implementations Data Loader

Usage:
    python load_implementations.py c_tran_implementations.json
"""

import json
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import Agency, Function, Component, AgencyFunctionImplementation

def load_implementations_from_file(filename):
    """Load agency function implementations from JSON file"""
    
    app = create_app()
    
    with app.app_context():
        print(f"🏛️ Loading agency implementations from {filename}...")
        
        # Load JSON data
        with open(filename, 'r') as f:
            data = json.load(f)
        
        stats = {'added': 0, 'skipped': 0, 'errors': 0}
        
        for impl_data in data.get('implementations', []):
            # Find agency
            agency = Agency.query.filter_by(name=impl_data['agency']).first()
            if not agency:
                print(f"    ❌ Agency not found: {impl_data['agency']}")
                stats['errors'] += 1
                continue
            
            # Find component
            component = Component.query.filter_by(name=impl_data['component']).first()
            if not component:
                print(f"    ❌ Component not found: {impl_data['component']}")
                stats['errors'] += 1
                continue
            
            # Find function
            function = Function.query.filter_by(name=impl_data['function']).first()
            if not function:
                print(f"    ❌ Function not found: {impl_data['function']}")
                stats['errors'] += 1
                continue
            
            # Check if implementation already exists
            existing = AgencyFunctionImplementation.query.filter_by(
                agency_id=agency.id,
                function_id=function.id,
                component_id=component.id
            ).first()
            
            if existing:
                print(f"    ⚠️  Implementation already exists: {agency.name} → {function.name} → {component.name}")
                stats['skipped'] += 1
                continue
            
            # Parse deployment date
            deployment_date = None
            if impl_data.get('deployment_date'):
                try:
                    deployment_date = datetime.strptime(impl_data['deployment_date'], '%Y-%m-%d').date()
                except ValueError:
                    print(f"    ⚠️  Invalid date format: {impl_data['deployment_date']}")
            
            # Create implementation
            implementation = AgencyFunctionImplementation(
                agency_id=agency.id,
                function_id=function.id,
                component_id=component.id,
                deployment_date=deployment_date,
                version=impl_data.get('version'),
                status=impl_data.get('status', 'Active'),
                deployment_notes=impl_data.get('deployment_notes'),
                implementation_notes=impl_data.get('implementation_notes'),
                additional_metadata=impl_data.get('additional_metadata')
            )
            
            db.session.add(implementation)
            stats['added'] += 1
            print(f"  ➕ Added implementation: {agency.name} → {function.name} → {component.name}")
        
        try:
            db.session.commit()
            print(f"\n✅ Agency implementations loaded successfully!")
            print(f"📊 Summary:")
            print(f"   Added: {stats['added']}")
            print(f"   Skipped: {stats['skipped']}")
            print(f"   Errors: {stats['errors']}")
            print(f"   Total Implementations: {AgencyFunctionImplementation.query.count()}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Load agency function implementations into the database.")
    parser.add_argument('file', help='JSON file to load')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        return
    
    success = load_implementations_from_file(args.file)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()