# logic/detector.py
import cv2
import numpy as np

class FloorPlanDetector:
    def __init__(self, debug_mode=False, output_dir=".", remove_captions=True, detection_mode="heuristic_only"):
        self.debug_mode = debug_mode
        self.output_dir = output_dir
        self.remove_captions = remove_captions
        self.detection_mode = detection_mode

    def detect(self, img):
        """
        A basic Computer Vision implementation to detect rooms 
        based on finding closed contours (outlines) in the image.
        """
        # 1. Convert image to grayscale (black and white)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Blur the image slightly to remove background noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 3. Apply a threshold to make walls purely black and empty space purely white
        _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY_INV)
        
        # 4. Find contours (shapes/outlines) in the image
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_rooms = []
        img_area = img.shape[0] * img.shape[1]
        
        # 5. Filter out tiny dots or massive borders. Keep medium-sized shapes as "rooms".
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if img_area * 0.005 < area < img_area * 0.9:  
                detected_rooms.append(cnt)

        # Return our actual detected rooms instead of an empty list!
        return {
            "rooms": detected_rooms,
            "doors": [],
            "windows": [],
            "furniture": [],
            "stairs": [],
            "flow_terminals": []
        }