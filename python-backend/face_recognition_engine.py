"""
============================================================
  Smart Attendance System - Face Recognition Engine
  Optional face-based attendance verification using OpenCV.
  
  Supports two modes:
    1. STANDALONE: Face-only attendance (no BLE required)
    2. HYBRID: Face + BLE combined verification
  
  Uses OpenCV's Haar Cascade for face detection and
  LBPH (Local Binary Pattern Histogram) for recognition.
============================================================
"""

import os
import json
import time
from datetime import datetime, date
from typing import Optional, Tuple, Dict, List

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("[WARN] opencv-python not installed. Face recognition disabled.")
    print("       Install with: pip install opencv-python opencv-contrib-python")

from config import DEFAULT_CLASSROOM

FACE_DATA_DIR = os.path.join(os.path.dirname(__file__), "face_data")
FACE_IMAGES_DIR = os.path.join(FACE_DATA_DIR, "images")
FACE_MODEL_PATH = os.path.join(FACE_DATA_DIR, "face_model.yml")
FACE_LABELS_PATH = os.path.join(FACE_DATA_DIR, "labels.json")

CASCADE_PATH = None
if OPENCV_AVAILABLE:
    CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

CONFIDENCE_THRESHOLD = 80.0

MIN_TRAINING_IMAGES = 3

