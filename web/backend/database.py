import os
from typing import Optional, Dict, Any, List, Union
import logging
import certifi
from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("uvicorn")
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "study_mind_db")

client: Optional[AsyncIOMotorClient] = None


class InMemoryCursor:
    """Mock async cursor for in-memory documents supporting async iteration, sorting, limit, and skip."""
    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = list(docs)
        self._iter = None

    def __aiter__(self):
        self._iter = iter(self.docs)
        return self

    async def __anext__(self):
        if self._iter is None:
            self._iter = iter(self.docs)
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    def sort(self, key_or_list: Union[str, List[tuple]], direction: int = 1):
        if isinstance(key_or_list, str):
            key = key_or_list
            reverse = (direction == -1)
            self.docs.sort(key=lambda d: str(d.get(key, "")), reverse=reverse)
        elif isinstance(key_or_list, list):
            for item in reversed(key_or_list):
                if isinstance(item, tuple) and len(item) == 2:
                    k, dirn = item
                    self.docs.sort(key=lambda d: str(d.get(k, "")), reverse=(dirn == -1))
        return self

    def skip(self, count: int):
        self.docs = self.docs[count:]
        return self

    def limit(self, count: int):
        self.docs = self.docs[:count]
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        if length is None:
            return [dict(d) for d in self.docs]
        return [dict(d) for d in self.docs[:length]]


def _match_doc(doc: Dict[str, Any], query: Optional[Dict[str, Any]]) -> bool:
    if not query:
        return True
    for k, v in query.items():
        if k == "_id":
            doc_id = doc.get("_id")
            if isinstance(v, ObjectId) or isinstance(doc_id, ObjectId):
                if str(doc_id) != str(v):
                    return False
            elif doc_id != v:
                return False
        elif "." in k:
            parts = k.split(".", 1)
            parent = doc.get(parts[0])
            if isinstance(parent, list):
                # Check if any item in the list matches
                child_key = parts[1]
                found = False
                for item in parent:
                    if isinstance(item, dict):
                        item_val = item.get(child_key)
                        if isinstance(v, dict) and "$in" in v:
                            if item_val in v["$in"]:
                                found = True
                                break
                        elif item_val == v:
                            found = True
                            break
                if not found:
                    return False
            elif isinstance(parent, dict):
                child_val = parent.get(parts[1])
                if isinstance(v, dict) and "$in" in v:
                    if child_val not in v["$in"]:
                        return False
                elif child_val != v:
                    return False
            else:
                return False
        elif isinstance(v, dict) and "$in" in v:
            doc_val = doc.get(k)
            if doc_val not in v["$in"]:
                return False
        elif doc.get(k) != v:
            return False
    return True


class InMemoryCollection:
    """In-memory collection fallback when MongoDB URI is absent or connection is unavailable."""
    def __init__(self, name: str):
        self.name = name
        self.documents: List[Dict[str, Any]] = []

    async def find_one(self, query: Optional[Dict[str, Any]] = None):
        for doc in self.documents:
            if _match_doc(doc, query):
                return dict(doc)
        return None

    async def insert_one(self, document: Dict[str, Any]):
        doc = dict(document)
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.documents.append(doc)
        return type("InsertResult", (), {"inserted_id": doc["_id"]})()

    async def insert_many(self, documents: List[Dict[str, Any]]):
        inserted_ids = []
        for document in documents:
            doc = dict(document)
            if "_id" not in doc:
                doc["_id"] = ObjectId()
            self.documents.append(doc)
            inserted_ids.append(doc["_id"])
        return type("InsertManyResult", (), {"inserted_ids": inserted_ids})()

    def find(self, query: Optional[Dict[str, Any]] = None):
        results = [dict(doc) for doc in self.documents if _match_doc(doc, query)]
        return InMemoryCursor(results)

    async def delete_one(self, query: Dict[str, Any]):
        for i, doc in enumerate(self.documents):
            if _match_doc(doc, query):
                self.documents.pop(i)
                return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()

    async def delete_many(self, query: Optional[Dict[str, Any]] = None):
        if not query:
            count = len(self.documents)
            self.documents.clear()
            return type("DeleteResult", (), {"deleted_count": count})()
        
        initial_count = len(self.documents)
        self.documents = [doc for doc in self.documents if not _match_doc(doc, query)]
        deleted_count = initial_count - len(self.documents)
        return type("DeleteResult", (), {"deleted_count": deleted_count})()

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        set_fields = update.get("$set", {})
        matched_count = 0
        modified_count = 0
        for doc in self.documents:
            if _match_doc(doc, query):
                matched_count += 1
                for field, val in set_fields.items():
                    if doc.get(field) != val:
                        doc[field] = val
                        modified_count += 1
                break
        return type("UpdateResult", (), {"matched_count": matched_count, "modified_count": modified_count})()

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]):
        set_fields = update.get("$set", {})
        matched_count = 0
        modified_count = 0
        for doc in self.documents:
            if _match_doc(doc, query):
                matched_count += 1
                for field, val in set_fields.items():
                    if doc.get(field) != val:
                        doc[field] = val
                        modified_count += 1
        return type("UpdateResult", (), {"matched_count": matched_count, "modified_count": modified_count})()

    async def count_documents(self, query: Optional[Dict[str, Any]] = None):
        return sum(1 for doc in self.documents if _match_doc(doc, query))


