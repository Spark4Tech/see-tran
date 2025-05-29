#!/usr/bin/env python3
"""
Category Data Loader

Usage:
    python load_categories.py                             # Load categories (skip duplicates)
    python load_categories.py --replace                   # Replace all existing category data
    python load_categories.py --clear                     # Clear all category data only
    python load_categories.py --file categories.json      # Load from custom file
"""

import json
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import FunctionalArea

def normalize_name(name):
    return name.strip().lower()

def load_categories_from_file(filename, replace_mode=False):
    """Load categories from a JSON file."""
    if replace_mode:
        clear_category_data()

    print(f"📥 Loading categories from {filename}...")

    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False

    stats = {'added': 0, 'skipped': 0, 'errors': 0}
    existing_names = {
        normalize_name(cat.name): cat for cat in Category.query.all()
    }

    for cat in data.get("categories", []):
        name = cat["name"]
        key = normalize_name(name)

        if key in existing_names:
            print(f"⚠️  Skipping existing category: {name}")
            stats['skipped'] += 1
            continue

        fa_name = cat.get("functional_area")
        fa = FunctionalArea.query.filter_by(name=fa_name).first()

        if not fa:
            print(f"❌ Functional area not found: {fa_name} (required for category '{name}')")
            stats['errors'] += 1
            continue

        category = Category(
            name=name,
            description=cat.get("description"),
            functional_area=fa
        )
        db.session.add(category)
        stats['added'] += 1
        print(f"➕ Added category: {name}")

    try:
        db.session.commit()
        print("\n✅ Categories loaded successfully!")
        print("📊 Summary:")
        print(f"   Added: {stats['added']}")
        print(f"   Skipped: {stats['skipped']}")
        print(f"   Errors: {stats['errors']}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error saving to database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Load category data into the database.")
    parser.add_argument('--replace', action='store_true', help='Replace all category data')
    parser.add_argument('--clear', action='store_true', help='Clear all category data only')
    parser.add_argument('--file', default='categories.json', help='Path to JSON file')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompts')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.clear:
            if not args.confirm:
                resp = input("⚠️  This will delete ALL categories. Type 'YES' to continue: ")
                if resp != "YES":
                    print("❌ Operation cancelled.")
                    return
            clear_category_data()
            return

        if args.replace and not args.confirm:
            resp = input("⚠️  This will REPLACE all category data. Type 'YES' to continue: ")
            if resp != "YES":
                print("❌ Operation cancelled.")
                return

        success = load_categories_from_file(args.file, replace_mode=args.replace)
        if success:
            print(f"\n📈 Total Categories in DB: {Category.query.count()}")
        else:
            sys.exit(1)

if __name__ == '__main__':
    main()
