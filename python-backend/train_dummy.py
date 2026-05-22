import os
import cv2
import numpy as np

from face_recognition_engine import FaceRecognitionEngine, FACE_IMAGES_DIR

def generate_dummy_faces():
    print("Generating dummy faces for Admin and Test...")
    engine = FaceRecognitionEngine()
    
    os.makedirs(FACE_IMAGES_DIR, exist_ok=True)
    
    users = [
        {"id": "ADMIN01", "name": "Admin User"},
        {"id": "TEST01", "name": "Test User"}
    ]

    for user in users:
        student_dir = os.path.join(FACE_IMAGES_DIR, user["id"])
        os.makedirs(student_dir, exist_ok=True)

        for i in range(5):

            base_color = 100 if user["id"] == "ADMIN01" else 150
            img = np.full((200, 200), base_color + (i * 10), dtype=np.uint8)

            cv2.circle(img, (60, 60), 20, 0, -1)
            cv2.circle(img, (140, 60), 20, 0, -1)

            cv2.rectangle(img, (60, 140), (140, 160), 0, -1)

            noise = np.random.normal(0, 15, img.shape).astype(np.uint8)
            img = cv2.add(img, noise)
            
            filepath = os.path.join(student_dir, f"face_{i}.jpg")
            cv2.imwrite(filepath, img)

        engine._student_names[user["id"]] = user["name"]

    res = engine.train_model()
    if res["success"]:
        print(f"Success! {res['message']}")
    else:
        print(f"Failed to train model: {res['message']}")

if __name__ == "__main__":
    generate_dummy_faces()
