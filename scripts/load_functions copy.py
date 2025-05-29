#!/usr/bin/env python3
"""
Function Loader

Usage:
    python load_functions.py                          # Load functions (skip duplicates)
    python load_functions.py --replace                # Replace all function data
    python load_functions.py --clear                  # Clear all function data
    python load_functions.py --file functions.json    # Load from custom JSON file
"""

import json
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import Function, Criticality

def normalize_name(name):
    return name.strip().lower()

def clear_function_data():
    """Clear all functions."""
    print("🗑️  Clearing all functions...")
    db.session.execute(db.text("DELETE FROM system_function"))  # Clear association table
    Function.query.delete()
    db.session.commit()
    print("✅ All function data cleared.")

def load_functions_from_file(filename, replace_mode=False):
    """Load functions from a JSON file."""
    if replace_mode:
        clear_function_data()

    print(f"📥 Loading functions from {filename}...")

    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {filename}: {e}")
        return False

    stats = {'added': 0, 'skipped': 0, 'missing_category': 0}
    existing = {normalize_name(f.name): f for f in Function.query.all()}
    categories = {normalize_name(c.name): c for c in Category.query.all()}

    for fdata in data.get("functions", []):
        name = fdata['name']
        normalized = normalize_name(name)

        if normalized in existing:
            print(f"⚠️  Skipping existing function: {name}")
            stats['skipped'] += 1
            continue

        category_name = fdata.get('category_name')
        category = categories.get(normalize_name(category_name)) if category_name else None

        if not category:
            print(f"❌ Category not found: {category_name} (required for function '{name}')")
            stats['missing_category'] += 1
            continue

        criticality_value = fdata.get('criticality', 'medium').lower()
        try:
            criticality = Criticality[criticality_value]
        except KeyError:
            print(f"⚠️  Invalid criticality '{criticality_value}' for function '{name}', defaulting to medium.")
            criticality = Criticality.medium

        function = Function(
            name=name,
            description=fdata.get('description'),
            criticality=criticality,
            category=category
        )
        db.session.add(function)
        stats['added'] += 1
        print(f"➕ Added function: {name} (Criticality: {criticality.value})")

    try:
        db.session.commit()
        print("\n✅ Functions loaded successfully!")
        print("📊 Summary:")
        print(f"   Added: {stats['added']}")
        print(f"   Skipped (duplicates): {stats['skipped']}")
        print(f"   Missing Category: {stats['missing_category']}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error saving to database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Load functions into the database.')
    parser.add_argument('--replace', action='store_true', help='Replace all existing functions')
    parser.add_argument('--clear', action='store_true', help='Clear all function data')
    parser.add_argument('--file', default='functions.json', help='Path to functions JSON file')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompts')

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        if args.clear:
            if not args.confirm:
                resp = input("⚠️  This will delete ALL functions! Type 'YES' to confirm: ")
                if resp != 'YES':
                    print("❌ Operation cancelled.")
                    return
            clear_function_data()
            return

        if args.replace and not args.confirm:
            resp = input("⚠️  This will REPLACE all functions! Type 'YES' to confirm: ")
            if resp != 'YES':
                print("❌ Operation cancelled.")
                return

        success = load_functions_from_file(args.file, replace_mode=args.replace)

        if success:
            print("\n🎉 Function loading complete!")
            print(f"📈 Total Functions: {Function.query.count()}")
        else:
            sys.exit(1)

if __name__ == '__main__':
    main()
