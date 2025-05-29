"""
Component & Vendor Loader

Usage:
    python load_components.py                                    # Load from default file (skip duplicates)
    python load_components.py --file path/to/file.json           # Load from a custom JSON file
    python load_components.py --replace                          # Replace all components and vendors with data from default file
    python load_components.py --replace --file path/to/file.json # Replace all components and vendors with data from custom file
    python load_components.py --clear                            # Clear all component and vendor records (does not delete functions)

Features:
    - Loads vendors and components from a JSON file containing "vendors" and/or "components" keys.
    - Links each component to its vendors and function (by name; creates function if missing).
    - Idempotent: running multiple times will not duplicate data.
    - Can be used with files containing only vendors, only components, or both.
    - Parent/child relationships for components are automatically established.

Expected file structure:
{
    "vendors":    [ { ... }, ... ],
    "components": [ { ... }, ... ]
}

Notes:
    - To add or update related functions, ensure functions exist or allow the script to create them (with default properties).
    - If using --replace or --clear, all existing components and vendors will be deleted first.
"""
import json
import os
from datetime import datetime
from app import create_app, db
from app.models.tran import Vendor, Component, Function, Criticality

def load_vendors(vendors_data):
    """
    Load vendors from a list of dicts.
    Returns dict mapping vendor JSON id to Vendor object.
    """
    print(f"Processing {len(vendors_data)} vendors...")
    id_map = {}
    for v in vendors_data:
        vendor = Vendor.query.filter_by(name=v['name']).first()
        if vendor:
            print(f"  Vendor '{v['name']}' already exists.")
        else:
            vendor = Vendor(
                name=v['name'],
                website=v.get('website'),
                vendor_email=v.get('vendor_email'),
                vendor_phone=v.get('vendor_phone'),
                contact_name=v.get('contact_name'),
                contact_email=v.get('contact_email'),
                contact_phone=v.get('contact_phone'),
                description=v.get('description'),
            )
            db.session.add(vendor)
            print(f"  Added vendor: {vendor.name}")
            db.session.flush()  # So we get the .id right away
        id_map[v['id']] = vendor
    db.session.commit()
    return id_map

def get_or_create_function(function_name):
    """
    Find a Function by name or create it (with default description and medium criticality).
    """
    if not function_name:
        return None
    function = Function.query.filter_by(name=function_name).first()
    if function:
        return function
    function = Function(
        name=function_name,
        description="Auto-added by loader.",
        criticality=Criticality.medium,
        functional_area_id=None  # Adjust if you want to auto-assign
    )
    db.session.add(function)
    db.session.flush()
    print(f"    Created function: {function_name}")
    return function

def load_components(components_data, vendor_id_map):
    """
    Load components and set up parent/child relationships and function links.
    """
    print(f"Processing {len(components_data)} components...")
    id_map = {}
    # Pass 1: Add all components (without parent/child links)
    for c in components_data:
        component = Component.query.filter_by(name=c['name']).first()
        if component:
            print(f"  Component '{c['name']}' already exists.")
            id_map[c['id']] = component
            continue

        # Pick first vendor in list (adjust if you want multi-vendor support)
        vendor = None
        vendor_ids = c.get('vendors') or []
        for v_id in vendor_ids:
            vendor = vendor_id_map.get(v_id)
            if vendor:
                break
        # Parse deployment_date (accept "YYYY-MM-DD" or just "YYYY")
        deployment_date = None
        if c.get('deployment_date'):
            dt = c['deployment_date']
            try:
                deployment_date = datetime.strptime(dt, '%Y-%m-%d').date()
            except Exception:
                try:
                    deployment_date = datetime.strptime(dt, '%Y').date()
                except Exception:
                    deployment_date = None

        component = Component(
            name=c['name'],
            description=c.get('description'),
            version=c.get('version'),
            deployment_date=deployment_date,
            update_frequency=c.get('update_frequency'),
            known_issues=c.get('known_issues'),
            is_composite=c.get('is_composite', False),
            vendor_id=vendor.id if vendor else None,
            additional_metadata=c.get('additional_metadata'),
        )
        db.session.add(component)
        db.session.flush()  # Ensure .id is available for linking

        # Function linkage (single function)
        function_name = c.get('function_name')
        if function_name:
            function = get_or_create_function(function_name)
            if function and function not in component.functions:
                component.functions.append(function)
                print(f"    Linked function '{function.name}' to component '{component.name}'")

        id_map[c['id']] = component
        print(f"  Added component: {component.name}")

    db.session.commit()

    # Pass 2: Handle parent/child (child_components)
    for c in components_data:
        parent = id_map.get(c['id'])
        for child_id in c.get('child_components', []):
            child = id_map.get(child_id)
            if child:
                child.parent_component_id = parent.id
                print(f"    Linked child '{child.name}' to parent '{parent.name}'")
    db.session.commit()

def load_from_json(json_file_path):
    """
    Main load function.
    """
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    vendors_data = data.get('vendors', [])
    components_data = data.get('components', [])

    # Load vendors first, get vendor id map
    vendor_id_map = {}
    if vendors_data:
        vendor_id_map = load_vendors(vendors_data)
    else:
        # If vendors weren't provided, build id map from DB
        vendor_id_map = {v.id: v for v in Vendor.query.all()}

    if components_data:
        load_components(components_data, vendor_id_map)

def main():
    import sys
    app = create_app()
    with app.app_context():
        if len(sys.argv) > 1:
            json_file = sys.argv[1]
        else:
            json_file = os.path.join(
                os.path.dirname(__file__),
                '..', 'app', 'models', 'data', 'components.json'
            )
        print(f"Loading data from: {json_file}")
        load_from_json(json_file)
        print("Load complete.")

if __name__ == '__main__':
    main()
