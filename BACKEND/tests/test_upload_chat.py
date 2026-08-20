import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

# Dummy test PDF file creation
@pytest.fixture(scope="module")
def dummy_pdf():
    filepath = "test_document.pdf"
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is a test legal document. It contains termination clauses.")
    doc.save(filepath)
    doc.close()
    yield filepath
    if os.path.exists(filepath):
        os.remove(filepath)

def mock_verify_token():
    from app.middleware.auth import VerifiedToken
    return VerifiedToken(uid="test_user_uid", email="test@nyaay.ai", name="Test User")

from app.middleware.auth import verify_firebase_token
app.dependency_overrides[verify_firebase_token] = mock_verify_token

def test_upload_document(dummy_pdf):
    # We must patch the auth middleware dependency correctly.
    # In app/routes/upload_chat.py: `user_token: dict = Depends(verify_firebase_token)`
    from app.middleware.auth import verify_firebase_token
    app.dependency_overrides[verify_firebase_token] = mock_verify_token
    
    with open(dummy_pdf, "rb") as f:
        response = client.post(
            "/api/upload-chat/upload",
            files={"file": ("test_document.pdf", f, "application/pdf")},
            headers={"Authorization": "Bearer dummy_token"}
        )
    
    assert response.status_code == 200, response.text
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "test_document.pdf"
    assert data["pages"] == 1
    assert "summary" in data
    
    return data["document_id"]

def test_query_document(dummy_pdf):
    # First upload
    from app.middleware.auth import verify_firebase_token
    app.dependency_overrides[verify_firebase_token] = mock_verify_token
    
    with open(dummy_pdf, "rb") as f:
        upload_resp = client.post(
            "/api/upload-chat/upload",
            files={"file": ("test_document.pdf", f, "application/pdf")},
            headers={"Authorization": "Bearer dummy_token"}
        )
    
    doc_id = upload_resp.json()["document_id"]
    
    # Now query
    query_payload = {
        "document_id": doc_id,
        "question": "What does the document say about termination?"
    }
    
    response = client.post(
        "/api/upload-chat/query",
        json=query_payload,
        headers={"Authorization": "Bearer dummy_token"}
    )
    
    assert response.status_code == 200, response.text
    data = response.json()
    assert "answer" in data
    assert "summary" in data
    assert "confidence" in data
