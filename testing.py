import chromadb

client = chromadb.PersistentClient(path="data/chroma_db")
collection = client.get_or_create_collection(name="company_docs")

# Search directly in DB for RTO
results = collection.get(where_document={"$contains": "Recovery Time Objective"})
print(f"Total matching chunks in DB: {len(results['documents'])}")

if results['documents']:
    print("\n--- SAMPLE MATCHING CHUNK ---")
    print("Metadata:", results['metadatas'][0])
    print("Content preview:\n", results['documents'][0][:200])
else:
    print("RTO text DB mein nahi mila! Check raw files.")