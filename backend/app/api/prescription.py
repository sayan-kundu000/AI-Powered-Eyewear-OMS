import json
import torch
import numpy as np
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Prescription, Customer
from app.schemas import PrescriptionCreate, PrescriptionResponse, EmbeddingGenerateRequest, EmbeddingSearchRequest
from app.api.auth import get_current_user, RoleChecker
from app.ai.transformer import model as transformer_model

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

role_staff_or_admin = RoleChecker(["STORE_STAFF", "LAB_TECH"])

@router.post("", response_model=PrescriptionResponse, dependencies=[Depends(role_staff_or_admin)])
def create_prescription(rx_in: PrescriptionCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == rx_in.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # Generate vector embedding for similarity search
    # Vector: [sph_od, cyl_od, axis_od, add_od, sph_os, cyl_os, axis_os, add_os, pd]
    num_list = [
        rx_in.sph_od, rx_in.cyl_od, float(rx_in.axis_od), rx_in.add_od,
        rx_in.sph_os, rx_in.cyl_os, float(rx_in.axis_os), rx_in.add_os,
        rx_in.pd
    ]
    
    with torch.no_grad():
        t_input = torch.tensor([num_list], dtype=torch.float32)
        emb_tensor = transformer_model.generate_embeddings(t_input).squeeze(0)
        emb_list = emb_tensor.tolist()
        
    prescription = Prescription(
        customer_id=rx_in.customer_id,
        sph_od=rx_in.sph_od,
        cyl_od=rx_in.cyl_od,
        axis_od=rx_in.axis_od,
        add_od=rx_in.add_od,
        sph_os=rx_in.sph_os,
        cyl_os=rx_in.cyl_os,
        axis_os=rx_in.axis_os,
        add_os=rx_in.add_os,
        pd=rx_in.pd,
        embedding=json.dumps(emb_list),
        is_validated=True
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription

@router.get("/{rx_id}", response_model=PrescriptionResponse, dependencies=[Depends(role_staff_or_admin)])
def get_prescription_by_id(rx_id: int, db: Session = Depends(get_db)):
    rx = db.query(Prescription).filter(Prescription.id == rx_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return rx

@router.put("/{rx_id}/validate", response_model=PrescriptionResponse, dependencies=[Depends(role_staff_or_admin)])
def validate_prescription_manual(rx_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Allow manual correction and approval of OCR-extracted values.
    """
    rx = db.query(Prescription).filter(Prescription.id == rx_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
        
    rx.is_validated = True
    rx.verified_by = current_user.id
    db.commit()
    db.refresh(rx)
    return rx

@router.post("/embeddings/generate", tags=["AI Extractions"])
def generate_embedding_only(req: EmbeddingGenerateRequest):
    """
    Generate embedding dense vector from a single eye parameters.
    """
    # Create full 9-dim input vector
    num_list = [req.sph, req.cyl, float(req.axis), req.add_val, req.sph, req.cyl, float(req.axis), req.add_val, 64.0]
    with torch.no_grad():
        t_input = torch.tensor([num_list], dtype=torch.float32)
        emb = transformer_model.generate_embeddings(t_input).squeeze(0).tolist()
    return {"embedding": emb}

@router.post("/embeddings/search", tags=["AI Extractions"])
def search_similar_prescriptions(req: EmbeddingSearchRequest, db: Session = Depends(get_db)):
    """
    Perform semantic prescription search using Cosine Similarity or Euclidean Distance in Python.
    Suggests similar historical orders and lens configurations.
    """
    query_vector = np.array(req.embedding)
    prescriptions = db.query(Prescription).filter(Prescription.embedding.isnot(None)).all()
    
    scored_results = []
    for rx in prescriptions:
        try:
            rx_vector = np.array(json.loads(rx.embedding))
            if len(rx_vector) != len(query_vector):
                continue
                
            if req.metric == "cosine":
                dot = np.dot(query_vector, rx_vector)
                norm_q = np.linalg.norm(query_vector)
                norm_r = np.linalg.norm(rx_vector)
                score = dot / (norm_q * norm_r) if (norm_q * norm_r) > 0 else 0.0
            else:
                # Euclidean
                score = np.linalg.norm(query_vector - rx_vector)
                
            scored_results.append({
                "prescription_id": rx.id,
                "customer_id": rx.customer_id,
                "sph_od": rx.sph_od,
                "cyl_od": rx.cyl_od,
                "sph_os": rx.sph_os,
                "cyl_os": rx.cyl_os,
                "pd": rx.pd,
                "score": float(score)
            })
        except Exception:
            continue
            
    # Sort results
    if req.metric == "cosine":
        # Higher score is better
        scored_results.sort(key=lambda x: x["score"], reverse=True)
    else:
        # Lower Euclidean is better
        scored_results.sort(key=lambda x: x["score"])
        
    return scored_results[:req.top_k]
