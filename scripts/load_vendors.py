#!/usr/bin/env python3
"""
Vendor Data Loader

Usage:
    python load_vendors.py                          # Load vendors (skip duplicates)
    python load_vendors.py --replace                # Replace all vendor data
    python load_vendors.py --clear                  # Clear all vendor data only
    python load_vendors.py --file vendors.json      # Load from custom file
"""

import json
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import Vendor, System

def clear_vendor_data():
    """Clear all vendor data, handling foreign key constraints."""
    print("🗑️  Clearing all vendor data...")
    System.query.update({System.vendor_id: None})
    Vendor.query.delete()
    db.session.commit()
    print("✅ Vendor data cleared.")

def normalize_name(name):
    """Normalize vendor name for case-insensitive comparisons."""
    return name.strip().lower()

def load_vendors_from_file(filename, replace_mode=False):
    """Load vendors from a JSON file."""
    if replace_mode:
        clear_vendor_data()

    print(f"📥 Loading vendor data from {filename}...")

    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {filename}: {e}")
        return False

    stats = {
        'vendors_added': 0,
        'vendors_skipped': 0
    }

    existing_names = {
        normalize_name(v.name): v for v in Vendor.query.all()
    }

    for vendor_data in data.get('vendors', []):
        normalized = normalize_name(vendor_data['name'])
        if normalized in existing_names:
            print(f"⚠️  Skipping existing vendor: {vendor_data['name']}")
            stats['vendors_skipped'] += 1
            continue

        vendor = Vendor(
            name=vendor_data['name'],
            website=vendor_data.get('website'),
            vendor_email=vendor_data.get('vendor_email'),
            vendor_phone=vendor_data.get('vendor_phone'),
            contact_name=vendor_data.get('contact_name'),
            contact_email=vendor_data.get('contact_email'),
            contact_phone=vendor_data.get('contact_phone'),
            description=vendor_data.get('description')
        )
        db.session.add(vendor)
        stats['vendors_added'] += 1
        print(f"➕ Added vendor: {vendor.name}")

    try:
        db.session.commit()
        print("\n✅ Vendor data loaded successfully!")
        print("📊 Summary:")
        print(f"   Vendors Added: {stats['vendors_added']}")
        print(f"   Vendors Skipped: {stats['vendors_skipped']}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error committing vendor data: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Load vendor data into the database.')
    parser.add_argument('--replace', action='store_true', help='Replace all existing vendor data')
    parser.add_argument('--clear', action='store_true', help='Clear vendor data without loading')
    parser.add_argument('--file', default='vendors.json', help='Path to vendor JSON file')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompts')

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        if args.clear:
            if not args.confirm:
                resp = input("⚠️  This will delete ALL vendor data! Type 'YES' to continue: ")
                if resp != 'YES':
                    print("❌ Operation cancelled.")
                    return
            clear_vendor_data()
            return

        if args.replace and not args.confirm:
            resp = input("⚠️  This will REPLACE all vendor data! Type 'YES' to continue: ")
            if resp != 'YES':
                print("❌ Operation cancelled.")
                return

        success = load_vendors_from_file(args.file, replace_mode=args.replace)

        if success:
            print("\n🎉 Vendor loading complete!")
            print(f"📈 Total Vendors in DB: {Vendor.query.count()}")
        else:
            sys.exit(1)

if __name__ == '__main__':
    main()
