#!/usr/bin/env python3
"""
Integration Point Data Loader

Usage:
    python load_integrations.py                           # Load integration points (skip existing)
    python load_integrations.py --replace                 # Replace all integration point data
    python load_integrations.py --clear                   # Clear all integration point data
    python load_integrations.py --file integrations.json  # Load from a specified JSON file

This script loads integration point records into the database, including:
- Associated standards (will create if not found)
- Associated tags (will create if not found)

Expected JSON structure:
{
  "integration_points": [
    {
      "name": "CAD/AVL API",
      "description": "Two-paragraph detailed explanation of the interface and its use.",
      "standards": [
        {
          "name": "REST",
          "description": "Describes the architectural style used for APIs.",
          "website": "https://restfulapi.net/"
        }
      ],
      "tags": ["Internal API", "AVL"]
    }
  ]
}
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import IntegrationPoint, Standard, Tag, TagGroup

def normalize_name(name):
    return name.strip().lower()

def clear_data():
    """Deletes all integration points"""
    print("🗑️  Clearing all integration points...")
    IntegrationPoint.query.delete()
    db.session.commit()
    print("✅ All integration points deleted.")

def get_or_create_standard(standard_data):
    """Fetch an existing standard or create a new one"""
    name = standard_data['name']
    standard = Standard.query.filter_by(name=name).first()
    if not standard:
        standard = Standard(
            name=name,
            description=standard_data.get('description'),
            standard_url=standard_data.get('website'),
            version=None
        )
        db.session.add(standard)
    return standard

def get_or_create_tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first()
    if tag:
        return tag

    # Ensure default tag group exists
    group_name = "Integration Tags"
    tag_group = TagGroup.query.filter_by(name=group_name).first()
    if not tag_group:
        tag_group = TagGroup(name=group_name, description="Tags related to integration points")
        db.session.add(tag_group)
        db.session.flush()  # get ID before using in Tag

    tag = Tag(name=tag_name, tag_group=tag_group)
    db.session.add(tag)
    return tag

def load_integration_points_from_file(filename, replace_mode=False):
    if replace_mode:
        clear_data()

    print(f"📥 Loading integration points from {filename}...")

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
        normalize_name(ip.name): ip for ip in IntegrationPoint.query.all()
    }

    for ip_data in data.get("integration_points", []):
        norm = normalize_name(ip_data["name"])
        if norm in existing:
            print(f"⚠️  Skipping existing integration point: {ip_data['name']}")
            stats['skipped'] += 1
            continue

        ip = IntegrationPoint(
            name=ip_data["name"],
            description=ip_data.get("description")
        )

        for std in ip_data.get("standards", []):
            ip.standards.append(get_or_create_standard(std))

        for tag_name in ip_data.get("tags", []):
            ip.tags.append(get_or_create_tag(tag_name))

        db.session.add(ip)
        stats['added'] += 1
        print(f"➕ Added integration point: {ip.name}")

    try:
        db.session.commit()
        print("\n✅ Integration points loaded successfully!")
        print("📊 Summary:")
        print(f"   Added: {stats['added']}")
        print(f"   Skipped: {stats['skipped']}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error committing changes: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Load integration points into the database.")
    parser.add_argument('--replace', action='store_true', help='Replace all existing data')
    parser.add_argument('--clear', action='store_true', help='Clear data without loading')
    parser.add_argument('--file', default='integration_points.json', help='JSON file to load')
    parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompts')

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        if args.clear:
            if not args.confirm:
                confirm = input("⚠️  This will delete ALL integration points. Type 'YES' to confirm: ")
                if confirm != 'YES':
                    print("❌ Operation cancelled.")
                    return
            clear_data()
            return

        if args.replace and not args.confirm:
            confirm = input("⚠️  This will REPLACE all integration points. Type 'YES' to confirm: ")
            if confirm != 'YES':
                print("❌ Operation cancelled.")
                return

        success = load_integration_points_from_file(args.file, replace_mode=args.replace)

        if success:
            print(f"\n📈 Total Integration Points: {IntegrationPoint.query.count()}")
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()