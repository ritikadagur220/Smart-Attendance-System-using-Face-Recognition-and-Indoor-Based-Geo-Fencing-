"""
============================================================
  Smart Attendance System - Test Cases
  Comprehensive unit tests for the attendance engine.
  Covers all edge cases, boundary values, and error paths.
============================================================
"""

import unittest
import time
from attendance_engine import AttendanceEngine
from config import (
    BLE_DEVICE_NAME,
    RSSI_THRESHOLD_PRESENT,
    RSSI_THRESHOLD_EXIT,
    STATUS_PRESENT,
    STATUS_EXIT,
    EXIT_TIMEOUT_SECONDS,
    DUPLICATE_WINDOW_SECONDS,
)

class TestDeviceValidation(unittest.TestCase):
    """Test device registration and validation."""

    def setUp(self):
        self.engine = AttendanceEngine()

    def test_register_device(self):
        """Device registration should succeed."""
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Test Student")
        is_valid, info = self.engine.validate_device("AA:BB:CC:DD:EE:01")
        self.assertTrue(is_valid)
        self.assertEqual(info["student_id"], "STU001")
        self.assertEqual(info["student_name"], "Test Student")

    def test_unregistered_device(self):
        """Unregistered device should be rejected."""
        is_valid, info = self.engine.validate_device("XX:YY:ZZ:00:00:00")
        self.assertFalse(is_valid)
        self.assertIsNone(info)

    def test_multiple_devices(self):
        """Multiple devices can be registered."""
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Student A")
        self.engine.register_device("AA:BB:CC:DD:EE:02", "STU002", "Student B")
        self.assertTrue(self.engine.is_device_registered("AA:BB:CC:DD:EE:01"))
        self.assertTrue(self.engine.is_device_registered("AA:BB:CC:DD:EE:02"))
        self.assertFalse(self.engine.is_device_registered("AA:BB:CC:DD:EE:03"))

class TestBeaconNameValidation(unittest.TestCase):
    """Test BLE device name matching."""

    def setUp(self):
        self.engine = AttendanceEngine()
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Test Student")

    def test_correct_beacon_name(self):
        """Correct beacon name should be accepted."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "MARKED_PRESENT")

    def test_wrong_beacon_name(self):
        """Wrong beacon name should be rejected."""
        result = self.engine.process_ble_event("WRONG-NAME", -60, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "REJECTED")
        self.assertIn("Unknown device name", result["message"])

    def test_empty_beacon_name(self):
        """Empty beacon name should be rejected."""
        result = self.engine.process_ble_event("", -60, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "REJECTED")

    def test_similar_beacon_name(self):
        """Similar but incorrect beacon name should be rejected."""
        result = self.engine.process_ble_event("ER-BLEV2.3-26D0009", -60, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "REJECTED")

class TestRSSIThresholds(unittest.TestCase):
    """Test RSSI boundary values for PRESENT/EXIT detection."""

    def setUp(self):
        self.engine = AttendanceEngine()
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Test Student")

    def test_strong_signal_present(self):
        """Strong signal (RSSI > -75) should mark PRESENT."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "MARKED_PRESENT")
        self.assertEqual(result["status"], STATUS_PRESENT)

    def test_boundary_present_rssi_minus_74(self):
        """RSSI = -74 (above -75 threshold) should mark PRESENT."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -74, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "MARKED_PRESENT")

    def test_boundary_present_rssi_minus_75(self):
        """RSSI = -75 (exact threshold) should NOT mark present (not greater than -75)."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -75, "AA:BB:CC:DD:EE:01")

        self.assertEqual(result["action"], "NO_CHANGE")

    def test_boundary_present_rssi_minus_76(self):
        """RSSI = -76 (below -75 threshold) should be in hysteresis zone."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -76, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "NO_CHANGE")

    def test_hysteresis_zone(self):
        """RSSI between -75 and -85 should cause no state change."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -80, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "NO_CHANGE")

    def test_boundary_exit_rssi_minus_85(self):
        """RSSI = -85 (exact exit threshold) should NOT exit (not less than -85)."""

        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")

        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -85, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "NO_CHANGE")

    def test_boundary_exit_rssi_minus_86(self):
        """RSSI = -86 (below exit threshold) should mark EXIT."""

        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -86, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "MARKED_EXIT")
        self.assertEqual(result["status"], STATUS_EXIT)

    def test_weak_signal_exit(self):
        """Weak signal (RSSI < -85) should mark EXIT if currently present."""

        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -95, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "MARKED_EXIT")

    def test_very_strong_signal(self):
        """Very strong signal should mark PRESENT."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -30, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "MARKED_PRESENT")

    def test_very_weak_signal(self):
        """Very weak signal for non-present student should be NOT_PRESENT."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -100, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "NOT_PRESENT")

class TestDuplicatePrevention(unittest.TestCase):
    """Test duplicate attendance prevention logic."""

    def setUp(self):
        self.engine = AttendanceEngine()
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Test Student")

    def test_duplicate_present_blocked(self):
        """Second PRESENT event should be blocked."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -55, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "ALREADY_PRESENT")

    def test_re_entry_within_window_blocked(self):
        """Re-entry within duplicate window should be blocked."""

        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")

        self.engine.process_ble_event(BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01")

        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "DUPLICATE_BLOCKED")

    def test_prevent_duplicate_check(self):
        """prevent_duplicate should return True for existing records."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.assertTrue(self.engine.prevent_duplicate("STU001"))

    def test_prevent_duplicate_no_record(self):
        """prevent_duplicate should return False for no records."""
        self.assertFalse(self.engine.prevent_duplicate("STU001"))

