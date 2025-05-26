# tests/test_phase2_transit_systems.py
"""
Phase 2 Test Script - Transit Systems CRUD
Run this after implementing Phase 2 Step 2.1 to verify transit systems CRUD works
Usage: python tests/test_phase2_transit_systems.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models.tran import TransitSystem

def test_transit_systems_page(app):
    """Test that transit systems page loads"""
    try:
        with app.test_client() as client:
            response = client.get('/transit-systems')
            assert response.status_code == 200
            assert b'Transit Systems Management' in response.data
            print("✓ Transit systems page loads correctly")
        return True
    except Exception as e:
        print(f"✗ Transit systems page test failed: {e}")
        return False

def test_transit_systems_api_endpoints(app):
    """Test transit systems API endpoints"""
    try:
        with app.test_client() as client:
            # Test list endpoint
            response = client.get('/api/transit-systems/list')
            assert response.status_code == 200
            print("✓ Transit systems list API works")
            
            # Test form endpoint
            response = client.get('/api/transit-systems/form')
            assert response.status_code == 200
            assert b'Add Transit System' in response.data
            print("✓ Transit systems form API works")
            
            # Test search functionality
            response = client.get('/api/transit-systems/list?search=metro')
            assert response.status_code == 200
            print("✓ Transit systems search works")
        
        # Test details endpoint in separate context
        first_system = TransitSystem.query.first()
        if first_system:
            with app.test_client() as client:
                response = client.get(f'/api/transit-systems/{first_system.id}/details')
                assert response.status_code == 200
                print(f"✓ Transit system details API works (tested with {first_system.name})")
                
                response = client.get(f'/api/transit-systems/{first_system.id}/form')
                assert response.status_code == 200
                assert b'Edit Transit System' in response.data
                print("✓ Transit system edit form API works")
        
        return True
    except Exception as e:
        print(f"✗ Transit systems API test failed: {e}")
        return False

def test_transit_systems_crud_operations(app):
    """Test CRUD operations for transit systems"""
    try:
        # Clean up any existing test systems first
        existing_test = TransitSystem.query.filter_by(name='Test Transit System').first()
        if existing_test:
            db.session.delete(existing_test)
            db.session.commit()
        
        existing_updated = TransitSystem.query.filter_by(name='Updated Test Transit System').first()
        if existing_updated:
            db.session.delete(existing_updated)
            db.session.commit()
        
        # Test CREATE
        with app.test_client() as client:
            response = client.post('/api/transit-systems', data={
                'name': 'Test Transit System',
                'location': 'Test City, ST',
                'description': 'A test transit system for Phase 2 testing'
            })
            assert response.status_code == 200
            assert b'created successfully' in response.data
            print("✓ Transit system CREATE works")
        
        # Find the created system
        test_system = TransitSystem.query.filter_by(name='Test Transit System').first()
        assert test_system is not None, "Created transit system not found in database"
        print(f"✓ Created transit system found in database (ID: {test_system.id})")
        
        # Test UPDATE
        with app.test_client() as client:
            response = client.put(f'/api/transit-systems/{test_system.id}', data={
                'name': 'Updated Test Transit System',
                'location': 'Updated City, ST',
                'description': 'Updated description'
            })
            assert response.status_code == 200
            assert b'updated successfully' in response.data
            print("✓ Transit system UPDATE works")
        
        # Verify update in database
        db.session.refresh(test_system)
        assert test_system.name == 'Updated Test Transit System'
        print("✓ Update reflected in database")
        
        # Test DELETE
        with app.test_client() as client:
            response = client.delete(f'/api/transit-systems/{test_system.id}')
            assert response.status_code == 200
            assert b'deleted successfully' in response.data
            print("✓ Transit system DELETE works")
        
        # Verify deletion (suppress SQLAlchemy 2.0 warning)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            deleted_system = TransitSystem.query.get(test_system.id)
        assert deleted_system is None
        print("✓ Deletion reflected in database")
        
        return True
    except Exception as e:
        print(f"✗ Transit systems CRUD test failed: {e}")
        return False

def test_error_handling(app):
    """Test error handling in transit systems routes"""
    try:
        with app.test_client() as client:
            # Test empty name validation
            response = client.post('/api/transit-systems', data={
                'name': '',  # Empty name should fail
                'location': 'Test City'
            })
            assert response.status_code == 200
            assert b'required' in response.data.lower()
            print("✓ Empty name validation works")
            
            # Test invalid ID for details - accept either 404 or error fragment
            response = client.get('/api/transit-systems/99999/details')
            if response.status_code == 404:
                print("✓ Invalid ID handling works")
            elif response.status_code == 200 and b'error' in response.data.lower():
                print("✓ Invalid ID handling works")
            else:
                print(f"✗ Unexpected response for invalid ID: {response.status_code}")
                return False
            
            # Test invalid ID for update
            response = client.put('/api/transit-systems/99999', data={'name': 'Test Update'})
            if response.status_code == 404 or (response.status_code == 200 and b'error' in response.data.lower()):
                print("✓ Invalid ID update handling works")
            else:
                print(f"✗ Unexpected response for invalid ID update: {response.status_code}")
                return False
            
            # Test invalid ID for delete
            response = client.delete('/api/transit-systems/99999')
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
        transit_systems = TransitSystem.query.limit(3).all()
        html = render_template('fragments/transit_system_list.html', 
                             transit_systems=transit_systems)
        assert 'transit-system-card' in html
        print("✓ Transit system list fragment renders")
        
        # Test form fragment
        html = render_template('fragments/transit_system_form.html', 
                             transit_system=None)
        assert 'Add Transit System' in html
        print("✓ Transit system form fragment renders")
        
        # Test details fragment (if we have systems)
        if transit_systems:
            html = render_template('fragments/transit_system_details.html', 
                                 transit_system=transit_systems[0])
            assert transit_systems[0].name in html
            print("✓ Transit system details fragment renders")
        
        return True
    except Exception as e:
        print(f"✗ Template fragments test failed: {e}")
        return False

def run_tests():
    """Run all Phase 2 Transit Systems tests"""
    print("Testing Phase 2 - Transit Systems CRUD...")
    print("=" * 60)
    
    app = create_app()
    
    tests = [
        ("Transit Systems Page", lambda: test_transit_systems_page(app)),
        ("API Endpoints", lambda: test_transit_systems_api_endpoints(app)),
        ("CRUD Operations", lambda: test_transit_systems_crud_operations(app)),
        ("Error Handling", lambda: test_error_handling(app)),
        ("Template Fragments", lambda: test_template_fragments(app))
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
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 Phase 2 Step 2.1 - Transit Systems CRUD is ready!")
        print("✅ Full page template created")
        print("✅ Template fragments working (no more HTML in routes!)")
        print("✅ Complete CRUD operations implemented")
        print("✅ Error handling and validation working")
        print("✅ Ready for Step 2.2: Functional Areas Management")
    else:
        print("❌ Some tests failed - check implementation")
    
    return passed == len(tests)

if __name__ == "__main__":
    run_tests()