import google.generativeai as genai

from app.core.config import settings

genai.configure(api_key=settings.effective_embedding_api_key)
try:
    result = genai.embed_content(
        model="models/gemini-embedding-001", content="test", task_type="retrieval_document"
    )
    print("Success without dimensions, dim:", len(result["embedding"]))
except Exception as e:
    print("Error without dimensions:", str(e))

try:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content="test",
        task_type="retrieval_document",
        output_dimensionality=3072,
    )
    print("Success with dimensions, dim:", len(result["embedding"]))
except Exception as e:
    print("Error with dimensions:", str(e))
