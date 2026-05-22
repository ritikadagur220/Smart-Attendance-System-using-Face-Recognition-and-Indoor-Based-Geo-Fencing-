"""
============================================================
  Smart Attendance System - Attendance Engine
  Core logic for BLE-based attendance processing.
  Handles PRESENT/EXIT detection, duplicate prevention,
  device validation, and session management.
============================================================
"""

import time
from datetime import datetime, date
from typing import Optional, Dict, Tuple

from config import (
    BLE_DEVICE_NAME,
    RSSI_THRESHOLD_PRESENT,
    RSSI_THRESHOLD_EXIT,
    EXIT_TIMEOUT_SECONDS,
    DUPLICATE_WINDOW_SECONDS,
    STATUS_PRESENT,
    STATUS_EXIT,
    STATUS_UNKNOWN,
)

class AttendanceRecord:
    """Represents a single attendance session for a student."""

    def __init__(self, student_id: str, student_name: str, classroom: str, rssi: int):
        self.student_id = student_id
        self.student_name = student_name
        self.classroom = classroom
        self.entry_time = datetime.now()
        self.exit_time: Optional[datetime] = None
        self.status = STATUS_PRESENT
        self.rssi = rssi
        self.date_str = date.today().isoformat()

    def mark_exit(self):
        """Mark this attendance session as exited."""
        self.exit_time = datetime.now()
        self.status = STATUS_EXIT

    def duration_seconds(self) -> float:
        """Get duration of this session in seconds."""
        end = self.exit_time if self.exit_time else datetime.now()
        return (end - self.entry_time).total_seconds()

    def to_dict(self) -> dict:
        """Convert record to dictionary for storage."""
        return {
            "student_id": self.student_id,
            "student_name": self.student_name,
            "classroom": self.classroom,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "status": self.status,
            "date": self.date_str,
            "rssi": self.rssi,
        }

    def __repr__(self):
        return (
            f"AttendanceRecord({self.student_name}, "
            f"status={self.status}, rssi={self.rssi}, "
            f"entry={self.entry_time.strftime('%H:%M:%S')})"
        )

