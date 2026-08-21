import asyncio
import os
import sys
from app.knowledge.hybrid_retriever import HybridRetriever

async def main():
    retriever = HybridRetriever()
    results = await retriever.search('can my landlord evict me')
    for r in results:
        print(f"Score: {r['combined_score']:.4f} | Source: {r['metadata'].get('source')} | Text: {r['text'][:100]}")

if __name__ == '__main__':
    asyncio.run(main())
