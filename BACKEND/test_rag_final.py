from app.ai.orchestrator import RAGOrchestrator

rag = RAGOrchestrator()
response = rag.trigger_pipeline('can my landlord evict me', history=[])
with open('output.txt', 'w', encoding='utf-8') as f:
    f.write(response['answer'])
