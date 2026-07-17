import os
from dotenv import load_dotenv
from groq import Groq
import chromadb
from sentence_transformers import SentenceTransformer

load_dotenv()

documents = [
    "The Great Barrier Reef is the world's largest coral reef system, located off the coast of Australia. It is home to thousands of species of marine life.",
    "Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen. It occurs mainly in the leaves.",
    "The French Revolution began in 1789 and led to the end of monarchy in France. It was driven by financial crisis and demands for equality.",
    "Neural networks are computing systems inspired by the human brain. They consist of layers of interconnected nodes that learn patterns from data.",
    "The water cycle describes how water moves through the atmosphere, land, and oceans through processes like evaporation, condensation, and precipitation."
]

print("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="study_snippets")

print("Creating embeddings and storing in ChromaDB...")
for i, doc in enumerate(documents):
    embedding = embedding_model.encode(doc).tolist()
    collection.add(
        ids=[f"doc_{i}"],
        embeddings=[embedding],
        documents=[doc]
    )

user_question = "How do plants make their food?"
question_embedding = embedding_model.encode(user_question).tolist()

results = collection.query(
    query_embeddings=[question_embedding],
    n_results=1
)

retrieved_snippet = results["documents"][0][0]
print(f"\nRetrieved snippet: {retrieved_snippet}\n")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "system",
            "content": "Answer the user's question using ONLY the provided reference snippet. If the snippet doesn't contain the answer, say so."
        },
        {
            "role": "user",
            "content": f"Reference snippet:\n{retrieved_snippet}\n\nQuestion: {user_question}"
        }
    ],
    temperature=0.3,
)

print("LLM Final Answer:\n")
print(response.choices[0].message.content)