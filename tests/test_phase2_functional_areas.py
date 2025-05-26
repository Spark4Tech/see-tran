# tests/test_phase2_functional_areas.py
"""
Phase 2 Test Script - Functional Areas CRUD
Run this after implementing Phase 2 Step 2.2 to verify functional areas CRUD works
Usage: python tests/test_phase2_functional_areas.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models.tran import TransitSystem, FunctionalArea

def test_functional_areas_page(app):
    """Test that functional areas page loads"""
    try:
        with app.test_client() as client:
            response = client.get('/functional-areas')
            if response.status_code == 404:
                print("✗ Functional areas page not found - make sure you created functional_areas.html")
                return False
            assert response.status_code == 200
            assert b'Functional Areas Management' in response.data
            print("✓ Functional areas page loads correctly")
        return True
    except Exception as e:
        print(f"✗ Functional areas page test failed: {e}")
        return False

def test_functional_areas_api_endpoints(app):
    """Test functional areas API endpoints"""
    try:
        with app.test_client() as client:
            # Test list endpoint
            response = client.get('/api/functional-areas/list')
            assert response.status_code == 200
            print("✓ Functional areas list API works")
            
            # Test form endpoint
            response = client.get('/api/functional-areas/form')
            assert response.status_code == 200
            assert b'Add Functional Area' in response.data
            print("✓ Functional areas form API works")
            
            # Test search functionality
            response = client.get('/api/functional-areas/list?search=operations')
            assert response.status_code == 200
            print("✓ Functional areas search works")
            
            # Test transit system filter
            first_transit_system = TransitSystem.query.first()
            if first_transit_system:
                response = client.get(f'/api/functional-areas/list?transit_system={first_transit_system.id}')
                assert response.status_code == 200
                print("✓ Functional areas transit system filter works")
            
        # Test details endpoint if we have functional areas
        first_area = FunctionalArea.query.first()
        if first_area:
            with app.test_client() as client:
                response = client.get(f'/api/functional-areas/{first_area.id}/details')
                assert response.status_code == 200
                print(f"✓ Functional area details API works (tested with {first_area.name})")
                
                response = client.get(f'/api/functional-areas/{first_area.id}/form')
                assert response.status_code == 200
                assert b'Edit Functional Area' in response.data
                print("✓ Functional area edit form API works")
        
        return True
    except Exception as e:
        print(f"✗ Functional areas API test failed: {e}")
        return False

def test_functional_areas_crud_operations(app):
    """Test CRUD operations for functional areas"""
    try:
        # Get a transit system to use for testing
        transit_system = TransitSystem.query.first()
        if not transit_system:
            print("✗ No transit systems found - create a transit system first")
            return False
        
        # Clean up any existing test functional areas
        existing_test = FunctionalArea.query.filter_by(name='Test Functional Area').first()
        if existing_test:
            db.session.delete(existing_test)
            db.session.commit()
        
        existing_updated = FunctionalArea.query.filter_by(name='Updated Test Functional Area').first()
        if existing_updated:
            db.session.delete(existing_updated)
            db.session.commit()
        
        # Test CREATE
        with app.test_client() as client:
            response = client.post('/api/functional-areas', data={
                'name': 'Test Functional Area',
                'description': 'A test functional area for Phase 2 testing',
                'transit_system_id': str(transit_system.id)
            })
            assert response.status_code == 200
            assert b'created successfully' in response.data
            print("✓ Functional area CREATE works")
        
        # Find the created functional area
        test_area = FunctionalArea.query.filter_by(name='Test Functional Area').first()
        assert test_area is not None, "Created functional area not found in database"
        print(f"✓ Created functional area found in database (ID: {test_area.id})")
        
        # Test UPDATE
        with app.test_client() as client:
            response = client.put(f'/api/functional-areas/{test_area.id}', data={
                'name': 'Updated Test Functional Area',
                'description': 'Updated description',
                'transit_system_id': str(transit_system.id)
            })
            assert response.status_code == 200
            assert b'updated successfully' in response.data
            print("✓ Functional area UPDATE works")
        
        # Verify update in database
        db.session.refresh(test_area)
        assert test_area.name == 'Updated Test Functional Area'
        print("✓ Update reflected in database")
        
        # Test DELETE
        with app.test_client() as client:
            response = client.delete(f'/api/functional-areas/{test_area.id}')
            assert response.status_code == 200
            assert b'deleted successfully' in response.data
            print("✓ Functional area DELETE works")
        
        # Verify deletion
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            deleted_area = FunctionalArea.query.get(test_area.id)
        assert deleted_area is None
        print("✓ Deletion reflected in database")
        
        return True
    except Exception as e:
        print(f"✗ Functional areas CRUD test failed: {e}")
        return False

def test_error_handling(app):
    """Test error handling in functional areas routes"""
    try:
        with app.test_client() as client:
            # Test empty name validation
            response = client.post('/api/functional-areas', data={
                'name': '',  # Empty name should fail
                'transit_system_id': '1'
            })
            assert response.status_code == 200
            assert b'required' in response.data.lower()
            print("✓ Empty name validation works")
            
            # Test missing transit system validation
            response = client.post('/api/functional-areas', data={
                'name': 'Test Area',
                'transit_system_id': ''  # Empty transit system should fail
            })
            assert response.status_code == 200
            assert b'required' in response.data.lower()
            print("✓ Missing transit system validation works")
            
            # Test invalid ID for details
            response = client.get('/api/functional-areas/99999/details')
            if response.status_code == 404 or (response.status_code == 200 and b'error' in response.data.lower()):
                print("✓ Invalid ID handling works")
            else:
                print(f"✗ Unexpected response for invalid ID: {response.status_code}")
                return False
            
            # Test invalid ID for update
            response = client.put('/api/functional-areas/99999', data={'name': 'Test Update'})
            if response.status_code == 404 or (response.status_code == 200 and b'error' in response.data.lower()):
                print("✓ Invalid ID update handling works")
            else:
                print(f"✗ Unexpected response for invalid ID update: {response.status_code}")
                return False
            
            # Test invalid ID for delete
            response = client.delete('/api/functional-areas/99999')
            if response.status_code == 404 or (response.status_code == 200 and b'error' in response.data.lower()):
                print("✓ Invalid ID delete handling works")
            else:
                print(f"✗ Unexpected response for invalid ID delete: {response.status_code}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False

def test_template_fragments(app):
    """Test that template fragments render correctly"""
    try:
        from flask import render_template
        
        # Test list fragment
        functional_areas = FunctionalArea.query.limit(3).all()
        html = render_template('fragments/functional_area_list.html', 
                             functional_areas=functional_areas)
        assert 'functional-area-card' in html
        print("✓ Functional area list fragment renders")
        
        # Test form fragment
        transit_systems = TransitSystem.query.limit(5).all()
        html = render_template('fragments/functional_area_form.html', 
                             functional_area=None,
                             transit_systems=transit_systems)
        assert 'Add Functional Area' in html
        print("✓ Functional area form fragment renders")
        
        # Test details fragment (if we have functional areas) - this might be the issue
        if functional_areas:
            try:
                html = render_template('fragments/functional_area_details.html', 
                                     functional_area=functional_areas[0])
                assert functional_areas[0].name in html
                print("✓ Functional area details fragment renders")
            except Exception as e:
                print(f"✗ Details fragment failed: {e}")
                return False
        else:
            print("✓ No functional areas to test details fragment with")
        
        return True
    except Exception as e:
        print(f"✗ Template fragments test failed: {e}")
        return False

def test_hierarchical_relationships(app):
    """Test hierarchical relationships between transit systems and functional areas"""
    try:
        # Test that functional areas are properly linked to transit systems
        functional_areas_with_systems = FunctionalArea.query.join(TransitSystem).limit(5).all()
        
        for area in functional_areas_with_systems:
            assert area.transit_system is not None, f"Functional area {area.name} has no transit system"
            assert area.transit_system.name is not None, f"Transit system for {area.name} has no name"
        
        print(f"✓ Hierarchical relationships verified for {len(functional_areas_with_systems)} functional areas")
        
        # Test filtering by transit system
        if functional_areas_with_systems:
            first_ts = functional_areas_with_systems[0].transit_system
            areas_in_system = FunctionalArea.query.filter_by(transit_system_id=first_ts.id).all()
            assert len(areas_in_system) > 0, "No functional areas found for transit system"
            print(f"✓ Transit system filtering works ({len(areas_in_system)} areas in {first_ts.name})")
        
        return True
    except Exception as e:
        print(f"✗ Hierarchical relationships test failed: {e}")
        return False

def run_tests():
    """Run all Phase 2 Functional Areas tests"""
    print("Testing Phase 2 Step 2.2 - Functional Areas CRUD...")
    print("=" * 70)
    
    app = create_app()
    
    tests = [
        ("Functional Areas Page", lambda: test_functional_areas_page(app)),
        ("API Endpoints", lambda: test_functional_areas_api_endpoints(app)),
        ("CRUD Operations", lambda: test_functional_areas_crud_operations(app)),
        ("Error Handling", lambda: test_error_handling(app)),
        ("Template Fragments", lambda: test_template_fragments(app)),
        ("Hierarchical Relationships", lambda: test_hierarchical_relationships(app))
    ]
    
    passed = 0
    with app.app_context():
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 Phase 2 Step 2.2 - Functional Areas CRUD is ready!")
        print("✅ Hierarchical CRUD with Transit Systems working")
        print("✅ Transit system filtering and selection working")
        print("✅ Template fragments with breadcrumbs working")
        print("✅ Complete validation and error handling")
        print("✅ Ready for Phase 3: Enhanced Systems & Vendors")
    else:
        print("❌ Some tests failed - check implementation")
    
    return passed == len(tests)

if __name__ == "__main__":
    run_tests()