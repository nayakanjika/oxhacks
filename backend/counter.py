"""
Hand-built queue counter: laptop webcam -> count people -> send number to the API.
Privacy: frames are processed in memory and never saved or uploaded. Only the NUMBER is sent.

Run:  python counter.py --location 1 --api http://127.0.0.1:8000
Press q in the preview window to stop.
"""
import argparse
import time

import cv2
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--location", type=int, required=True)
parser.add_argument("--api", default="http://127.0.0.1:8000")
parser.add_argument("--every", type=int, default=10, help="seconds between uploads")
args = parser.parse_args()

# OpenCV's built-in person detector (no cloud, no AI service: good for the Handmade prize)
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

cam = cv2.VideoCapture(0)
last_sent = 0
recent = []

while True:
    ok, frame = cam.read()
    if not ok:
        break
    frame = cv2.resize(frame, (640, 480))
    boxes, _ = hog.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)
    recent.append(len(boxes))
    recent = recent[-15:]  # smooth over the last ~15 frames

    for (x, y, w, h) in boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
    count = round(sum(recent) / len(recent))
    cv2.putText(frame, f"People in queue: {count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.imshow("Queueless counter (preview only, nothing saved)", frame)

    if time.time() - last_sent > args.every:
        try:
            requests.post(f"{args.api}/counts",
                          json={"location_id": args.location, "people_count": count}, timeout=5)
            print("sent", count)
        except requests.RequestException as e:
            print("upload failed:", e)
        last_sent = time.time()

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()
