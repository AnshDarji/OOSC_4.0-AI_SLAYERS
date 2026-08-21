import asyncio
from app.ai.orchestrator import RAGOrchestrator

rag = RAGOrchestrator()
response = rag.trigger_pipeline('can my landlord evict me', history=[])
with open('output.json', 'w', encoding='utf-8') as f:
    f.write(response.model_dump_json(indent=2))
