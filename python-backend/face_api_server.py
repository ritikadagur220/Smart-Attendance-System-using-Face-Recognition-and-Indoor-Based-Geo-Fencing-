"""
============================================================
  Smart Attendance System - Face Attendance API Server
  HTTP server providing face recognition endpoints for
  the web dashboard (webcam capture -> face verify -> mark attendance).
  
  Endpoints:
    POST /api/face/register     - Register a face image
    POST /api/face/verify       - Verify face and mark attendance
    POST /api/face/train        - Train the recognition model
    GET  /api/face/status       - Get face recognition status
    GET  /api/attendance/today  - Get today's attendance
    
  Usage:
    python face_api_server.py
    
  Then open the web dashboard and use the Face Attendance tab.
============================================================
"""

import os
import sys
import json
import base64
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(__file__))

from config import DEFAULT_CLASSROOM
from attendance_engine import AttendanceEngine

face_engine = None
attendance_engine = AttendanceEngine()

face_attendance_log = []

def get_face_engine():
    """Lazy-load face recognition engine."""
    global face_engine
    if face_engine is None:
        try:
            from face_recognition_engine import FaceRecognitionEngine
            face_engine = FaceRecognitionEngine()
        except Exception as e:
            print(f"[WARN] Face recognition not available: {e}")
    return face_engine

class FaceAttendanceHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for face attendance API."""

    def translate_path(self, path):
        """Serve files from web-dashboard directory."""
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web-dashboard")
        if path == "/" or path == "":
            path = "/index.html"
        filepath = os.path.join(web_dir, path.lstrip("/"))
        return filepath

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/face/status":
            self._handle_face_status()
        elif parsed.path == "/api/attendance/today":
            self._handle_attendance_today()
        elif parsed.path.startswith("/api/"):
            self._send_json(404, {"error": "Endpoint not found"})
        else:

            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        if parsed.path == "/api/face/register":
            self._handle_face_register(data)
        elif parsed.path == "/api/face/verify":
            self._handle_face_verify(data)
        elif parsed.path == "/api/face/train":
            self._handle_face_train()
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def _handle_face_status(self):
        """GET /api/face/status"""
        engine = get_face_engine()
        if engine is None:
            self._send_json(200, {
                "available": False,
                "trained": False,
                "message": "OpenCV not installed",
            })
            return

        registered = engine.get_registered_students()
        self._send_json(200, {
            "available": True,
            "trained": engine.is_model_trained(),
            "registered_students": len(registered),
            "students": registered,
        })

    def _handle_face_register(self, data):
        """POST /api/face/register - Register face from base64 image."""
        engine = get_face_engine()
        if engine is None:
            self._send_json(500, {"error": "Face recognition not available"})
            return

        student_id = data.get("student_id")
        student_name = data.get("student_name")
        image_b64 = data.get("image")
        image_index = data.get("index", 0)

        if not all([student_id, student_name, image_b64]):
            self._send_json(400, {"error": "Missing: student_id, student_name, image"})
            return

        try:

            if "," in image_b64:
                image_b64 = image_b64.split(",")[1]
            image_data = base64.b64decode(image_b64)
        except Exception as e:
            self._send_json(400, {"error": f"Invalid base64 image: {str(e)}"})
            return

        result = engine.register_face_from_image(student_id, student_name, image_data, image_index)
        self._send_json(200, result)

    def _handle_face_verify(self, data):
        """POST /api/face/verify - Verify face and mark attendance."""
        engine = get_face_engine()
        if engine is None:
            self._send_json(500, {"error": "Face recognition not available"})
            return

        image_b64 = data.get("image")
        if not image_b64:
            self._send_json(400, {"error": "Missing: image"})
            return

        try:
            if "," in image_b64:
                image_b64 = image_b64.split(",")[1]
            image_data = base64.b64decode(image_b64)
        except Exception:
            self._send_json(400, {"error": "Invalid base64 image"})
            return

        result = engine.verify_face_from_image(image_data)

        if result.get("verified"):

            student_id = result["student_id"]
            student_name = result["student_name"]
            now = datetime.now()

            already_present = any(
                r["student_id"] == student_id and r["status"] == "PRESENT"
                and r["date"] == date.today().isoformat()
                for r in face_attendance_log
            )

            if already_present:
                result["attendance"] = "ALREADY_PRESENT"
                result["message"] += " (already marked today)"
            else:
                record = {
                    "student_id": student_id,
                    "student_name": student_name,
                    "entry_time": now.isoformat(),
                    "exit_time": None,
                    "status": "PRESENT",
                    "date": date.today().isoformat(),
                    "classroom": DEFAULT_CLASSROOM,
                    "method": "FACE",
                    "confidence": result.get("confidence", 0),
                }
                face_attendance_log.append(record)
                result["attendance"] = "MARKED_PRESENT"

        self._send_json(200, result)

    def _handle_face_train(self):
        """POST /api/face/train - Train the model."""
        engine = get_face_engine()
        if engine is None:
            self._send_json(500, {"error": "Face recognition not available"})
            return

        result = engine.train_model()
        self._send_json(200, result)

    def _handle_attendance_today(self):
        """GET /api/attendance/today - Get today's attendance."""
        today = date.today().isoformat()
        today_records = [r for r in face_attendance_log if r["date"] == today]
        self._send_json(200, {"records": today_records, "count": len(today_records)})

    def _send_json(self, status_code, data):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _add_cors_headers(self):
        """Add CORS headers for browser requests."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[API] {args[0]}")

def run_server(port=8080):
    """Start the face attendance API server."""
    server = HTTPServer(("0.0.0.0", port), FaceAttendanceHandler)
    print("=" * 60)
    print("  Smart Attendance - Face Recognition API Server")
    print("=" * 60)
    print(f"  Server:    http://localhost:{port}")
    print(f"  Dashboard: http://localhost:{port}/index.html")
    print(f"  API:       http://localhost:{port}/api/face/status")
    print("=" * 60)

    engine = get_face_engine()
    if engine:
        print("  [OK] Face recognition engine loaded")
        if engine.is_model_trained():
            print(f"  [OK] Model trained ({len(engine.get_registered_students())} students)")
        else:
            print("  [INFO] No trained model -- register faces first")
    else:
        print("  [WARN] Face recognition unavailable (install opencv-contrib-python)")

    print(f"\n  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[API] Server stopped")
        server.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
