#!/usr/bin/env python3
"""
Transit System Data Loader

Usage:
    python load_transit_systems.py                           # Load systems (skip duplicates)
    python load_transit_systems.py --replace                 # Replace all systems
    python load_transit_systems.py --clear                   # Clear all system data
    python load_transit_systems.py --file systems.json       # Load from custom file
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import TransitSystem

def normalize_name(name):
    """Case-insensitive name normalization"""
    return name.strip().lower()

def clear_data():
    """Deletes all transit systems"""
    print("🗑️  Clearing all transit systems...")
    TransitSystem.query.delete()
    db.session.commit()
    print("✅ All transit systems deleted.")

def load_transit_systems_from_file(filename, replace_mode=False):
    if replace_mode:
        clear_data()

    print(f"📥 Loading transit systems from {filename}...")

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
        normalize_name(ts.name): ts for ts in TransitSystem.query.all()
    }

    for ts_data in data.get("transit_systems", []):
        norm = normalize_name(ts_data["name"])
        if norm in existing:
            print(f"⚠️  Skipping existing transit system: {ts_data['name']}")
            stats['skipped'] += 1
            continue

        # All fields present in your model
        system = TransitSystem(
            name=ts_data['name'],
            location=ts_data.get('location'),
            description=ts_data.get('description'),
            website=ts_data.get('website'),
            ceo=ts_data.get('ceo'),
            address_hq=ts_data.get('address_hq'),
            phone_number=ts_data.get('phone_number'),
            transit_map_link=ts_data.get('transit_map_link')
        )
        db.session.add(system)
        stats['added'] += 1
        print(f"➕ Added transit system: {system.name}")

    try:
        db.session.commit()
        print("\n✅ Transit systems loaded successfully!")
        print("📊 Summary:")
        print(f"   Added: {stats['added']}")
        print(f"   Skipped: {stats['skipped']}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error committing changes: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Load transit systems into the database.")
    parser.add_argument('--replace', action='store_true', help='Replace all existing data')
    parser.add_argument('--clear', action='store_true', help='Clear data without loading')
    parser.add_argument('--file', default='systems.json', help='JSON file to load')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompts')

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        if args.clear:
            if not args.confirm:
                confirm = input("⚠️  This will delete ALL transit systems. Type 'YES' to confirm: ")
                if confirm != 'YES':
                    print("❌ Operation cancelled.")
                    return
            clear_data()
            return

        if args.replace and not args.confirm:
            confirm = input("⚠️  This will REPLACE all transit systems. Type 'YES' to confirm: ")
            if confirm != 'YES':
                print("❌ Operation cancelled.")
                return

        success = load_transit_systems_from_file(args.file, replace_mode=args.replace)

        if success:
            print(f"\n📈 Total Transit Systems: {TransitSystem.query.count()}")
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
