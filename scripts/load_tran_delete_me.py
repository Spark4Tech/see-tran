# scripts/load_tran.py
"""
Transit System Data Loader

Usage:
    python load_tran_data.py                    # Load data (skip duplicates)
    python load_tran_data.py --replace          # Replace all existing data
    python load_tran_data.py --clear            # Clear all data only
    python load_tran_data.py --file custom.json # Load from custom file
"""

import json
import argparse
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from app.models.tran import (
    TransitSystem, FunctionalArea, System, Vendor,
    IntegrationPoint, UserRole, UpdateLog
)

def clear_all_data():
    """Clear all data from the database in correct order to avoid foreign key conflicts."""
    print("🗑️  Clearing all existing data...")
    
    # Delete in reverse dependency order
    UpdateLog.query.delete()
    UserRole.query.delete()
    
    # Clear many-to-many relationships
    db.session.execute(db.text("DELETE FROM system_integration"))
    
    System.query.delete()
    IntegrationPoint.query.delete()
    FunctionalArea.query.delete()
    Vendor.query.delete()
    TransitSystem.query.delete()
    
    db.session.commit()
    print("✅ All data cleared successfully!")

def load_data_from_file(filename, replace_mode=False):
    """Load transit system data from JSON file."""
    
    if replace_mode:
        clear_all_data()
    
    print(f"📥 Loading data from {filename}...")
    
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"❌ Error: File '{filename}' not found!")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{filename}': {e}")
        return False
    
    stats = {
        'transit_systems': 0,
        'functional_areas': 0,
        'systems': 0,
        'vendors': 0,
        'integration_points': 0,
        'user_roles': 0,
        'skipped_duplicates': 0
    }
    
    for ts_data in data.get('transit_systems', []):
        # Check if transit system already exists (if not in replace mode)
        if not replace_mode:
            existing_ts = TransitSystem.query.filter_by(name=ts_data['name']).first()
            if existing_ts:
                print(f"⚠️  Skipping existing transit system: {ts_data['name']}")
                stats['skipped_duplicates'] += 1
                continue
        
        # Create transit system
        transit_system = TransitSystem(
            name=ts_data['name'],
            location=ts_data.get('location'),
            description=ts_data.get('description')
        )
        db.session.add(transit_system)
        stats['transit_systems'] += 1
        print(f"➕ Added transit system: {transit_system.name}")

        # Process functional areas
        for fa_data in ts_data.get('functional_areas', []):
            functional_area = FunctionalArea(
                name=fa_data['name'],
                description=fa_data.get('description'),
                transit_system=transit_system
            )
            db.session.add(functional_area)
            stats['functional_areas'] += 1
            print(f"  ➕ Added functional area: {functional_area.name}")

            # Process systems
            for sys_data in fa_data.get('systems', []):
                # Handle vendor
                vendor = None
                vendor_data = sys_data.get('vendor')
                if vendor_data:
                    vendor = Vendor.query.filter_by(name=vendor_data['name']).first()
                    if not vendor:
                        vendor = Vendor(
                            name=vendor_data['name'],
                            website=vendor_data.get('website'),
                            contact_info=vendor_data.get('contact_info'),
                            description=vendor_data.get('description')
                        )
                        db.session.add(vendor)
                        stats['vendors'] += 1
                        print(f"    ➕ Added vendor: {vendor.name}")

                # Handle deployment date
                deployment_date = None
                if sys_data.get('deployment_date'):
                    try:
                        deployment_date = datetime.strptime(
                            sys_data['deployment_date'], "%Y-%m-%d"
                        ).date()
                    except ValueError as e:
                        print(f"    ⚠️  Invalid date format for {sys_data['name']}: {e}")

                # Create system
                system = System(
                    name=sys_data['name'],
                    function=sys_data['function'],
                    version=sys_data.get('version'),
                    deployment_date=deployment_date,
                    update_frequency=sys_data.get('update_frequency'),
                    known_issues=sys_data.get('known_issues'),
                    additional_metadata=sys_data.get('additional_metadata'),
                    functional_area=functional_area,
                    vendor=vendor
                )
                db.session.add(system)
                stats['systems'] += 1
                print(f"    ➕ Added system: {system.name}")

                # Handle integration points
                for ip_data in sys_data.get('integration_points', []):
                    integration_point = IntegrationPoint.query.filter_by(
                        name=ip_data['name'],
                        standard=ip_data.get('standard')
                    ).first()
                    
                    if not integration_point:
                        integration_point = IntegrationPoint(
                            name=ip_data['name'],
                            standard=ip_data.get('standard'),
                            description=ip_data.get('description')
                        )
                        db.session.add(integration_point)
                        stats['integration_points'] += 1
                        print(f"      ➕ Added integration point: {integration_point.name}")
                    
                    system.integration_points.append(integration_point)

                # Handle user roles
                for ur_data in sys_data.get('user_roles', []):
                    user_role = UserRole(
                        role_name=ur_data['role_name'],
                        description=ur_data.get('description'),
                        system=system
                    )
                    db.session.add(user_role)
                    stats['user_roles'] += 1
                    print(f"      ➕ Added user role: {user_role.role_name}")

    # Commit all changes
    try:
        db.session.commit()
        print("\n✅ Data loaded successfully!")
        print("\n📊 Summary:")
        for key, value in stats.items():
            if value > 0:
                print(f"   {key.replace('_', ' ').title()}: {value}")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error loading data: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Load transit system data into database')
    parser.add_argument('--replace', action='store_true', 
                       help='Replace all existing data')
    parser.add_argument('--clear', action='store_true',
                       help='Clear all data without loading new data')
    parser.add_argument('--file', default='app/models/tran.json',
                       help='JSON file to load (default: app/models/tran.json)')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Handle clear-only mode
        if args.clear:
            if not args.confirm:
                response = input("⚠️  This will delete ALL data! Are you sure? (type 'YES' to confirm): ")
                if response != 'YES':
                    print("❌ Operation cancelled.")
                    return
            clear_all_data()
            return
        
        # Handle replace mode confirmation
        if args.replace and not args.confirm:
            response = input("⚠️  This will replace ALL existing data! Are you sure? (type 'YES' to confirm): ")
            if response != 'YES':
                print("❌ Operation cancelled.")
                return
        
        # Load data
        success = load_data_from_file(args.file, replace_mode=args.replace)
        
        if success:
            print(f"\n🎉 Data loading complete!")
            
            # Show current database stats
            print("\n📈 Current Database Stats:")
            print(f"   Transit Systems: {TransitSystem.query.count()}")
            print(f"   Functional Areas: {FunctionalArea.query.count()}")
            print(f"   Systems: {System.query.count()}")
            print(f"   Vendors: {Vendor.query.count()}")
            print(f"   Integration Points: {IntegrationPoint.query.count()}")
            print(f"   User Roles: {UserRole.query.count()}")
        else:
            sys.exit(1)

if __name__ == '__main__':
    main()