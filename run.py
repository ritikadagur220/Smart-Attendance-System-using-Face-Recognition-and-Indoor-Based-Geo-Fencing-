"""
============================================================
  Smart Attendance System - QuickRun
  One-command system validator and simulator.
  
  Usage: python run.py
============================================================
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python-backend"))

def check_python_version():
    """Verify Python version."""
    print("[CHECK] Checking Python version...")
    v = sys.version_info
    print(f"   Python {v.major}.{v.minor}.{v.micro}")
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print("   [FAIL] Python 3.8+ required!")
        return False
    print("   [OK] Python version OK")
    return True

def check_dependencies():
    """Check required packages."""
    print("\n[CHECK] Checking dependencies...")
    deps = {
        "colorama": "colorama (colored output)",
    }
    for module, desc in deps.items():
        try:
            __import__(module)
            print(f"   [OK] {desc}")
        except ImportError:
            print(f"   [WARN] {desc} -- not installed (optional, will use fallback)")

    try:
        import firebase_admin
        print(f"   [OK] firebase-admin")
    except ImportError:
        print(f"   [WARN] firebase-admin -- not installed (mock mode will be used)")

    try:
        import cv2
        print(f"   [OK] opencv-python ({cv2.__version__})")
    except ImportError:
        print(f"   [WARN] opencv-python -- not installed (face recognition disabled)")

    return True

def check_project_structure():
    """Verify all project files exist."""
    print("\n[CHECK] Checking project structure...")
    base = os.path.dirname(os.path.abspath(__file__))
    
    required_files = [
        "python-backend/config.py",
        "python-backend/attendance_engine.py",
        "python-backend/firebase_handler.py",
        "python-backend/simulator.py",
        "python-backend/test_cases.py",
        "web-dashboard/index.html",
        "web-dashboard/login.html",
        "web-dashboard/style.css",
        "web-dashboard/app.js",
    ]
    
    all_ok = True
    for f in required_files:
        full_path = os.path.join(base, f)
        exists = os.path.exists(full_path)
        status = "[OK]" if exists else "[FAIL]"
        print(f"   {status} {f}")
        if not exists:
            all_ok = False
    
    return all_ok

def run_tests():
    """Run the test suite."""
    print("\n[TEST] Running test suite...")
    print("-" * 50)
    
    import unittest
    from test_cases import (
        TestDeviceValidation,
        TestBeaconNameValidation,
        TestRSSIThresholds,
        TestDuplicatePrevention,
        TestExitLogic,
        TestTimeoutExit,
        TestMultipleStudents,
        TestReset,
        TestFluctuatingSignal,
    )
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TestDeviceValidation,
        TestBeaconNameValidation,
        TestRSSIThresholds,
        TestDuplicatePrevention,
        TestExitLogic,
        TestTimeoutExit,
        TestMultipleStudents,
        TestReset,
        TestFluctuatingSignal,
    ]
    
    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("-" * 50)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"\n   Results: {passed}/{result.testsRun} passed")
    
    if result.failures:
        print(f"   [FAIL] Failures: {len(result.failures)}")
    if result.errors:
        print(f"   [FAIL] Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("   [OK] All tests passed!")
    
    return result.wasSuccessful()

def run_simulator():
    """Run the BLE event simulator."""
    print("\n[SIM] Running BLE Event Simulator...")
    print("-" * 50)
    
    from python_backend.simulator import run_simulation
    run_simulation()

def print_attendance_log():
    """Print a formatted attendance log from a quick simulation."""
    print("\n[LOG] Quick Attendance Log Demo")
    print("-" * 50)
    
    from attendance_engine import AttendanceEngine
    from config import BLE_DEVICE_NAME, DEFAULT_CLASSROOM
    
    engine = AttendanceEngine()
    engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Ritik Kumar")
    engine.register_device("AA:BB:CC:DD:EE:02", "STU002", "Priya Sharma")

    engine.process_ble_event(BLE_DEVICE_NAME, -55, "AA:BB:CC:DD:EE:01", DEFAULT_CLASSROOM)
    engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:02", DEFAULT_CLASSROOM)

    engine.process_ble_event(BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01", DEFAULT_CLASSROOM)

    active = engine.get_active_sessions()
    if active:
        print("\n  Currently Present:")
        print(f"  {'Name':<20} {'Entry Time':<12} {'RSSI':<8} {'Classroom'}")
        print(f"  {'-'*20} {'-'*12} {'-'*8} {'-'*12}")
        for sid, record in active.items():
            print(
                f"  {record.student_name:<20} "
                f"{record.entry_time.strftime('%H:%M:%S'):<12} "
                f"{record.rssi:<8} "
                f"{record.classroom}"
            )

    history = engine.get_history()
    if history:
        print("\n  Completed Sessions:")
        print(f"  {'Name':<20} {'Entry':<10} {'Exit':<10} {'Duration':<10} {'Status'}")
        print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
        for record in history:
            entry = record.entry_time.strftime('%H:%M:%S')
            exit_t = record.exit_time.strftime('%H:%M:%S') if record.exit_time else 'N/A'
            dur = f"{int(record.duration_seconds())}s"
            print(f"  {record.student_name:<20} {entry:<10} {exit_t:<10} {dur:<10} {record.status}")

def main():
    """Main QuickRun entry point."""
    print("=" * 60)
    print("  Smart BLE Attendance System -- QuickRun")
    print("=" * 60)

    if not check_python_version():
        sys.exit(1)

    check_dependencies()

    check_project_structure()

    print("\n" + "=" * 60)
    print("  PHASE 1: UNIT TESTS")
    print("=" * 60)
    tests_passed = run_tests()

    print("\n" + "=" * 60)
    print("  PHASE 2: BLE SIMULATION")
    print("=" * 60)
    run_simulator()

    print("\n" + "=" * 60)
    print("  PHASE 3: ATTENDANCE LOG")
    print("=" * 60)
    print_attendance_log()

    print("\n" + "=" * 60)
    if tests_passed:
        print("  [OK] SYSTEM VALIDATION COMPLETE -- All checks passed!")
    else:
        print("  [WARN] SYSTEM VALIDATION COMPLETE -- Some tests failed")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()
