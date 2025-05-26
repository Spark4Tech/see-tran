#!/usr/bin/env python3
"""
System Loader

Usage:
    python scripts/load_systems.py --file ./app/models/data/systems_ctran.json --system "C-TRAN" [--replace]

Assumes systems.json format:
{
  "transit_system": "C-TRAN",
  "systems": [ ... ]
}
"""

import json
import argparse
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import System, Vendor, Function, FunctionalArea, TransitSystem

def normalize_name(name):
    return name.strip().lower()

def load_systems_from_file(filename, system_name, replace=False):
    print(f"📥 Loading systems from {filename} for transit system: {system_name}...")

    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read JSON: {e}")
        return False

    json_system_name = data.get('transit_system')
    if json_system_name and json_system_name.strip().lower() != system_name.strip().lower():
        print(f"❌ Mismatch: JSON is for '{json_system_name}', but you passed --system '{system_name}'")
        return False

    entries = data.get('systems', [])
    if not entries:
        print("❌ No 'systems' key or empty list in JSON.")
        return False

    # Get or create the TransitSystem
    transit_system = TransitSystem.query.filter_by(name=system_name).first()
    if not transit_system:
        print(f"➕ Creating new TransitSystem: {system_name}")
        transit_system = TransitSystem(name=system_name)
        db.session.add(transit_system)
        db.session.commit()

    if replace:
        print("🗑️ Deleting existing systems for this TransitSystem...")
        System.query.filter(
            System.functional_area.has(transit_system_id=transit_system.id)
        ).delete(synchronize_session=False)
        db.session.commit()

    vendors = {normalize_name(v.name): v for v in Vendor.query.all()}
    functions = {normalize_name(f.name): f for f in Function.query.all()}
    functional_areas = {
        normalize_name(fa.name): fa for fa in FunctionalArea.query.filter_by(transit_system_id=transit_system.id)
    }

    stats = {'added': 0, 'skipped': 0, 'missing_vendor': 0, 'missing_function': 0}

    for s in entries:
        name = s['name']
        vendor_name = s.get('vendor')
        vendor = vendors.get(normalize_name(vendor_name)) if vendor_name else None
        if vendor_name and not vendor:
            print(f"⚠️  Missing vendor: {vendor_name} for system '{name}'")
            stats['missing_vendor'] += 1
            continue

        fa_name = s['functional_area']
        functional_area = functional_areas.get(normalize_name(fa_name))
        if not functional_area:
            functional_area = FunctionalArea(name=fa_name, transit_system=transit_system)
            db.session.add(functional_area)
            db.session.flush()
            functional_areas[normalize_name(fa_name)] = functional_area
            print(f"➕ Created FunctionalArea: {fa_name}")

        # Check if system exists already under same name + functional_area
        existing = System.query.filter_by(name=name, functional_area_id=functional_area.id).first()
        if existing:
            print(f"⏭️  Skipping existing system: {name}")
            stats['skipped'] += 1
            continue

        deployment_date = None
        if s.get('deployment_date'):
            try:
                deployment_date = datetime.strptime(s['deployment_date'], "%Y-%m-%d").date()
            except ValueError:
                print(f"⚠️  Invalid date format for '{name}': {s['deployment_date']}")

        system = System(
            name=name,
            version=s.get('version'),
            deployment_date=deployment_date,
            update_frequency=s.get('update_frequency'),
            known_issues=s.get('known_issues'),
            functional_area=functional_area,
            vendor=vendor
        )

        # Attach functions
        func_names = s.get('functions', [])
        for fname in func_names:
            fobj = functions.get(normalize_name(fname))
            if not fobj:
                print(f"⚠️  Missing function: {fname} for system '{name}'")
                stats['missing_function'] += 1
                continue
            system.functions.append(fobj)

        db.session.add(system)
        stats['added'] += 1
        print(f"✅ Added system: {name}")

    try:
        db.session.commit()
        print("\n🎉 Systems loaded successfully!")
        print("📊 Summary:")
        for k, v in stats.items():
            print(f"   {k.title()}: {v}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ DB commit failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Load systems for a transit system.')
    parser.add_argument('--file', required=True, help='Path to systems JSON file')
    parser.add_argument('--system', required=True, help='Transit system name (e.g. C-TRAN)')
    parser.add_argument('--replace', action='store_true', help='Replace all existing systems for the given system')

    args = parser.parse_args()
    app = create_app()

    with app.app_context():
        success = load_systems_from_file(args.file, args.system, replace=args.replace)
        if not success:
            sys.exit(1)

if __name__ == '__main__':
    main()