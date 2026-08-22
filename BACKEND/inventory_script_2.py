from app.knowledge.vector_store import vector_store

try:
    sc_collection = vector_store.sc_collection
    print("Total SC dense vectors:", sc_collection.count())
    
    docs = sc_collection.get(limit=10, include=['metadatas'])
    metadatas = docs.get('metadatas', [])
    print("SC metadatas sample:", metadatas)
except Exception as e:
    print("Error inspecting SC dense:", e)
