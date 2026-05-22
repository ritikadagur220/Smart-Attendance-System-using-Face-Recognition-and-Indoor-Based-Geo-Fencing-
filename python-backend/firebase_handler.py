"""
============================================================
  Smart Attendance System - Firebase Handler
  Manages all Firestore read/write operations.
  Supports both LIVE (Firebase) and MOCK modes.
============================================================
"""

import os
from datetime import datetime, date
from typing import Optional, List, Dict

from config import (
    USE_FIREBASE,
    FIREBASE_CREDENTIALS_PATH,
    COLLECTION_STUDENTS,
    COLLECTION_BEACONS,
    COLLECTION_ATTENDANCE,
)

if USE_FIREBASE:
    import firebase_admin
    from firebase_admin import credentials, firestore

class FirebaseHandler:
    """
    Handles all Firestore database operations.
    Supports MOCK mode for local testing without Firebase.
    """

    def __init__(self, use_firebase: bool = None):
        """
        Initialize Firebase handler.
        
        Args:
            use_firebase: Override config setting. None uses config.py value.
        """
        self._use_firebase = use_firebase if use_firebase is not None else USE_FIREBASE
        self._db = None

        self._mock_students: Dict[str, dict] = {}
        self._mock_beacons: Dict[str, dict] = {}
        self._mock_attendance: List[dict] = []

        if self._use_firebase:
            self._init_firebase()
        else:
            print("⚡ FirebaseHandler running in MOCK mode (no Firebase connection)")

    def _init_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            if not firebase_admin._apps:
                if not os.path.exists(FIREBASE_CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"Firebase credentials not found at: {FIREBASE_CREDENTIALS_PATH}\n"
                        f"Download from: Firebase Console → Project Settings → "
                        f"Service Accounts → Generate New Private Key"
                    )
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)

            self._db = firestore.client()
            print("✅ Firebase initialized successfully")
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            print("⚡ Falling back to MOCK mode")
            self._use_firebase = False

    def add_student(self, student_id: str, name: str, email: str, device_id: str) -> bool:
        """Add a new student record."""
        data = {
            "id": student_id,
            "name": name,
            "email": email,
            "device_id": device_id,
            "registered_at": datetime.now().isoformat(),
        }

        if self._use_firebase:
            try:
                self._db.collection(COLLECTION_STUDENTS).document(student_id).set(data)
                return True
            except Exception as e:
                print(f"❌ Error adding student: {e}")
                return False
        else:
            self._mock_students[student_id] = data
            return True

    def get_student_by_device(self, device_id: str) -> Optional[dict]:
        """Look up a student by their device ID."""
        if self._use_firebase:
            try:
                docs = (
                    self._db.collection(COLLECTION_STUDENTS)
                    .where("device_id", "==", device_id)
                    .limit(1)
                    .get()
                )
                for doc in docs:
                    return doc.to_dict()
                return None
            except Exception as e:
                print(f"❌ Error querying student: {e}")
                return None
        else:
            for student in self._mock_students.values():
                if student["device_id"] == device_id:
                    return student
            return None

    def get_all_students(self) -> List[dict]:
        """Get all registered students."""
        if self._use_firebase:
            try:
                docs = self._db.collection(COLLECTION_STUDENTS).get()
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                print(f"❌ Error getting students: {e}")
                return []
        else:
            return list(self._mock_students.values())

    def delete_student(self, student_id: str) -> bool:
        """Delete a student record."""
        if self._use_firebase:
            try:
                self._db.collection(COLLECTION_STUDENTS).document(student_id).delete()
                return True
            except Exception as e:
                print(f"❌ Error deleting student: {e}")
                return False
        else:
            self._mock_students.pop(student_id, None)
            return True

    def add_beacon(self, beacon_id: str, device_name: str, classroom: str, active: bool = True) -> bool:
        """Register a beacon."""
        data = {
            "device_name": device_name,
            "classroom": classroom,
            "rssi_threshold_present": -75,
            "rssi_threshold_exit": -85,
            "active": active,
        }

        if self._use_firebase:
            try:
                self._db.collection(COLLECTION_BEACONS).document(beacon_id).set(data)
                return True
            except Exception as e:
                print(f"❌ Error adding beacon: {e}")
                return False
        else:
            self._mock_beacons[beacon_id] = data
            return True

    def get_all_beacons(self) -> List[dict]:
        """Get all registered beacons."""
        if self._use_firebase:
            try:
                docs = self._db.collection(COLLECTION_BEACONS).get()
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                print(f"❌ Error getting beacons: {e}")
                return []
        else:
            return list(self._mock_beacons.values())

    def delete_beacon(self, beacon_id: str) -> bool:
        """Delete a beacon."""
        if self._use_firebase:
            try:
                self._db.collection(COLLECTION_BEACONS).document(beacon_id).delete()
                return True
            except Exception as e:
                print(f"❌ Error deleting beacon: {e}")
                return False
        else:
            self._mock_beacons.pop(beacon_id, None)
            return True

    def mark_present(self, student_id: str, student_name: str, rssi: int, classroom: str) -> Optional[str]:
        """
        Record a PRESENT attendance entry.
        Returns the document ID on success, None on failure.
        """
        data = {
            "student_id": student_id,
            "student_name": student_name,
            "entry_time": datetime.now().isoformat(),
            "exit_time": None,
            "status": "PRESENT",
            "date": date.today().isoformat(),
            "classroom": classroom,
            "rssi": rssi,
        }

        if self._use_firebase:
            try:
                doc_ref = self._db.collection(COLLECTION_ATTENDANCE).add(data)
                return doc_ref[1].id
            except Exception as e:
                print(f"❌ Error marking present: {e}")
                return None
        else:
            doc_id = f"att_{student_id}_{len(self._mock_attendance)}"
            data["doc_id"] = doc_id
            self._mock_attendance.append(data)
            return doc_id

    def mark_exit(self, student_id: str, target_date: str = None) -> bool:
        """
        Update the latest PRESENT record for a student to EXIT.
        """
        if target_date is None:
            target_date = date.today().isoformat()

        if self._use_firebase:
            try:
                docs = (
                    self._db.collection(COLLECTION_ATTENDANCE)
                    .where("student_id", "==", student_id)
                    .where("date", "==", target_date)
                    .where("status", "==", "PRESENT")
                    .order_by("entry_time", direction=firestore.Query.DESCENDING)
                    .limit(1)
                    .get()
                )
                for doc in docs:
                    doc.reference.update({
                        "exit_time": datetime.now().isoformat(),
                        "status": "EXIT",
                    })
                    return True
                return False
            except Exception as e:
                print(f"❌ Error marking exit: {e}")
                return False
        else:

            for record in reversed(self._mock_attendance):
                if (
                    record["student_id"] == student_id
                    and record["date"] == target_date
                    and record["status"] == "PRESENT"
                ):
                    record["exit_time"] = datetime.now().isoformat()
                    record["status"] = "EXIT"
                    return True
            return False

    def get_attendance_today(self, student_id: str = None) -> List[dict]:
        """
        Get attendance records for today.
        If student_id is provided, filter for that student.
        """
        today = date.today().isoformat()

        if self._use_firebase:
            try:
                query = self._db.collection(COLLECTION_ATTENDANCE).where("date", "==", today)
                if student_id:
                    query = query.where("student_id", "==", student_id)
                docs = query.get()
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                print(f"❌ Error getting attendance: {e}")
                return []
        else:
            results = []
            for record in self._mock_attendance:
                if record["date"] == today:
                    if student_id is None or record["student_id"] == student_id:
                        results.append(record)
            return results

    def get_all_attendance(self, target_date: str = None) -> List[dict]:
        """Get all attendance records for a specific date."""
        if target_date is None:
            target_date = date.today().isoformat()

        if self._use_firebase:
            try:
                docs = (
                    self._db.collection(COLLECTION_ATTENDANCE)
                    .where("date", "==", target_date)
                    .get()
                )
                return [doc.to_dict() for doc in docs]
            except Exception as e:
                print(f"❌ Error getting all attendance: {e}")
                return []
        else:
            return [r for r in self._mock_attendance if r["date"] == target_date]

    def has_active_session(self, student_id: str) -> bool:
        """Check if a student has an active PRESENT session today."""
        records = self.get_attendance_today(student_id)
        for record in records:
            if record["status"] == "PRESENT":
                return True
        return False
