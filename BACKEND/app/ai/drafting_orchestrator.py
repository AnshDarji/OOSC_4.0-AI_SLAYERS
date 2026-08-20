import json
import logging
import os
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from app.core.config import settings
from app.knowledge.hybrid_retriever import hybrid_retriever
from app.knowledge.embeddings import embedding_service
from app.schemas.drafting import StructuredDocumentObject

logger = logging.getLogger(__name__)

class DraftingOrchestrator:
    def __init__(self):
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing in settings")
        self.client = genai.Client(api_key=api_key)
        self.templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")

    def _get_template_data(self, document_type: str) -> Dict[str, Any]:
        """Loads template schema and instructions from the registry."""
        folder = os.path.join(self.templates_dir, document_type.lower())
        if not os.path.exists(folder):
            return None
        
        schema = {}
        instructions = ""
        
        schema_path = os.path.join(folder, "schema.json")
        if os.path.exists(schema_path):
            with open(schema_path, "r") as f:
                schema = json.load(f)
                
        inst_path = os.path.join(folder, "instructions.md")
        if os.path.exists(inst_path):
            with open(inst_path, "r") as f:
                instructions = f.read()
                
        return {"schema": schema, "instructions": instructions}

    def classify_intent(self, user_facts: str, mandatory_fields: list = None) -> Dict[str, Any]:
        fields_hint = ""
        if mandatory_fields:
            fields_hint = f"\n\nFor the identified document type, these fields are MANDATORY:\n{json.dumps(mandatory_fields)}\nCarefully check if each mandatory field is clearly stated in the user's facts. If any are missing or ambiguous, list them in 'missing_essential_fields'."

        sys_prompt = f"""You are a Legal Drafting Intent Classifier.
Analyze the user's facts and determine the correct legal document type.
Supported types: AFFIDAVIT, POLICE_COMPLAINT, SP_COMPLAINT, LEGAL_NOTICE, CONSUMER_COMPLAINT, RTI_APPLICATION, REPRESENTATION, DECLARATION, INDEMNITY_BOND, POWER_OF_ATTORNEY.
Respond strictly in JSON format matching this schema:
{{
  "document_type": "string",
  "missing_essential_fields": ["string"],
  "alternatives": ["string"]
}}{fields_hint}"""
        
        import time
        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-lite-latest']
        max_retries = 3
        
        for attempt in range(max_retries):
            model_name = models_to_try[attempt % len(models_to_try)]
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=user_facts,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        response_mime_type="application/json"
                    )
                )
                return json.loads(response.text)
            except Exception as e:
                error_str = str(e)
                logger.warning(f"Intent classification with {model_name} failed: {error_str}")
                if attempt < max_retries - 1:
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str:
                        time.sleep(2 ** attempt * 2)
                    continue
                logger.error(f"Intent classification failed completely after {max_retries} attempts.")
                return {"document_type": "UNKNOWN", "missing_essential_fields": [], "alternatives": []}

    def _generate_with_retry(self, prompt: str, sys_prompt: str, retries: int = 2) -> StructuredDocumentObject:
        """Helper to generate content and parse it robustly with retries on malformed JSON and rate limits."""
        # Include Pydantic schema structure in the prompt to guide the LLM
        schema_str = StructuredDocumentObject.model_json_schema()
        sys_prompt += f"\n\nOUTPUT FORMAT:\nYou MUST return a single JSON object strictly adhering to this schema:\n{json.dumps(schema_str, indent=2)}\nDo NOT include markdown wrapping like ```json."
        
        import time
        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-lite-latest']
        
        for attempt in range(retries + 1):
            model_name = models_to_try[attempt % len(models_to_try)]
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                
                raw_json = response.text.strip()
                if raw_json.startswith("```json"):
                    raw_json = raw_json[7:-3].strip()
                elif raw_json.startswith("```"):
                    raw_json = raw_json[3:-3].strip()
                    
                # Validate and parse
                doc_obj = StructuredDocumentObject.model_validate_json(raw_json)
                return doc_obj
            except Exception as e:
                error_str = str(e)
                logger.warning(f"Generation attempt {attempt + 1} with {model_name} failed: {error_str}")
                if attempt < retries:
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str:
                        time.sleep(2 ** attempt * 2)
                    continue
                raise ValueError(f"Failed to generate structured document after {retries + 1} attempts. Error: {error_str}")

    def generate_document_object(self, user_facts: str, document_type: str, context_chunks: List[Dict[str, Any]]) -> StructuredDocumentObject:
        template_data = self._get_template_data(document_type)
        if not template_data:
            raise ValueError(f"Template for {document_type} not found in registry.")

        context_str = "RELEVANT LEGAL PROVISIONS:\n"
        for chunk in context_chunks:
            context_str += f"- {chunk.get('document', '')[:300]}...\n"

        sys_prompt = f"""You are a master Legal Draftsman in India.
Your task is to draft a highly professional, filing-ready {document_type} based strictly on the user's facts and the provided legal context.
Do NOT invent missing facts. Use placeholders like [District] or [Name] if something is missing but required.

DRAFTING INSTRUCTIONS:
{template_data['instructions']}
"""
        prompt = f"User Facts:\n{user_facts}\n\n{context_str}"
        return self._generate_with_retry(prompt, sys_prompt)

    def edit_document_object(self, doc_obj_data: Dict[str, Any], edit_instructions: str) -> StructuredDocumentObject:
        """Edits an existing StructuredDocumentObject using LLM."""
        sys_prompt = """You are a Legal Editor. You will receive an existing structured document object (JSON) and an edit instruction.
Apply the edit instruction carefully to the appropriate fields of the document (usually the 'body' array).
Keep the rest of the document identical.
Increment the 'metadata.version' by 1.
"""
        prompt = f"Existing Document JSON:\n{json.dumps(doc_obj_data, indent=2)}\n\nEdit Instruction:\n{edit_instructions}"
        return self._generate_with_retry(prompt, sys_prompt)

    def trigger_drafting_pipeline(self, user_facts: str, provided_fields: Dict[str, str] = None) -> Dict[str, Any]:
        # Pass 1: Identify the document type only
        intent_res = self.classify_intent(user_facts)
        doc_type = intent_res.get("document_type", "UNKNOWN")

        if doc_type == "UNKNOWN" or not self._get_template_data(doc_type):
            return {
                "status": "ERROR",
                "message": "We could not determine a supported legal document type for your request. Please try providing more details or request one of the supported types (e.g., Affidavit, Police Complaint, Legal Notice)."
            }

        template_data = self._get_template_data(doc_type)
        schema_mandatory = template_data["schema"].get("mandatory_fields", [])

        # If the user already provided fields from a previous form submission, inject them
        if provided_fields:
            user_facts += "\n\nAdditional Details:\n" + "\n".join([f"{k}: {v}" for k, v in provided_fields.items()])
            missing = []
        else:
            # Pass 2: Re-classify with mandatory field knowledge so LLM can accurately detect gaps
            intent_res2 = self.classify_intent(user_facts, mandatory_fields=schema_mandatory)
            missing = intent_res2.get("missing_essential_fields", [])

        if missing:
            return {
                "status": "MISSING_INFO",
                "document_type": doc_type,
                "missing_fields": missing,
                "alternatives": intent_res.get("alternatives", [])
            }

        search_query = f"Elements and procedures for drafting a {doc_type}. Facts: {user_facts}"
        query_embedding = embedding_service.embed_query(search_query)
        chunks = hybrid_retriever.search(search_query, query_embedding, n_results=3)

        doc_obj = self.generate_document_object(user_facts, doc_type, chunks)

        return {
            "status": "SUCCESS",
            "document_object": doc_obj.model_dump()
        }

drafting_orchestrator = DraftingOrchestrator()
