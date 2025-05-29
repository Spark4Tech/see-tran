#!/usr/bin/env python3
"""
Vendors Data Loader

Usage:
    python load_vendors.py vendors.json
"""

import json
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import Vendor

def load_vendors_from_file(filename):
    """Load vendors from JSON file"""
    
    app = create_app()
    
    with app.app_context():
        print(f"🏢 Loading vendors from {filename}...")
        
        # Load JSON data
        with open(filename, 'r') as f:
            data = json.load(f)
        
        stats = {'added': 0, 'skipped': 0}
        
        for vendor_data in data.get('vendors', []):
            # Check if vendor already exists
            existing = Vendor.query.filter_by(name=vendor_data['name']).first()
            if existing:
                print(f"  ⚠️  Vendor '{vendor_data['name']}' already exists, skipping")
                stats['skipped'] += 1
                continue
            
            # Create vendor
            vendor = Vendor(
                name=vendor_data['name'],
                description=vendor_data.get('description'),
                website=vendor_data.get('website'),
                vendor_email=vendor_data.get('vendor_email'),
                vendor_phone=vendor_data.get('vendor_phone'),
                contact_name=vendor_data.get('contact_name'),
                contact_email=vendor_data.get('contact_email'),
                contact_phone=vendor_data.get('contact_phone')
            )
            
            db.session.add(vendor)
            stats['added'] += 1
            print(f"  ➕ Added vendor: {vendor.name}")
        
        try:
            db.session.commit()
            print(f"\n✅ Vendors loaded successfully!")
            print(f"📊 Summary:")
            print(f"   Added: {stats['added']}")
            print(f"   Skipped: {stats['skipped']}")
            print(f"   Total Vendors: {Vendor.query.count()}")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Load vendors into the database.")
    parser.add_argument('file', help='JSON file to load')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        return
    
    success = load_vendors_from_file(args.file)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()