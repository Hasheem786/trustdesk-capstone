import pytest

def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

def test_api_list_customers(client):
    res = client.get("/api/customers")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1

def test_api_list_kb(client):
    res = client.get("/api/kb")
    assert res.status_code == 200
    data = res.json()
    assert any(d["doc_id"] == "KB-REFUND-001" for d in data)

def test_api_create_and_process_ticket(client):
    # 1. Create ticket
    payload = {
        "customer_id": "CUST-001",
        "order_id": "ORD-1001",
        "subject": "Return wireless headphones",
        "description": "The headphones don't fit. Requesting refund.",
    }
    create_res = client.post("/api/tickets", json=payload)
    assert create_res.status_code == 200
    ticket = create_res.json()
    ticket_id = ticket["id"]

    # 2. Process ticket
    proc_res = client.post(f"/api/tickets/{ticket_id}/process")
    assert proc_res.status_code == 200
    proc_data = proc_res.json()
    assert proc_data["triage"]["category"] == "refund"
    assert "KB-REFUND-001" in proc_data["draft"]["cited_doc_ids"]

    # 3. Check ticket detail
    detail_res = client.get(f"/api/tickets/{ticket_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert len(detail_data["actions"]) > 0

    # 4. Approve action
    action_id = detail_data["actions"][0]["id"]
    approve_res = client.post(f"/api/actions/{action_id}/approve")
    assert approve_res.status_code == 200
    assert approve_res.json()["action"]["status"] == "EXECUTED"