class FaceRecognitionEngine:
    """
    Face recognition engine for attendance verification.
    
    Workflow:
      1. Register student faces (capture + store)
      2. Train the recognition model
      3. Verify identity via webcam capture
    """

    def __init__(self):
        if not OPENCV_AVAILABLE:
            raise RuntimeError(
                "OpenCV is required for face recognition. "
                "Install: pip install opencv-python opencv-contrib-python"
            )

        os.makedirs(FACE_IMAGES_DIR, exist_ok=True)

        self.face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if self.face_cascade.empty():
            raise RuntimeError("Failed to load Haar cascade classifier")

        self.recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1, neighbors=8, grid_x=8, grid_y=8, threshold=CONFIDENCE_THRESHOLD
        )

        self._label_map: Dict[int, str] = {}
        self._student_names: Dict[str, str] = {}
        self._model_trained = False

        self._load_model()

    def register_face_from_image(
        self,
        student_id: str,
        student_name: str,
        image_data: bytes,
        image_index: int = 0,
    ) -> dict:
        """
        Register a student's face from an image (e.g., webcam capture).
        
        Args:
            student_id: Student identifier
            student_name: Student name
            image_data: Raw image bytes (JPEG/PNG)
            image_index: Index for multiple captures
            
        Returns:
            dict with status and message
        """
        try:

            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return {"success": False, "message": "Invalid image data"}

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )

            if len(faces) == 0:
                return {"success": False, "message": "No face detected in the image"}

            if len(faces) > 1:
                return {"success": False, "message": "Multiple faces detected. Please capture one face at a time."}

            (x, y, w, h) = faces[0]
            face_roi = gray[y:y+h, x:x+w]

            face_resized = cv2.resize(face_roi, (200, 200))

            student_dir = os.path.join(FACE_IMAGES_DIR, student_id)
            os.makedirs(student_dir, exist_ok=True)
            filepath = os.path.join(student_dir, f"face_{image_index}.jpg")
            cv2.imwrite(filepath, face_resized)

            self._student_names[student_id] = student_name

            return {
                "success": True,
                "message": f"Face registered for {student_name} (image {image_index})",
                "face_location": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
            }

        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def capture_faces_from_camera(
        self,
        student_id: str,
        student_name: str,
        num_captures: int = 5,
        camera_index: int = 0,
    ) -> dict:
        """
        Capture multiple face images from webcam for registration.
        
        Args:
            student_id: Student identifier
            student_name: Student name
            num_captures: Number of face images to capture
            camera_index: Camera device index
            
        Returns:
            dict with status and captured count
        """
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return {"success": False, "message": "Cannot access camera"}

        student_dir = os.path.join(FACE_IMAGES_DIR, student_id)
        os.makedirs(student_dir, exist_ok=True)

        captured = 0
        frame_count = 0
        print(f"[FACE] Capturing {num_captures} face images for {student_name}...")
        print("[FACE] Look at the camera. Press 'q' to cancel.")

        while captured < num_captures:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(
                    frame, f"Capture {captured+1}/{num_captures}",
                    (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )

            cv2.imshow("Face Registration", frame)

            if len(faces) == 1 and frame_count % 10 == 0:
                (x, y, w, h) = faces[0]
                face_roi = gray[y:y+h, x:x+w]
                face_resized = cv2.resize(face_roi, (200, 200))
                filepath = os.path.join(student_dir, f"face_{captured}.jpg")
                cv2.imwrite(filepath, face_resized)
                captured += 1
                print(f"  [OK] Captured image {captured}/{num_captures}")

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        self._student_names[student_id] = student_name

        return {
            "success": captured >= MIN_TRAINING_IMAGES,
            "message": f"Captured {captured}/{num_captures} images for {student_name}",
            "captured": captured,
        }

    def train_model(self) -> dict:
        """
        Train the face recognition model using all registered faces.
        Must be called after registering faces and before verification.
        
        Returns:
            dict with training results
        """
        faces = []
        labels = []
        label_map = {}
        student_names = {}
        label_counter = 0

        if not os.path.exists(FACE_IMAGES_DIR):
            return {"success": False, "message": "No face data directory found"}

        for student_id in os.listdir(FACE_IMAGES_DIR):
            student_dir = os.path.join(FACE_IMAGES_DIR, student_id)
            if not os.path.isdir(student_dir):
                continue

            image_files = [
                f for f in os.listdir(student_dir) 
                if f.endswith(('.jpg', '.png', '.jpeg'))
            ]

            if len(image_files) < MIN_TRAINING_IMAGES:
                print(f"  [WARN] {student_id}: Only {len(image_files)} images (need {MIN_TRAINING_IMAGES})")
                continue

            label_map[label_counter] = student_id
            student_names[student_id] = self._student_names.get(student_id, student_id)

            for img_file in image_files:
                img_path = os.path.join(student_dir, img_file)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img_resized = cv2.resize(img, (200, 200))
                    faces.append(img_resized)
                    labels.append(label_counter)

            label_counter += 1

        if len(faces) == 0:
            return {"success": False, "message": "No valid training data found"}

        self.recognizer.train(faces, np.array(labels))
        self._label_map = label_map
        self._student_names = student_names
        self._model_trained = True

        self._save_model()

        return {
            "success": True,
            "message": f"Model trained with {len(faces)} images from {label_counter} students",
            "students": label_counter,
            "images": len(faces),
        }

    def verify_face_from_image(self, image_data: bytes) -> dict:
        """
        Verify a face from image data (e.g., from webcam capture in browser).
        
        Args:
            image_data: Raw image bytes (JPEG/PNG)
            
        Returns:
            dict with verification result
        """
        if not self._model_trained:
            return {"verified": False, "message": "Model not trained. Register faces first."}

        try:

            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return {"verified": False, "message": "Invalid image data"}

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )

            if len(faces) == 0:
                return {"verified": False, "message": "No face detected"}

            largest = max(faces, key=lambda f: f[2] * f[3])
            (x, y, w, h) = largest
            face_roi = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_roi, (200, 200))

            label, confidence = self.recognizer.predict(face_resized)

            if confidence < CONFIDENCE_THRESHOLD:
                student_id = self._label_map.get(label, "unknown")
                student_name = self._student_names.get(student_id, "Unknown")
                return {
                    "verified": True,
                    "student_id": student_id,
                    "student_name": student_name,
                    "confidence": round(100 - confidence, 2),
                    "message": f"Verified: {student_name} (confidence: {round(100 - confidence, 2)}%)",
                }
            else:
                return {
                    "verified": False,
                    "confidence": round(100 - confidence, 2),
                    "message": f"Face not recognized (confidence too low: {round(100 - confidence, 2)}%)",
                }

        except Exception as e:
            return {"verified": False, "message": f"Error: {str(e)}"}

    def verify_face_from_camera(self, camera_index: int = 0, timeout: int = 10) -> dict:
        """
        Verify a face using live camera feed.
        
        Args:
            camera_index: Camera device index
            timeout: Max seconds to wait for valid face
            
        Returns:
            dict with verification result
        """
        if not self._model_trained:
            return {"verified": False, "message": "Model not trained"}

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return {"verified": False, "message": "Cannot access camera"}

        start_time = time.time()
        result = {"verified": False, "message": "Timeout - no face verified"}

        print("[FACE] Looking for face... Press 'q' to cancel.")

        while time.time() - start_time < timeout:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )

            for (x, y, w, h) in faces:
                face_roi = gray[y:y+h, x:x+w]
                face_resized = cv2.resize(face_roi, (200, 200))

                label, confidence = self.recognizer.predict(face_resized)

                if confidence < CONFIDENCE_THRESHOLD:
                    student_id = self._label_map.get(label, "unknown")
                    student_name = self._student_names.get(student_id, "Unknown")
                    conf_pct = round(100 - confidence, 2)

                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, f"{student_name} ({conf_pct}%)",
                                (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    result = {
                        "verified": True,
                        "student_id": student_id,
                        "student_name": student_name,
                        "confidence": conf_pct,
                        "message": f"Verified: {student_name} ({conf_pct}%)",
                    }
                    cv2.imshow("Face Verification", frame)
                    cv2.waitKey(1500)
                    cap.release()
                    cv2.destroyAllWindows()
                    return result
                else:

                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(frame, "Unknown",
                                (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow("Face Verification", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        return result

    def _save_model(self):
        """Save trained model and label mappings to disk."""
        try:
            self.recognizer.write(FACE_MODEL_PATH)
            data = {
                "label_map": {str(k): v for k, v in self._label_map.items()},
                "student_names": self._student_names,
            }
            with open(FACE_LABELS_PATH, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"[FACE] Model saved to {FACE_MODEL_PATH}")
        except Exception as e:
            print(f"[FACE] Error saving model: {e}")

    def _load_model(self):
        """Load trained model and label mappings from disk."""
        if os.path.exists(FACE_MODEL_PATH) and os.path.exists(FACE_LABELS_PATH):
            try:
                self.recognizer.read(FACE_MODEL_PATH)
                with open(FACE_LABELS_PATH, 'r') as f:
                    data = json.load(f)
                self._label_map = {int(k): v for k, v in data["label_map"].items()}
                self._student_names = data.get("student_names", {})
                self._model_trained = True
                print(f"[FACE] Model loaded ({len(self._label_map)} students)")
            except Exception as e:
                print(f"[FACE] Error loading model: {e}")
                self._model_trained = False

    def get_registered_students(self) -> List[str]:
        """Get list of student IDs with registered faces."""
        if not os.path.exists(FACE_IMAGES_DIR):
            return []
        return [
            d for d in os.listdir(FACE_IMAGES_DIR)
            if os.path.isdir(os.path.join(FACE_IMAGES_DIR, d))
        ]

    def get_image_count(self, student_id: str) -> int:
        """Get number of registered face images for a student."""
        student_dir = os.path.join(FACE_IMAGES_DIR, student_id)
        if not os.path.exists(student_dir):
            return 0
        return len([
            f for f in os.listdir(student_dir)
            if f.endswith(('.jpg', '.png', '.jpeg'))
        ])

    def is_model_trained(self) -> bool:
        """Check if the recognition model is trained and ready."""
        return self._model_trained

    def delete_student_faces(self, student_id: str) -> bool:
        """Delete all face data for a student."""
        import shutil
        student_dir = os.path.join(FACE_IMAGES_DIR, student_id)
        if os.path.exists(student_dir):
            shutil.rmtree(student_dir)
            return True
        return False
