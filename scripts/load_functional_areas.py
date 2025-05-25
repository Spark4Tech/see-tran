#!/usr/bin/env python3
"""
Functional Area Loader

Usage:
    python load_functional_areas.py                            # Load data (skip duplicates)
    python load_functional_areas.py --replace                  # Replace all functional areas
    python load_functional_areas.py --clear                    # Clear all data only
    python load_functional_areas.py --file path/to/file.json   # Load from a custom JSON file
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import FunctionalArea, TransitSystem

def normalize(name):
    return name.strip().lower()

def clear_functional_area_data():
    """Delete all functional areas."""
    print("🗑️  Clearing all functional areas...")
    FunctionalArea.query.delete()
    db.session.commit()
    print("✅ All functional area data cleared.")

def load_functional_areas(filename, replace_mode=False):
    """Load functional areas from JSON."""
    if replace_mode:
        clear_functional_area_data()

    print(f"📥 Loading functional areas from {filename}...")

    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {filename}: {e}")
        return False

    stats = {
        "added": 0,
        "skipped": 0,
        "missing_system": 0
    }

    existing = {
        normalize(fa.name): fa for fa in FunctionalArea.query.all()
    }

    for entry in data.get("functional_areas", []):
        name = entry.get("name")
        system_name = entry.get("transit_system")

        if not name or not system_name:
            print(f"⚠️  Skipping entry with missing name or transit system: {entry}")
            continue

        key = normalize(name)
        if key in existing:
            print(f"⚠️  Skipping existing functional area: {name}")
            stats["skipped"] += 1
            continue

        system = TransitSystem.query.filter_by(name=system_name).first()
        if not system:
            print(f"❌ Error: TransitSystem '{system_name}' not found for functional area '{name}'")
            stats["missing_system"] += 1
            continue

        fa = FunctionalArea(
            name=name,
            description=entry.get("description"),
            transit_system=system
        )
        db.session.add(fa)
        stats["added"] += 1
        print(f"➕ Added functional area: {fa.name}")

    try:
        db.session.commit()
        print("\n✅ Functional areas loaded successfully!")
        print("📊 Summary:")
        for k, v in stats.items():
            print(f"   {k.replace('_', ' ').title()}: {v}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error saving to database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Load functional areas into the database.")
    parser.add_argument("--replace", action="store_true", help="Replace all existing data")
    parser.add_argument("--clear", action="store_true", help="Clear functional area data only")
    parser.add_argument("--file", default="functional_areas.json", help="Path to JSON file")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.clear:
            if not args.confirm:
                confirm = input("⚠️  This will delete ALL functional area data! Type 'YES' to continue: ")
                if confirm != "YES":
                    print("❌ Operation cancelled.")
                    return
            clear_functional_area_data()
            return

        if args.replace and not args.confirm:
            confirm = input("⚠️  This will replace ALL existing data! Type 'YES' to continue: ")
            if confirm != "YES":
                print("❌ Operation cancelled.")
                return

        success = load_functional_areas(args.file, replace_mode=args.replace)
        if success:
            print(f"\n🎉 Total Functional Areas: {FunctionalArea.query.count()}")
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
