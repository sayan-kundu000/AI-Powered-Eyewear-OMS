import pytest
import torch
import numpy as np
from app.ai.transformer import PrescriptionTransformer, model as default_transformer
from app.ai.qc_vision import QCCNNModel, qc_vision_engine
from app.ai.models_registry import registry as ml_registry
from sqlalchemy.orm import Session

def test_custom_transformer_embedding_shape():
    """
    Ensure the custom transformer Encoder handles projecting 9-dimensional values
    into normalized dense embeddings of shape [1, 128].
    """
    # [SPH OD, CYL OD, AXIS OD, ADD OD, SPH OS, CYL OS, AXIS OS, ADD OS, PD]
    numerical_input = torch.tensor([[ -2.50, -0.75, 95.0, 1.50, -2.25, -0.50, 90.0, 1.50, 64.0 ]], dtype=torch.float32)
    
    default_transformer.eval()
    with torch.no_grad():
        embedding = default_transformer.generate_embeddings(numerical_input)
        
    assert embedding.shape == (1, 128)
    # Cosine distance vectors must be unit length normalized
    norm = torch.linalg.norm(embedding, dim=1).item()
    assert pytest.approx(norm, 0.01) == 1.0

def test_qc_cnn_shapes():
    """
    Validate that QCCNNModel parses image features [batch, 3, 224, 224]
    into 3 property scores (surface quality, alignment, coating).
    """
    model = QCCNNModel()
    model.eval()
    
    dummy_img = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        out = model(dummy_img)
        
    assert out.shape == (1, 3)
    # Values mapped to sigmoid outputs between 0.0 and 1.0
    for val in out.squeeze(0).tolist():
        assert 0.0 <= val <= 1.0

def test_tabular_forecasters(db_session: Session):
    """
    Verify that models registry fits Random Forests and isolates shortages/breach probabilities.
    """
    # Fit defaults
    ml_registry.initialize_models()
    
    # SLA Breach prediction
    # Features: [current_stage_id, lens_type_id, store_id, rx_complexity, qc_failures]
    breach_prob = ml_registry.predict_sla_breach(db_session, 1, [2.0, 1.0, 1.0, 1.2, 0.0])
    assert 0.0 <= breach_prob <= 1.0
    
    # Delivery delay prediction
    # Features: [courier_id, dest_region_id, weather_severity, inventory_availability, historical_delay]
    delay_hours, delay_prob = ml_registry.predict_delivery_delay(db_session, 1, [1.0, 2.0, 0.0, 1.0, 2.4])
    assert delay_hours >= 0.0
    assert 0.0 <= delay_prob <= 1.0