class InMemoryDatabase:
    """Mock database container mapping collection names to InMemoryCollection."""
    def __init__(self):
        self._collections: Dict[str, InMemoryCollection] = {}

    def __getitem__(self, name: str) -> InMemoryCollection:
        if name not in self._collections:
            self._collections[name] = InMemoryCollection(name)
        return self._collections[name]

    def __getattr__(self, name: str) -> InMemoryCollection:
        return self[name]

    def get_collection(self, name: str) -> InMemoryCollection:
        return self[name]


_in_memory_db = InMemoryDatabase()


def is_placeholder_uri(uri: str) -> bool:
    """Check if MongoDB URI is empty, placeholder, or standard dev default without active mongo."""
    return (
        not uri
        or "<username>" in uri
        or "<password>" in uri
        or "<cluster-url>" in uri
        or (uri == "mongodb://localhost:27017" and os.getenv("USE_LOCAL_MONGO") != "1")
    )



def get_client() -> Optional[AsyncIOMotorClient]:
    """Create and cache the MongoDB client instance if configured."""
    global client
    if is_placeholder_uri(MONGODB_URI):
        return None

    if client is None:
        client_kwargs: Dict[str, Any] = {
            "serverSelectionTimeoutMS": 5000,
        }
        # Only attach TLS/SSL certificate authority for cloud/TLS connections
        uri_lower = MONGODB_URI.lower()
        if "mongodb+srv://" in uri_lower or "ssl=true" in uri_lower or "tls=true" in uri_lower:
            client_kwargs["tlsCAFile"] = certifi.where()

        client = AsyncIOMotorClient(
            MONGODB_URI,
            **client_kwargs,
        )
    return client


def get_database():
    """Return the configured database object or in-memory fallback."""
    c = get_client()
    if c is None:
        return _in_memory_db
    return c[MONGODB_DB_NAME]


def get_uploads_collection():
    """Return the uploads collection used by the app."""
    return get_database()["uploads"]


def get_chat_history_collection():
    """Return the chat history collection used by the app."""
    return get_database()["chat_history"]


def get_users_collection():
    """Return the users collection used by the app."""
    return get_database()["users"]


def get_quiz_results_collection():
    """Return the quiz results collection used by the app."""
    return get_database()["quiz_results"]


def get_quiz_sessions_collection():
    """Return the quiz sessions collection used for server-side grading."""
    return get_database()["quiz_sessions"]


def get_flashcard_reviews_collection():
    """Return the flashcard_reviews collection for tracking user reviews."""
    return get_database()["flashcard_reviews"]


def get_flashcards_collection():
    """Return the flashcards collection for saved/generated flashcards."""
    return get_database()["flashcards"]
