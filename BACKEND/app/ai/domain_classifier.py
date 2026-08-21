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
            "Consumer Law": [r"\bconsumer\b", r"\bdefective\b", r"\becommerce\b", r"\be-commerce\b", r"\brefund\b", r"\bwarranty\b", r"\bseller\b", r"\bonline shopping\b", r"\bunfair trade\b", r"\bccpa\b", r"\bncdrc\b", r"\bdistrict forum\b"],
            "RTI & Transparency": [r"\brti\b", r"\bright to information\b", r"\bpio\b", r"\bpublic information officer\b", r"\bfirst appeal\b", r"\bsecond appeal\b", r"\bcic\b", r"\bsic\b"],
            "Tenant & Rent Law": [r"\btenant\b", r"\blandlord\b", r"\brent\b", r"\blease\b", r"\beviction\b", r"\bsecurity deposit\b", r"\brent agreement\b", r"\bmodel tenancy\b", r"\bpagdi\b", r"\brent control\b"],
            "Labour & Employment": [r"\bemployer\b", r"\bemployee\b", r"\bsalary\b", r"\bwages\b", r"\bovertime\b", r"\bpf\b", r"\bprovident fund\b", r"\bgratuity\b", r"\bharassment at workplace\b", r"\bposh\b", r"\btermination\b", r"\bnotice period\b"],
            "Criminal Law": [r"\bpolice\b", r"\bfir\b", r"\bbail\b", r"\barrest\b", r"\btheft\b", r"\bmurder\b", r"\bassault\b", r"\bbns\b", r"\bbnss\b", r"\bbsa\b", r"\bipc\b", r"\bcrpc\b"],
            "Constitutional Law": [r"\bfundamental rights\b", r"\bwrit\b", r"\bhigh court\b", r"\bsupreme court\b", r"\bconstitution\b"],
            "Family Law": [r"\bdivorce\b", r"\bmarriage\b", r"\bmaintenance\b", r"\bchild custody\b", r"\balimony\b", r"\bhindu marriage act\b", r"\bspecial marriage act\b"],
            "Corporate Law": [r"\bcompany\b", r"\bdirector\b", r"\bshareholder\b", r"\bincorporation\b", r"\bmca\b"],
            "Tax Law": [r"\bincome tax\b", r"\bgst\b", r"\btds\b", r"\bassessment\b"],
            "Contract Law": [r"\bcontract\b", r"\bbreach\b", r"\bagreement\b", r"\bspecific performance\b"],
            "Property Law": [r"\bproperty\b", r"\bsale deed\b", r"\bregistration\b", r"\bmutation\b", r"\bencumbrance\b", r"\btransfer of property\b"]
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
                
        # If unknown, just return default immediately - save 2s latency and LLM rate limit
        return default_response

domain_classifier = DomainClassifier()
