from pinecone import ServerlessSpec

def init_index(pc):
    if "sextbot-index" not in pc.list_indexes().names():
        pc.create_index(
            name="sextbot-index",
            dimension=1536,  # Adjust if your embedding size is different
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-west-2")
        )
    return pc.Index("sextbot-index")
