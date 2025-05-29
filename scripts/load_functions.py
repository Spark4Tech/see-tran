#!/usr/bin/env python3
"""
Functions Data Loader

Usage:
    python load_functions.py functions.json
"""

import json
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import FunctionalArea, Function, Criticality

def load_functions_from_file(filename):
    """Load functions from JSON file"""
    
    app = create_app()
    
    with app.app_context():
        print(f"📋 Loading functions from {filename}...")
        
        # Load JSON data
        with open(filename, 'r') as f:
            data = json.load(f)
        
        stats = {'added': 0, 'skipped': 0}
        
        for func_data in data.get('functions', []):
            # Check if function already exists
            existing = Function.query.filter_by(name=func_data['name']).first()
            if existing:
                print(f"  ⚠️  Function '{func_data['name']}' already exists, skipping")
                stats['skipped'] += 1
                continue
            
            # Find the functional area
            functional_area = FunctionalArea.query.filter_by(
                name=func_data['functional_area']
            ).first()
            
            if not functional_area:
                print(f"  ❌ Functional area '{func_data['functional_area']}' not found for function '{func_data['name']}'")
                continue
            
            # Convert criticality string to enum
            criticality = getattr(Criticality, func_data.get('criticality', 'medium'))
            
            # Create function
            function = Function(
                name=func_data['name'],
                description=func_data.get('description'),
                criticality=criticality,
                functional_area_id=functional_area.id
            )
            
            db.session.add(function)
            stats['added'] += 1
            print(f"  ➕ Added function: {function.name} → {functional_area.name}")
        
        try:
            db.session.commit()
            print(f"\n✅ Functions loaded successfully!")
            print(f"📊 Summary:")
            print(f"   Added: {stats['added']}")
            print(f"   Skipped: {stats['skipped']}")
            print(f"   Total Functions: {Function.query.count()}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Load functions into the database.")
    parser.add_argument('file', help='JSON file to load')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        return
    
    success = load_functions_from_file(args.file)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()