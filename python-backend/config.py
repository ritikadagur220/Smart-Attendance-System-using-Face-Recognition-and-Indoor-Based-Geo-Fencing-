"""
============================================================
  Smart Attendance System - Configuration
  Central configuration for BLE detection, Firebase,
  and attendance engine parameters.
============================================================
"""

BLE_DEVICE_NAME = "ER-BLEV2.3-26D0008"

RSSI_THRESHOLD_PRESENT = -75
RSSI_THRESHOLD_EXIT = -85

EXIT_TIMEOUT_SECONDS = 30
SCAN_INTERVAL_SECONDS = 5
DUPLICATE_WINDOW_SECONDS = 60

STATUS_PRESENT = "PRESENT"
STATUS_EXIT = "EXIT"
STATUS_UNKNOWN = "UNKNOWN"

USE_FIREBASE = False

FIREBASE_CREDENTIALS_PATH = "serviceAccountKey.json"

FIREBASE_PROJECT_ID = "your-project-id"

COLLECTION_STUDENTS = "students"
COLLECTION_BEACONS = "beacons"
COLLECTION_ATTENDANCE = "attendance"

DEFAULT_CLASSROOM = "Room-101"

LOG_LEVEL = "INFO"
