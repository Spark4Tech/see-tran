#!/usr/bin/env python3
"""
Functional Areas Data Loader

Usage:
    python load_functional_areas.py functional_areas.json
"""

import json
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import FunctionalArea

def load_functional_areas_from_file(filename):
    """Load functional areas from JSON file"""
    
    app = create_app()
    
    with app.app_context():
        print(f"📁 Loading functional areas from {filename}...")
        
        # Load JSON data
        with open(filename, 'r') as f:
            data = json.load(f)
        
        stats = {'added': 0, 'skipped': 0}
        
        for fa_data in data.get('functional_areas', []):
            # Check if functional area already exists
            existing = FunctionalArea.query.filter_by(name=fa_data['name']).first()
            if existing:
                print(f"  ⚠️  Functional Area '{fa_data['name']}' already exists, skipping")
                stats['skipped'] += 1
                continue
            
            # Create functional area
            functional_area = FunctionalArea(
                name=fa_data['name'],
                description=fa_data.get('description')
            )
            
            db.session.add(functional_area)
            stats['added'] += 1
            print(f"  ➕ Added functional area: {functional_area.name}")
        
        try:
            db.session.commit()
            print(f"\n✅ Functional areas loaded successfully!")
            print(f"📊 Summary:")
            print(f"   Added: {stats['added']}")
            print(f"   Skipped: {stats['skipped']}")
            print(f"   Total Functional Areas: {FunctionalArea.query.count()}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Load functional areas into the database.")
    parser.add_argument('file', help='JSON file to load')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        return
    
    success = load_functional_areas_from_file(args.file)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()