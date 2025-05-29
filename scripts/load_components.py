#!/usr/bin/env python3
"""
Components Data Loader

Usage:
    python load_components.py components.json
"""

import json
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import Component, Vendor

def load_components_from_file(filename):
    """Load components from JSON file"""
    
    app = create_app()
    
    with app.app_context():
        print(f"🔧 Loading components from {filename}...")
        
        # Load JSON data
        with open(filename, 'r') as f:
            data = json.load(f)
        
        stats = {'added': 0, 'skipped': 0}
        
        for comp_data in data.get('components', []):
            # Check if component already exists
            existing = Component.query.filter_by(name=comp_data['name']).first()
            if existing:
                print(f"  ⚠️  Component '{comp_data['name']}' already exists, skipping")
                stats['skipped'] += 1
                continue
            
            # Find vendor
            vendor = None
            if comp_data.get('vendor'):
                vendor = Vendor.query.filter_by(name=comp_data['vendor']).first()
                if not vendor:
                    print(f"    ❌ Vendor not found: {comp_data['vendor']}")
                    continue
            
            # Parse deployment date
            deployment_date = None
            if comp_data.get('deployment_date'):
                try:
                    deployment_date = datetime.strptime(comp_data['deployment_date'], '%Y-%m-%d').date()
                except ValueError:
                    print(f"    ⚠️  Invalid date format for {comp_data['name']}: {comp_data['deployment_date']}")
            
            # Create component
            component = Component(
                name=comp_data['name'],
                description=comp_data.get('description'),
                version=comp_data.get('version'),
                deployment_date=deployment_date,
                update_frequency=comp_data.get('update_frequency'),
                known_issues=comp_data.get('known_issues'),
                is_composite=comp_data.get('is_composite', False),
                vendor_id=vendor.id if vendor else None,
                additional_metadata=comp_data.get('additional_metadata')
            )
            
            db.session.add(component)
            stats['added'] += 1
            vendor_name = vendor.name if vendor else "No Vendor"
            print(f"  ➕ Added component: {component.name} ({vendor_name})")
        
        try:
            db.session.commit()
            print(f"\n✅ Components loaded successfully!")
            print(f"📊 Summary:")
            print(f"   Added: {stats['added']}")
            print(f"   Skipped: {stats['skipped']}")
            print(f"   Total Components: {Component.query.count()}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Load components into the database.")
    parser.add_argument('file', help='JSON file to load')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        return
    
    success = load_components_from_file(args.file)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()