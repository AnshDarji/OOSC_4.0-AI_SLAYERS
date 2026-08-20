import re
import json
import logging
from typing import Dict, Any, Tuple
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

class DomainClassifier:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

        # Rule-based dictionary for fast path
        # Keys are domains, values are lists of regex patterns
        self.rules = {
            "Real Estate": [r"\brera\b", r"\bbuilder\b", r"\bpossession\b", r"\bapartment\b", r"\bflat\b", r"\bdeveloper\b"],
            "Consumer Law": [r"\bconsumer\b", r"\bdeficiency\b", r"\bunfair trade\b", r"\bproduct liability\b"],
            "Criminal Law": [r"\bfir\b", r"\bpolice\b", r"\barrest\b", r"\bbail\b", r"\bmurder\b", r"\btheft\b", r"\bbns\b", r"\bbnss\b"],
            "Constitutional Law": [r"\bwrit\b", r"\bfundamental right\b", r"\bconstitution\b", r"\barticle 32\b", r"\barticle 226\b"],
            "Family Law": [r"\bdivorce\b", r"\bmaintenance\b", r"\bchild custody\b", r"\bhindu marriage act\b", r"\balimony\b"],
            "Corporate Law": [r"\bcompany\b", r"\bshareholder\b", r"\bdirector\b", r"\bincorporation\b", r"\bboard meeting\b"],
            "Tax Law": [r"\bincometax\b", r"\bgst\b", r"\btax evasion\b", r"\btds\b"],
            "Contract Law": [r"\bbreach of contract\b", r"\bagreement\b", r"\bindemnity\b", r"\bspecific performance\b"]
        }
        
        # Heuristics for unsupported jurisdictions
        self.unsupported_jurisdictions = [
            r"\bus constitution\b", r"\bsecond amendment\b", r"\bfirst amendment\b",
            r"\buk law\b", r"\beuropean union\b", r"\bgdpr\b"
        ]
        
        # Heuristics for non-legal queries
        self.non_legal_queries = [
            r"\bjoke\b", r"\brecipe\b", r"\bweather\b", r"\bignore all previous\b"
        ]

    def _rule_based_classification(self, query: str) -> str:
        query_lower = query.lower()
        
        # 1. Check for non-legal or unsupported jurisdictions
        for pattern in self.unsupported_jurisdictions + self.non_legal_queries:
            if re.search(pattern, query_lower):
                return "UNSUPPORTED"
                
        # 2. Check for domain keywords
        domain_scores = {domain: 0 for domain in self.rules.keys()}
        for domain, patterns in self.rules.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    domain_scores[domain] += 1
                    
        # Find the max score
        max_score = 0
        best_domain = "UNKNOWN"
        for domain, score in domain_scores.items():
            if score > max_score:
                max_score = score
                best_domain = domain
                
        # If we have a strong match (at least 2 keywords, or 1 very strong one), use it.
        # For simplicity, if max_score > 0, we'll tentatively use it, but LLM is better for ambiguity.
        if max_score >= 1:
            return best_domain
            
        return "UNKNOWN"

    def predict_domain(self, query: str) -> Dict[str, Any]:
        """
        Predicts the legal domains and document type priorities of the query.
        Returns a dictionary:
        {
            "domains": {"Criminal Law": 0.9, "Cyber Law": 0.5},
            "document_type_priority": "statute" | "judgment" | "any",
            "is_supported": bool
        }
        """
        default_response = {
            "domains": {},
            "document_type_priority": "any",
            "is_supported": True
        }
        
        query_lower = query.lower()
        
        # 1. Check for non-legal or unsupported jurisdictions
        for pattern in self.unsupported_jurisdictions + self.non_legal_queries:
            if re.search(pattern, query_lower):
                default_response["is_supported"] = False
                return default_response

        # A deterministic match is both faster and more reliable than a
        # second model call. It also keeps the retrieval path available when
        # the external classifier service is unavailable.
        rule_domain = self._rule_based_classification(query)
        if rule_domain != "UNKNOWN":
            return {
                "domains": {rule_domain: 0.9},
                "document_type_priority": "statute" if re.search(r"\b(section|sections|act|code|rule|rules|punishment)\b", query_lower) else "any",
                "is_supported": True,
            }
                
        if not self.client:
            return default_response
            
        sys_prompt = """You are a Legal Domain Classifier for NYAAY AI, an Indian legal platform.
Determine the primary and secondary legal domains of the user's query, and the preferred document type.
If the query is asking about non-Indian law (e.g., US Constitution, UK Law) or is completely non-legal, set "is_supported" to false.

Available Domains: Constitutional Law, Education, Civil & Procedural Law, Criminal Law, Banking & Finance, General Law, Environmental Law, Consumer Law, Tax Law, Family Law, Labour & Employment, Contract Law, Intellectual Property, Tenant & Rent, Property Law, Healthcare, Agriculture, Cyber Data & Technology, Test Law.

Output MUST be a valid JSON object matching this schema:
{
    "domains": {"Domain Name": confidence_score_between_0_and_1},
    "document_type_priority": "statute" | "judgment" | "any",
    "is_supported": true | false
}

Rules:
- For 'document_type_priority': if the user asks about rules/sections, use "statute". If they ask about precedents/Supreme Court/interpretation, use "judgment". Otherwise "any".
- Include up to 3 relevant domains in the 'domains' dict with their respective confidence scores (0.1 to 1.0).
"""
        try:
            res = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Query: {query}",
                config=types.GenerateContentConfig(
                    system_instruction=sys_prompt,
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            prediction = json.loads(res.text)
            logger.info(f"Domain prediction: {prediction}")
            return prediction
        except Exception as e:
            logger.warning(f"LLM Domain Classification failed: {e}")
            return default_response

domain_classifier = DomainClassifier()
