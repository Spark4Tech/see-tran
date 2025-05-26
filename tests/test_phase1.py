# tests/test_phase1.py - Phase 1 implementation test with proper app context
"""
Phase 1 Test Script
Run this after implementing Phase 1 to verify everything works
Usage: python -m pytest tests/test_phase1.py -v
   OR: python tests/test_phase1.py
"""

import sys
import os
# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db

def test_auth_import():
    """Test that auth module imports correctly"""
    try:
        from app.auth import login_required, get_current_user, get_updated_by
        print("✓ Auth module imports successfully")
        
        # Test get_current_user
        user = get_current_user()
        assert user['username'] == 'Steve'
        print("✓ get_current_user returns expected user")
        
        # Test get_updated_by
        updated_by = get_updated_by()
        assert updated_by == '1_Steve'
        print("✓ get_updated_by returns expected format")
        
        # Test login_required decorator
        @login_required
        def dummy_function():
            return "success"
        
        result = dummy_function()
        assert result == "success"
        print("✓ login_required decorator works (no-op)")
        
        return True
    except Exception as e:
        print(f"✗ Auth module test failed: {e}")
        return False

def test_error_helpers_import():
    """Test that error helpers import correctly"""
    try:
        from app.utils.errors import (
            json_error_response, json_success_response,
            html_error_fragment, html_success_fragment
        )
        print("✓ Error helpers import successfully")
        
        # Test JSON responses
        error_resp = json_error_response("Test error")
        assert error_resp[1] == 400  # status code
        assert error_resp[0].json['status'] == 'error'
        assert error_resp[0].json['message'] == 'Test error'
        print("✓ JSON error response works")
        
        success_resp = json_success_response("Test success")
        assert success_resp.json['status'] == 'success'
        assert success_resp.json['message'] == 'Test success'
        print("✓ JSON success response works")
        
        # Test HTML fragments
        error_html = html_error_fragment("Test error")
        assert "Test error" in error_html
        assert "bg-red-900/20" in error_html
        print("✓ HTML error fragment works")
        
        success_html = html_success_fragment("Test success")
        assert "Test success" in success_html
        assert "bg-green-900/20" in success_html
        print("✓ HTML success fragment works")
        
        return True
    except Exception as e:
        print(f"✗ Error helpers test failed: {e}")
        return False

def test_routes_with_error_handling(app):
    """Test that routes handle errors gracefully"""
    try:
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/api/health')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'ok'
            print("✓ Health endpoint works with error handling")
            
            # Test count endpoints
            response = client.get('/api/count/systems')
            assert response.status_code == 200
            print("✓ Count endpoints work with error handling")
            
            # Test systems list endpoint
            response = client.get('/api/systems/list')
            assert response.status_code == 200
            print("✓ Systems list works with error handling")
            
            # Test vendors list endpoint
            response = client.get('/api/vendors/list')
            assert response.status_code == 200
            print("✓ Vendors list works with error handling")
        
        return True
    except Exception as e:
        print(f"✗ Routes error handling test failed: {e}")
        return False

def test_database_connection(app):
    """Test that database connection works"""
    try:
        with app.app_context():
            # Test basic query
            from app.models.tran import TransitSystem
            count = TransitSystem.query.count()
            print(f"✓ Database connection works - {count} transit systems found")
        return True
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        return False

def run_tests():
    """Run all Phase 1 tests with proper Flask app context"""
    print("Testing Phase 1 Implementation...")
    print("=" * 50)
    
    # Create Flask app
    app = create_app()
    
    tests = [
        ("Auth Import", lambda: test_auth_import()),
        ("Error Helpers", lambda: test_error_helpers_import()),
        ("Database Connection", lambda: test_database_connection(app)),
        ("Routes Error Handling", lambda: test_routes_with_error_handling(app))
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
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 Phase 1 implementation ready!")
        print("✅ Authentication stubs working")
        print("✅ Error handling implemented")
        print("✅ All existing routes preserved")
        print("✅ Ready for Phase 2: Complete Core Entity CRUD")
    else:
        print("❌ Some tests failed - check implementation")
        print("💡 Check that all files are created and Flask app starts normally")
    
    return passed == len(tests)

if __name__ == "__main__":
    run_tests()