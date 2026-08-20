from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.ai.drafting_orchestrator import drafting_orchestrator
from app.schemas.drafting import StructuredDocumentObject
from app.utils.document_generators import DocumentGenerator
from app.middleware.auth import VerifiedToken, verify_firebase_token
from app.core.rate_limit import limiter

router = APIRouter()

class DraftRequest(BaseModel):
    user_facts: str
    provided_fields: Optional[Dict[str, str]] = None

class EditRequest(BaseModel):
    document_object: StructuredDocumentObject
    edit_instructions: str

@router.post("/generate")
@limiter.limit("10/minute")
def generate_draft(request: Request, payload: DraftRequest, _: VerifiedToken = Depends(verify_firebase_token)):
    try:
        response = drafting_orchestrator.trigger_drafting_pipeline(payload.user_facts, payload.provided_fields)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/edit", response_model=StructuredDocumentObject)
@limiter.limit("20/minute")
def edit_draft(request: Request, payload: EditRequest, _: VerifiedToken = Depends(verify_firebase_token)):
    try:
        updated_doc = drafting_orchestrator.edit_document_object(
            payload.document_object.model_dump(),
            payload.edit_instructions
        )
        # Manually increment version (or rely on LLM to do it, but let's enforce it)
        updated_doc.metadata.version = payload.document_object.metadata.version + 1
        return updated_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download/pdf")
@limiter.limit("30/minute")
def download_pdf(request: Request, doc_obj: StructuredDocumentObject, _: VerifiedToken = Depends(verify_firebase_token)):
    try:
        buffer = DocumentGenerator.generate_pdf(doc_obj)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={doc_obj.document_type.lower()}_draft.pdf"}
        )
    except Exception as e:
        import traceback
        import logging
        logging.getLogger(__name__).error(f"PDF Export Failed:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail={"error": "Failed to generate PDF", "reason": str(e)})

@router.post("/download/docx")
@limiter.limit("30/minute")
def download_docx(request: Request, doc_obj: StructuredDocumentObject, _: VerifiedToken = Depends(verify_firebase_token)):
    try:
        buffer = DocumentGenerator.generate_docx(doc_obj)
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={doc_obj.document_type.lower()}_draft.docx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
