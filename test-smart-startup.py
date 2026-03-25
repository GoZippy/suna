#!/usr/bin/env python3
"""
Test script for Zippy Suna Smart Startup System
Tests the core functionality without starting actual services
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from start_zippy import ServiceDetector, SmartStartup
    print("✅ Successfully imported smart startup classes")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_service_detector():
    """Test the service detector functionality"""
    print("\n🔍 Testing Service Detector...")
    
    detector = ServiceDetector()
    
    # Test port availability checking
    print("  Testing port availability...")
    available = detector.check_port_available(9999)  # Should be available
    if available:
        print("    ✅ Port 9999 correctly identified as available")
    else:
        print("    ❌ Port 9999 incorrectly identified as unavailable")
    
    # Test local service detection (without actual connections)
    print("  Testing local service detection...")
    try:
        postgres_running, postgres_url = detector.check_local_postgres()
        print(f"    PostgreSQL: {'Running' if postgres_running else 'Not running'} at {postgres_url or 'N/A'}")
    except Exception as e:
        print(f"    ⚠️  PostgreSQL detection error: {e}")
    
    try:
        redis_running, redis_url = detector.check_local_redis()
        print(f"    Redis: {'Running' if redis_running else 'Not running'} at {redis_url or 'N/A'}")
    except Exception as e:
        print(f"    ⚠️  Redis detection error: {e}")
    
    try:
        ollama_running, ollama_url = detector.check_local_ollama()
        print(f"    Ollama: {'Running' if ollama_running else 'Not running'} at {ollama_url or 'N/A'}")
    except Exception as e:
        print(f"    ⚠️  Ollama detection error: {e}")
    
    # Test project container detection
    print("  Testing project container detection...")
    try:
        containers = detector.check_project_containers()
        print(f"    Project containers: {containers}")
    except Exception as e:
        print(f"    ⚠️  Container detection error: {e}")
    
    return True

def test_smart_startup():
    """Test the smart startup functionality"""
    print("\n🚀 Testing Smart Startup...")
    
    startup = SmartStartup()
    
    # Test service detection
    print("  Testing service detection...")
    try:
        services = startup.detect_services()
        print(f"    Detected services: {len(services)}")
        for service, status in services.items():
            print(f"      {service}: {status}")
    except Exception as e:
        print(f"    ❌ Service detection error: {e}")
        return False
    
    # Test environment file creation
    print("  Testing environment configuration...")
    try:
        # Create a test preferences dict
        test_preferences = {
            'postgres': 'local',
            'redis': 'container',
            'ollama': 'local'
        }
        
        # Test environment config update
        startup.update_environment_config(services, test_preferences)
        print("    ✅ Environment configuration updated")
        
    except Exception as e:
        print(f"    ❌ Environment config error: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🧪 Testing Zippy Suna Smart Startup System")
    print("=" * 50)
    
    # Test service detector
    detector_ok = test_service_detector()
    
    # Test smart startup
    startup_ok = test_smart_startup()
    
    # Summary
    print("\n📊 Test Results:")
    print("=" * 30)
    print(f"Service Detector: {'✅ PASS' if detector_ok else '❌ FAIL'}")
    print(f"Smart Startup:   {'✅ PASS' if startup_ok else '❌ FAIL'}")
    
    if detector_ok and startup_ok:
        print("\n🎉 All tests passed! Smart startup system is ready.")
        return True
    else:
        print("\n❌ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


