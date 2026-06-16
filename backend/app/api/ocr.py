import json
import torch
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Prescription, Customer
from app.api.auth import get_current_user, RoleChecker
from app.services.ocr_service import OCRService
from app.ai.transformer import model as transformer_model

router = APIRouter(prefix="/ocr", tags=["OCR Extraction"])

role_staff_or_admin = RoleChecker(["STORE_STAFF", "LAB_TECH"])

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB limit

@router.post("", dependencies=[Depends(role_staff_or_admin)])
def extract_prescription_ocr(
    customer_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Verify file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds maximum size limit of 500 MB.")
        
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")
        
    # Read file bytes
    file_bytes = file.file.read()
    
    # 2. Run OCR Extraction Service
    try:
        extraction = OCRService.extract_from_file(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"OCR processing failed: {str(e)}")
        
    vals = extraction["parsed_values"]
    
    # Generate embedding
    num_list = [
        vals["sph_od"], vals["cyl_od"], float(vals["axis_od"]), vals["add_od"],
        vals["sph_os"], vals["cyl_os"], float(vals["axis_os"]), vals["add_os"],
        vals["pd"]
    ]
    with torch.no_grad():
        t_input = torch.tensor([num_list], dtype=torch.float32)
        emb = transformer_model.generate_embeddings(t_input).squeeze(0).tolist()
        
    # 3. Save to database as unvalidated prescription
    prescription = Prescription(
        customer_id=customer_id,
        sph_od=vals["sph_od"],
        cyl_od=vals["cyl_od"],
        axis_od=vals["axis_od"],
        add_od=vals["add_od"],
        sph_os=vals["sph_os"],
        cyl_os=vals["cyl_os"],
        axis_os=vals["axis_os"],
        add_os=vals["add_os"],
        pd=vals["pd"],
        pdf_url=f"/static/prescriptions/{file.filename}",
        raw_ocr_text=extraction["raw_text"],
        embedding=json.dumps(emb),
        is_validated=False
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    
    return {
        "prescription_id": prescription.id,
        "raw_text": extraction["raw_text"],
        "extracted_values": vals,
        "is_validated": prescription.is_validated
    }
