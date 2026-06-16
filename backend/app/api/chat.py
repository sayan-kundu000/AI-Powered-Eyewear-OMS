import torch
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas import ChatQuery, ChatResponse
from app.api.auth import get_current_user, RoleChecker
from app.ai.transformer import model as transformer_model, tokenize_query

router = APIRouter(prefix="/chat", tags=["AI Chat Assistant"])

role_staff_or_admin = RoleChecker(["STORE_STAFF", "LAB_TECH"])

INTENT_LABELS = {
    0: "query_orders",
    1: "explain_delay",
    2: "show_analytics",
    3: "greeting"
}

@router.post("", response_model=ChatResponse, dependencies=[Depends(role_staff_or_admin)])
def ask_internal_ai_assistant(query_in: ChatQuery, db: Session = Depends(get_db)):
    msg = query_in.message.lower().strip()
    
    # 1. Classify Query Intent using the custom Transformer
    with torch.no_grad():
        tokens = tokenize_query(msg)
        intent_logits = transformer_model.forward_intent(tokens)
        intent_id = torch.argmax(intent_logits, dim=1).item()
        intent = INTENT_LABELS.get(intent_id, "query_orders")

    # Simple heuristic fallback if keywords are obvious
    if "hello" in msg or "hi " in msg or "hey " in msg:
        intent = "greeting"
    elif "chart" in msg or "analytics" in msg or "trend" in msg:
        intent = "show_analytics"
    elif "why" in msg or "explain" in msg or "reason" in msg:
        intent = "explain_delay"

    # 2. Handle Intents
    if intent == "greeting":
        return ChatResponse(
            response="Hello! I am your internal Eyewear OMS Assistant. How can I help you query orders, analyze delays, or audit inventory today?",
            sql_query="-- None --",
            results=[]
        )
        
    elif intent == "show_analytics":
        return ChatResponse(
            response="To view system analytics and store performance trends, please navigate to the Analytics Dashboard tab.",
            sql_query="-- None --",
            results=[]
        )
        
    elif intent == "explain_delay":
        # Explain why an order is delayed (Auto Root Cause Analysis)
        # Look for order numbers
        order_match = None
        import re
        m = re.search(r"ord-\d+-\d+|ord-\S+", msg)
        if m:
            order_match = m.group(0).upper()
            
        if order_match:
            sql = "SELECT id, order_number, current_status, remaining_tat_hours, risk_score FROM orders WHERE UPPER(order_number) = :order_no"
            params = {"order_no": order_match}
            res = db.execute(text(sql), params).mappings().all()
            if res:
                order_item = res[0]
                status_val = order_item["current_status"]
                tat = order_item["remaining_tat_hours"]
                
                # Check for QC Failures
                qc_sql = "SELECT COUNT(*) as count FROM qc_logs WHERE order_id = :order_id AND recommendation = 'FAIL'"
                qc_res = db.execute(text(qc_sql), {"order_id": order_item["id"]}).mappings().all()
                qc_fails = qc_res[0]["count"] if qc_res else 0
                
                explanation = f"Order {order_match} is currently in state '{status_val}'. "
                if status_val == "QC_FAILED" or qc_fails > 0:
                    explanation += f"It has failed visual quality checks {qc_fails} times in the lab, triggering automated rework. "
                if tat < 0:
                    explanation += f"The remaining SLA timer has expired by {-tat:.1f} hours due to production queue congestion."
                else:
                    explanation += f"It has {tat:.1f} hours remaining of its SLA window. Current risk level is: {order_item['risk_score']}."
                    
                return ChatResponse(response=explanation, sql_query=sql, results=[dict(r) for r in res])
                
        return ChatResponse(
            response="I can analyze order delays. Please include the specific order number in your question (e.g. 'Explain why order ORD-20260614-1234 is delayed').",
            sql_query="-- None --",
            results=[]
        )
        
    else: # query_orders
        # Natural Language Parsing to SQL parameters (SQL generation layer)
        base_query = (
            "SELECT o.id, o.order_number, o.lens_type, o.current_status, s.name as store, c.first_name || ' ' || c.last_name as customer "
            "FROM orders o "
            "JOIN stores s ON o.store_id = s.id "
            "JOIN customers c ON o.customer_id = c.id "
            "WHERE 1=1"
        )
        params = {}
        
        # Check Lens Type filter
        if "progressive" in msg:
            base_query += " AND LOWER(o.lens_type) LIKE :lens"
            params["lens"] = "%progressive%"
        elif "single vision" in msg or "single" in msg:
            base_query += " AND LOWER(o.lens_type) LIKE :lens"
            params["lens"] = "%single vision%"
            
        # Check Location filter
        locations = ["mumbai", "delhi", "bangalore", "pune", "chennai", "kolkata"]
        for loc in locations:
            if loc in msg:
                base_query += " AND LOWER(s.location) LIKE :loc"
                params["loc"] = f"%{loc}%"
                break
                
        # Check status modifiers
        if "delay" in msg or "breach" in msg or "risk" in msg:
            base_query += " AND (o.remaining_tat_hours < 0 OR o.risk_score = 'High')"
        elif "failed" in msg or "qc" in msg:
            base_query += " AND o.current_status = 'QC_FAILED'"
            
        # Add order-by limit
        base_query += " ORDER BY o.created_at DESC LIMIT 5"
        
        try:
            results = db.execute(text(base_query), params).mappings().all()
            formatted_results = [dict(r) for r in results]
            
            response_text = f"I found {len(formatted_results)} matching orders. Here is the query result:"
            if not formatted_results:
                response_text = "I couldn't find any orders matching those criteria."
                
            return ChatResponse(
                response=response_text,
                sql_query=base_query,
                results=formatted_results
            )
        except Exception as e:
            logger.error(f"SQL execution error in Chat Assistant: {e}")
            raise HTTPException(status_code=500, detail="Error generating query results.")
