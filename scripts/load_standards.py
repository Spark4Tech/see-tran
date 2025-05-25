#!/usr/bin/env python3
"""
Standard Data Loader

Usage:
    python load_standards.py                          # Load standards (skip duplicates)
    python load_standards.py --replace                # Replace all standard data
    python load_standards.py --clear                  # Clear all standard data only
    python load_standards.py --file standards.json    # Load from custom file
"""

import json
import argparse
import sys
import os

# Adjust path so script can import app context
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.tran import Standard

def normalize_name(name):
    """Normalize names for case-insensitive comparison."""
    return name.strip().lower()

def clear_standard_data():
    """Clear all standards from the database."""
    print("🗑️  Clearing all standard data...")
    Standard.query.delete()
    db.session.commit()
    print("✅ All standard data cleared.")

def load_standards_from_file(filename, replace_mode=False):
    """Load standards from the given JSON file."""
    if replace_mode:
        clear_standard_data()

    print(f"📥 Loading standards from {filename}...")

    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format in {filename}: {e}")
        return False

    stats = {
        'standards_added': 0,
        'standards_skipped': 0
    }

    existing_names = {
        normalize_name(s.name): s for s in Standard.query.all()
    }

    for item in data.get('standards', []):
        norm = normalize_name(item['name'])
        if norm in existing_names:
            print(f"⚠️  Skipping existing standard: {item['name']}")
            stats['standards_skipped'] += 1
            continue

        standard = Standard(
            name=item['name'],
            version=item.get('version'),
            description=item.get('description'),
            standard_url=item.get('standard_url')
        )
        db.session.add(standard)
        stats['standards_added'] += 1
        print(f"➕ Added standard: {standard.name}")

    try:
        db.session.commit()
        print("\n✅ Standards loaded successfully!")
        print("📊 Summary:")
        print(f"   Standards Added: {stats['standards_added']}")
        print(f"   Standards Skipped: {stats['standards_skipped']}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error committing standards: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Load standards into the database.')
    parser.add_argument('--replace', action='store_true', help='Replace all standard data')
    parser.add_argument('--clear', action='store_true', help='Clear all standard data')
    parser.add_argument('--file', default='standards.json', help='Path to JSON file with standards')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompts')

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        if args.clear:
            if not args.confirm:
                resp = input("⚠️  This will delete ALL standard data! Type 'YES' to continue: ")
                if resp != 'YES':
                    print("❌ Operation cancelled.")
                    return
            clear_standard_data()
            return

        if args.replace and not args.confirm:
            resp = input("⚠️  This will REPLACE all standard data! Type 'YES' to continue: ")
            if resp != 'YES':
                print("❌ Operation cancelled.")
                return

        success = load_standards_from_file(args.file, replace_mode=args.replace)

        if success:
            print("\n🎉 Standards loading complete!")
            print(f"📈 Total Standards in DB: {Standard.query.count()}")
        else:
            sys.exit(1)

if __name__ == '__main__':
    main()