class TestExitLogic(unittest.TestCase):
    """Test exit detection scenarios."""

    def setUp(self):
        self.engine = AttendanceEngine()
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Test Student")

    def test_exit_without_entry(self):
        """Exit signal for non-present student should be NOT_PRESENT."""
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "NOT_PRESENT")

    def test_normal_exit(self):
        """Normal exit after entry should work."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "MARKED_EXIT")
        self.assertEqual(result["status"], STATUS_EXIT)

    def test_exit_recorded_in_history(self):
        """Exit should move record to history."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.engine.process_ble_event(BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01")
        history = self.engine.get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, STATUS_EXIT)

class TestTimeoutExit(unittest.TestCase):
    """Test timeout-based auto-exit."""

    def setUp(self):
        self.engine = AttendanceEngine()
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Test Student")

    def test_timeout_exit(self):
        """Student should be auto-exited after timeout."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")

        self.engine._last_seen["STU001"] = time.time() - EXIT_TIMEOUT_SECONDS - 10
        auto_exits = self.engine.check_exit_timeouts()
        self.assertEqual(len(auto_exits), 1)
        self.assertEqual(auto_exits[0]["action"], "AUTO_EXIT")
        self.assertEqual(auto_exits[0]["student_id"], "STU001")

    def test_no_timeout_if_recent(self):
        """No auto-exit if recently seen."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        auto_exits = self.engine.check_exit_timeouts()
        self.assertEqual(len(auto_exits), 0)

class TestMultipleStudents(unittest.TestCase):
    """Test scenarios with multiple students."""

    def setUp(self):
        self.engine = AttendanceEngine()
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Student A")
        self.engine.register_device("AA:BB:CC:DD:EE:02", "STU002", "Student B")
        self.engine.register_device("AA:BB:CC:DD:EE:03", "STU003", "Student C")

    def test_multiple_entries(self):
        """Multiple students can enter independently."""
        r1 = self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        r2 = self.engine.process_ble_event(BLE_DEVICE_NAME, -55, "AA:BB:CC:DD:EE:02")
        r3 = self.engine.process_ble_event(BLE_DEVICE_NAME, -65, "AA:BB:CC:DD:EE:03")
        self.assertEqual(r1["action"], "MARKED_PRESENT")
        self.assertEqual(r2["action"], "MARKED_PRESENT")
        self.assertEqual(r3["action"], "MARKED_PRESENT")
        self.assertEqual(len(self.engine.get_active_sessions()), 3)

    def test_individual_exits(self):
        """Students can exit independently without affecting others."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.engine.process_ble_event(BLE_DEVICE_NAME, -55, "AA:BB:CC:DD:EE:02")

        self.engine.process_ble_event(BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01")
        self.assertEqual(len(self.engine.get_active_sessions()), 1)
        self.assertEqual(self.engine.get_student_status("STU001"), STATUS_EXIT)
        self.assertEqual(self.engine.get_student_status("STU002"), STATUS_PRESENT)

    def test_summary_accuracy(self):
        """Attendance summary should be accurate."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.engine.process_ble_event(BLE_DEVICE_NAME, -55, "AA:BB:CC:DD:EE:02")
        summary = self.engine.get_attendance_summary()
        self.assertEqual(summary["active_count"], 2)
        self.assertEqual(len(summary["active_students"]), 2)

class TestReset(unittest.TestCase):
    """Test engine reset functionality."""

    def setUp(self):
        self.engine = AttendanceEngine()
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Test Student")

    def test_full_reset(self):
        """Full reset should clear everything."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.engine.reset()
        self.assertEqual(len(self.engine.get_active_sessions()), 0)
        self.assertEqual(len(self.engine.get_history()), 0)
        self.assertEqual(len(self.engine.get_event_log()), 0)

    def test_session_reset_keeps_history(self):
        """Session-only reset should keep registered devices."""
        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.engine.process_ble_event(BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01")
        self.engine.reset_sessions_only()

        self.assertTrue(self.engine.is_device_registered("AA:BB:CC:DD:EE:01"))

        self.assertEqual(len(self.engine.get_history()), 1)

class TestFluctuatingSignal(unittest.TestCase):
    """Test behavior with rapidly fluctuating RSSI."""

    def setUp(self):
        self.engine = AttendanceEngine()
        self.engine.register_device("AA:BB:CC:DD:EE:01", "STU001", "Test Student")

    def test_fluctuating_signal_sequence(self):
        """Fluctuating signal should be handled by hysteresis zone."""

        r1 = self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.assertEqual(r1["action"], "MARKED_PRESENT")

        r2 = self.engine.process_ble_event(BLE_DEVICE_NAME, -78, "AA:BB:CC:DD:EE:01")
        self.assertEqual(r2["action"], "NO_CHANGE")

        r3 = self.engine.process_ble_event(BLE_DEVICE_NAME, -65, "AA:BB:CC:DD:EE:01")
        self.assertEqual(r3["action"], "ALREADY_PRESENT")

        r4 = self.engine.process_ble_event(BLE_DEVICE_NAME, -82, "AA:BB:CC:DD:EE:01")
        self.assertEqual(r4["action"], "NO_CHANGE")

        self.assertEqual(self.engine.get_student_status("STU001"), STATUS_PRESENT)

    def test_rapid_enter_exit_enter(self):
        """Rapid enter-exit-enter should be handled by duplicate window."""

        self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")

        self.engine.process_ble_event(BLE_DEVICE_NAME, -90, "AA:BB:CC:DD:EE:01")

        result = self.engine.process_ble_event(BLE_DEVICE_NAME, -60, "AA:BB:CC:DD:EE:01")
        self.assertEqual(result["action"], "DUPLICATE_BLOCKED")

if __name__ == "__main__":

    unittest.main(verbosity=2)