class AttendanceEngine:
    """
    Core attendance processing engine.
    
    Manages BLE event processing, device validation,
    duplicate prevention, and session state tracking.
    """

    def __init__(self):

        self._active_sessions: Dict[str, AttendanceRecord] = {}

        self._last_seen: Dict[str, float] = {}

        self._last_exit: Dict[str, float] = {}

        self._registered_devices: Dict[str, dict] = {}

        self._history: list = []

        self._event_log: list = []

    def register_device(self, device_id: str, student_id: str, student_name: str):
        """
        Register/bind a student's device for attendance verification.
        Must be called before processing events for this device.
        """
        self._registered_devices[device_id] = {
            "student_id": student_id,
            "student_name": student_name,
            "registered_at": datetime.now().isoformat(),
        }
        self._log(f"DEVICE REGISTERED: {device_id} → {student_name}")

    def validate_device(self, device_id: str) -> Tuple[bool, Optional[dict]]:
        """
        Validate if a device is registered.
        Returns (is_valid, student_info or None).
        """
        if device_id in self._registered_devices:
            return True, self._registered_devices[device_id]
        return False, None

    def is_device_registered(self, device_id: str) -> bool:
        """Quick check if device is registered."""
        return device_id in self._registered_devices

    def process_ble_event(
        self,
        device_name: str,
        rssi: int,
        device_id: str,
        classroom: str = "Room-101",
    ) -> dict:
        """
        Process a single BLE scan event.

        Args:
            device_name: Detected BLE device name
            rssi: Signal strength (dBm)
            device_id: Student's device MAC/ID
            classroom: Classroom identifier

        Returns:
            dict with keys: action, status, message, student_id, student_name
        """
        result = {
            "action": "NONE",
            "status": STATUS_UNKNOWN,
            "message": "",
            "student_id": None,
            "student_name": None,
            "rssi": rssi,
            "timestamp": datetime.now().isoformat(),
        }

        if device_name != BLE_DEVICE_NAME:
            result["action"] = "REJECTED"
            result["message"] = f"Unknown device name: {device_name}"
            self._log(f"REJECTED: Unknown device '{device_name}'")
            return result

        is_valid, student_info = self.validate_device(device_id)
        if not is_valid:
            result["action"] = "REJECTED"
            result["message"] = f"Unregistered device: {device_id}"
            self._log(f"REJECTED: Unregistered device '{device_id}'")
            return result

        student_id = student_info["student_id"]
        student_name = student_info["student_name"]
        result["student_id"] = student_id
        result["student_name"] = student_name

        self._last_seen[student_id] = time.time()

        if rssi > RSSI_THRESHOLD_PRESENT:

            result = self._handle_present(student_id, student_name, rssi, classroom, result)

        elif rssi < RSSI_THRESHOLD_EXIT:

            result = self._handle_exit(student_id, student_name, rssi, result)

        else:

            result["action"] = "NO_CHANGE"
            result["message"] = (
                f"RSSI {rssi} in hysteresis zone "
                f"({RSSI_THRESHOLD_EXIT} to {RSSI_THRESHOLD_PRESENT}), no action"
            )
            self._log(
                f"HYSTERESIS: {student_name} RSSI={rssi} (no change)"
            )

        return result

    def _handle_present(
        self, student_id: str, student_name: str, rssi: int, classroom: str, result: dict
    ) -> dict:
        """Handle strong signal → mark PRESENT if not already."""

        if student_id in self._active_sessions:
            result["action"] = "ALREADY_PRESENT"
            result["status"] = STATUS_PRESENT
            result["message"] = f"{student_name} already marked PRESENT"
            self._log(f"DUPLICATE BLOCKED: {student_name} already PRESENT")
            return result

        if student_id in self._last_exit:
            elapsed = time.time() - self._last_exit[student_id]
            if elapsed < DUPLICATE_WINDOW_SECONDS:
                result["action"] = "DUPLICATE_BLOCKED"
                result["status"] = STATUS_UNKNOWN
                remaining = int(DUPLICATE_WINDOW_SECONDS - elapsed)
                result["message"] = (
                    f"Re-entry blocked for {student_name}. "
                    f"Wait {remaining}s (duplicate prevention)"
                )
                self._log(
                    f"DUPLICATE WINDOW: {student_name} re-entry blocked, "
                    f"{remaining}s remaining"
                )
                return result

        record = AttendanceRecord(student_id, student_name, classroom, rssi)
        self._active_sessions[student_id] = record

        result["action"] = "MARKED_PRESENT"
        result["status"] = STATUS_PRESENT
        result["message"] = (
            f"{student_name} marked PRESENT in {classroom} "
            f"(RSSI: {rssi}dBm)"
        )
        self._log(
            f"✅ PRESENT: {student_name} | RSSI={rssi} | {classroom}"
        )
        return result

    def _handle_exit(self, student_id: str, student_name: str, rssi: int, result: dict) -> dict:
        """Handle weak signal → mark EXIT if currently present."""

        if student_id not in self._active_sessions:
            result["action"] = "NOT_PRESENT"
            result["status"] = STATUS_UNKNOWN
            result["message"] = f"{student_name} is not currently present"
            self._log(f"EXIT IGNORED: {student_name} was not present")
            return result

        record = self._active_sessions.pop(student_id)
        record.mark_exit()
        self._history.append(record)
        self._last_exit[student_id] = time.time()

        duration = record.duration_seconds()
        result["action"] = "MARKED_EXIT"
        result["status"] = STATUS_EXIT
        result["message"] = (
            f"{student_name} marked EXIT "
            f"(duration: {int(duration)}s, RSSI: {rssi}dBm)"
        )
        self._log(
            f"🚪 EXIT: {student_name} | RSSI={rssi} | "
            f"Duration={int(duration)}s"
        )
        return result

    def check_exit_timeouts(self) -> list:
        """
        Check all active sessions for timeout-based exits.
        Call this periodically (e.g., every scan interval).
        
        Returns list of auto-exited student results.
        """
        now = time.time()
        auto_exits = []

        for student_id in list(self._active_sessions.keys()):
            last_seen = self._last_seen.get(student_id, 0)
            elapsed = now - last_seen

            if elapsed > EXIT_TIMEOUT_SECONDS:
                record = self._active_sessions.pop(student_id)
                record.mark_exit()
                self._history.append(record)
                self._last_exit[student_id] = now

                duration = record.duration_seconds()
                auto_exits.append({
                    "action": "AUTO_EXIT",
                    "status": STATUS_EXIT,
                    "student_id": student_id,
                    "student_name": record.student_name,
                    "message": (
                        f"{record.student_name} auto-exited "
                        f"(timeout: {int(elapsed)}s, duration: {int(duration)}s)"
                    ),
                })
                self._log(
                    f"⏰ AUTO-EXIT: {record.student_name} | "
                    f"Timeout={int(elapsed)}s | Duration={int(duration)}s"
                )

        return auto_exits

    def prevent_duplicate(self, student_id: str, target_date: str = None) -> bool:
        """
        Check if a student already has a completed attendance entry today.
        Returns True if duplicate exists (should prevent).
        
        Note: This checks the history list. For Firebase-based checks,
        use firebase_handler.get_attendance_today().
        """
        if target_date is None:
            target_date = date.today().isoformat()

        for record in self._history:
            if record.student_id == student_id and record.date_str == target_date:
                return True

        if student_id in self._active_sessions:
            return True

        return False

    def get_active_sessions(self) -> Dict[str, AttendanceRecord]:
        """Get all currently active (PRESENT) sessions."""
        return dict(self._active_sessions)

    def get_history(self) -> list:
        """Get all completed attendance records."""
        return list(self._history)

    def get_student_status(self, student_id: str) -> str:
        """Get current status of a student."""
        if student_id in self._active_sessions:
            return STATUS_PRESENT
        return STATUS_EXIT

    def get_attendance_summary(self) -> dict:
        """Get summary statistics."""
        return {
            "active_count": len(self._active_sessions),
            "total_entries_today": len(self._history),
            "active_students": [
                {
                    "student_id": r.student_id,
                    "student_name": r.student_name,
                    "entry_time": r.entry_time.strftime("%H:%M:%S"),
                    "rssi": r.rssi,
                }
                for r in self._active_sessions.values()
            ],
        }

    def get_event_log(self) -> list:
        """Get the full event log for debugging."""
        return list(self._event_log)

    def reset(self):
        """Reset all state. Useful for testing."""
        self._active_sessions.clear()
        self._last_seen.clear()
        self._last_exit.clear()
        self._history.clear()
        self._event_log.clear()

    def reset_sessions_only(self):
        """Reset active sessions but keep history and devices."""
        self._active_sessions.clear()
        self._last_seen.clear()
        self._last_exit.clear()

    def _log(self, message: str):
        """Internal logging."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
        }
        self._event_log.append(entry)
