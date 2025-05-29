#!/usr/bin/env python3
"""
Agency Data Loader

Usage:
    python load_agencies.py                           # Load agencies (skip duplicates)
    python load_agencies.py --replace                 # Replace all agencies
    python load_agencies.py --clear                   # Clear all agency data
    python load_agencies.py --file agencies.json      # Load from custom file
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import Agency

def normalize_name(name):
    """Case-insensitive name normalization"""
    return name.strip().lower()

def clear_data():
    """Deletes all agencies"""
    print("🗑️  Clearing all agencies...")
    Agency.query.delete()
    db.session.commit()
    print("✅ All agencies deleted.")

def load_agencies_from_file(filename, replace_mode=False):
    if replace_mode:
        clear_data()

    print(f"📥 Loading agencies from {filename}...")

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
        'added': 0,
        'skipped': 0
    }

    existing = {
        normalize_name(agency.name): agency for agency in Agency.query.all()
    }

    for agency_data in data.get("agencies", []):
        norm = normalize_name(agency_data["name"])
        if norm in existing:
            print(f"⚠️  Skipping existing agency: {agency_data['name']}")
            stats['skipped'] += 1
            continue

        # All fields present in your Agency model
        agency = Agency(
            name=agency_data['name'],
            location=agency_data.get('location'),
            description=agency_data.get('description'),
            website=agency_data.get('website'),
            ceo=agency_data.get('ceo'),
            address_hq=agency_data.get('address_hq'),
            phone_number=agency_data.get('phone_number'),
            transit_map_link=agency_data.get('transit_map_link'),
            contact_email=agency_data.get('contact_email'),
            contact_phone=agency_data.get('contact_phone'),
            contact_name=agency_data.get('contact_name'),
            additional_metadata=agency_data.get('additional_metadata')
        )
        db.session.add(agency)
        stats['added'] += 1
        print(f"➕ Added agency: {agency.name}")

    try:
        db.session.commit()
        print("\n✅ Agencies loaded successfully!")
        print("📊 Summary:")
        print(f"   Added: {stats['added']}")
        print(f"   Skipped: {stats['skipped']}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error committing changes: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Load agencies into the database.")
    parser.add_argument('--replace', action='store_true', help='Replace all existing data')
    parser.add_argument('--clear', action='store_true', help='Clear data without loading')
    parser.add_argument('--file', default='agencies.json', help='JSON file to load')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompts')

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        if args.clear:
            if not args.confirm:
                confirm = input("⚠️  This will delete ALL agencies. Type 'YES' to confirm: ")
                if confirm != 'YES':
                    print("❌ Operation cancelled.")
                    return
            clear_data()
            return

        if args.replace and not args.confirm:
            confirm = input("⚠️  This will REPLACE all agencies. Type 'YES' to confirm: ")
            if confirm != 'YES':
                print("❌ Operation cancelled.")
                return

        success = load_agencies_from_file(args.file, replace_mode=args.replace)

        if success:
            print(f"\n📈 Total Agencies: {Agency.query.count()}")
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()