import chromadb

client = chromadb.PersistentClient(path=r"D:\Dev\QuantumLearningWorkspace\shared_chroma_data")
col = client.get_or_create_collection("study_chunks")

result = col.get(limit=50)
user_ids = set()
for metadata in result["metadatas"]:
    user_ids.add(metadata.get("user_id", "UNKNOWN"))

print("Users found in collection:")
for uid in user_ids:
    print(f"  - {uid}")