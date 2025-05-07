import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import uuid

load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Create index if it doesn't exist
index_name = "sextbot-v2"
embedding_dim = 384  # for MiniLM

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=embedding_dim,
        metric="cosine"
    )

index = pc.Index(index_name)

# Embedding model
embed_model = SentenceTransformer('all-MiniLM-L6-v2')


def store_message(session_id, user_message, bot_reply):
    conversation = f"User: {user_message}\nBot: {bot_reply}"
    embedding = embed_model.encode(conversation).tolist()

    index.upsert([
        {
            "id": str(uuid.uuid4()),
            "values": embedding,
            "metadata": {
                "session_id": session_id,
                "user": user_message,
                "bot": bot_reply
            }
        }
    ])


def get_chat_history(session_id, k=10):
    query_vector = embed_model.encode("chat history").tolist()

    result = index.query(
        vector=query_vector,
        filter={"session_id": {"$eq": session_id}},
        top_k=k,
        include_metadata=True
    )

    chat_history = []
    for match in result["matches"]:
        metadata = match["metadata"]
        chat_history.append({
            "user": metadata["user"],
            "bot": metadata["bot"]
        })

    return chat_history
