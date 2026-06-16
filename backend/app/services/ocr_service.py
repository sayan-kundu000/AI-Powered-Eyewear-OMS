import re
import logging
import cv2
import numpy as np
from typing import Dict, Any, Tuple

logger = logging.getLogger("ocr_service")

class OCRService:
    @staticmethod
    def preprocess_image(image_bytes: bytes) -> np.ndarray:
        """
        OpenCV image preprocessing pipeline:
        - Image loading
        - Noise reduction (Bilateral filter to preserve edges)
        - Binarization/Adaptive thresholding
        - Orientation check & correction
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image bytes. OpenCV could not decode.")

        # 1. Grayscale conversion
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Noise reduction using Bilateral Filter
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)

        # 3. Adaptive thresholding for high contrast text
        thresholded = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # 4. Orientation checking (dummy rotation checking for orientation correction)
        # In a real environment, you'd use Tesseract's OSD (Orientation and Script Detection)
        # Here we verify text density or basic contours. If height > width, orientation is normal.
        # Otherwise, rotate by 90 degrees if required.
        h, w = thresholded.shape
        if w > h * 1.5:
            # Rotate 90 degrees clockwise as correction
            thresholded = cv2.rotate(thresholded, cv2.ROTATE_90_CLOCKWISE)
            logger.info("Orientation correction applied (rotated 90 deg clockwise).")

        return thresholded

    @staticmethod
    def parse_prescription_text(text: str) -> Dict[str, float]:
        """
        Parse SPH, CYL, AXIS, ADD, PD values from raw OCR text using regular expressions.
        """
        results = {
            "sph_od": 0.0, "cyl_od": 0.0, "axis_od": 0, "add_od": 0.0,
            "sph_os": 0.0, "cyl_os": 0.0, "axis_os": 0, "add_os": 0.0,
            "pd": 63.0
        }
        
        # Regex mappings
        sph_matches = re.findall(r"(?:SPH|SPHERE)?\s*[:=]?\s*([+-]\d+\.\d{2})", text, re.IGNORECASE)
        cyl_matches = re.findall(r"(?:CYL|CYLINDER)?\s*[:=]?\s*([+-]\d+\.\d{2})", text, re.IGNORECASE)
        axis_matches = re.findall(r"(?:AXIS|AX)?\s*[:=]?\s*(\d{1,3})", text, re.IGNORECASE)
        add_matches = re.findall(r"(?:ADD|ADDITION)?\s*[:=]?\s*([+-]?\d+\.\d{2})", text, re.IGNORECASE)
        pd_matches = re.search(r"(?:PD|PUPIL)\s*[:=]?\s*(\d{2}(?:\.\d)?)", text, re.IGNORECASE)

        if len(sph_matches) >= 2:
            results["sph_od"] = float(sph_matches[0])
            results["sph_os"] = float(sph_matches[1])
        elif len(sph_matches) == 1:
            results["sph_od"] = float(sph_matches[0])
            results["sph_os"] = float(sph_matches[0])
            
        if len(cyl_matches) >= 2:
            results["cyl_od"] = float(cyl_matches[0])
            results["cyl_os"] = float(cyl_matches[1])
        elif len(cyl_matches) == 1:
            results["cyl_od"] = float(cyl_matches[0])
            results["cyl_os"] = float(cyl_matches[0])
            
        if len(axis_matches) >= 2:
            results["axis_od"] = int(axis_matches[0])
            results["axis_os"] = int(axis_matches[1])
        elif len(axis_matches) == 1:
            results["axis_od"] = int(axis_matches[0])
            results["axis_os"] = int(axis_matches[0])
            
        if len(add_matches) >= 2:
            results["add_od"] = float(add_matches[0])
            results["add_os"] = float(add_matches[1])
        elif len(add_matches) == 1:
            results["add_od"] = float(add_matches[0])
            results["add_os"] = float(add_matches[0])
            
        if pd_matches:
            results["pd"] = float(pd_matches.group(1))

        return results

    @staticmethod
    def extract_from_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Orchestrate preprocessing, text extraction, and parameter parsing.
        """
        # Perform image preprocessing (if image file)
        is_pdf = filename.lower().endswith(".pdf")
        
        raw_text = ""
        if not is_pdf:
            try:
                preprocessed = OCRService.preprocess_image(file_bytes)
                # In production, we pass preprocessed image to pytesseract / easyocr
                # We mock/extract text for sandbox out-of-the-box support:
                raw_text = (
                    "Prescription Date: 2026-06-14\n"
                    "OD (Right Eye): SPH -2.50 CYL -0.75 AXIS 95 ADD +1.50\n"
                    "OS (Left Eye): SPH -2.25 CYL -0.50 AXIS 90 ADD +1.50\n"
                    "PD: 64.0 mm\n"
                    "Signed: Dr. Amanda Croft\n"
                )
            except Exception as e:
                logger.error(f"Image preprocessing failed: {e}")
                raw_text = "ERROR: Preprocessing failed"
        else:
            # Mock PDF extraction
            raw_text = (
                "Prescription Date: 2026-06-14\n"
                "OD (Right Eye): SPH -1.75 CYL -1.00 AXIS 105 ADD +2.00\n"
                "OS (Left Eye): SPH -1.50 CYL -1.00 AXIS 110 ADD +2.00\n"
                "PD: 62.0 mm\n"
            )

        parsed_values = OCRService.parse_prescription_text(raw_text)
        return {
            "raw_text": raw_text,
            "parsed_values": parsed_values
        }
