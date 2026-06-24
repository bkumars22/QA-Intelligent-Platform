"""RAG smoke tests — run with: pytest tests/test_rag.py -v

Requires DATABASE_URL set in env (or .env file).
Tests verify embedder, vector store, and retrieval work end-to-end.
"""

import os
import pytest
import uuid

# Skip all tests if DATABASE_URL not set
DB_AVAILABLE = bool(os.getenv("DATABASE_URL"))


def test_embed_single():
    """Embedding a single text produces a 384-dim float vector."""
    from rag.embedder import embed
    vec = embed("test text for QAIP RAG embedding")
    assert len(vec) == 384, f"Expected 384 dims, got {len(vec)}"
    assert all(isinstance(x, float) for x in vec)
    assert abs(sum(x**2 for x in vec) - 1.0) < 0.01, "Vector should be unit-normalised"
    print("✅ embed() → 384-dim normalised vector")


def test_embed_batch():
    """Batch embedding produces one vector per text."""
    from rag.embedder import embed_batch
    texts = ["first text", "second text", "third text"]
    vecs = embed_batch(texts)
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)
    print("✅ embed_batch() → 3 × 384-dim vectors")


@pytest.mark.skipif(not DB_AVAILABLE, reason="DATABASE_URL not set")
def test_schema_creation():
    """ensure_schema() creates rag_documents table without error."""
    from rag.vector_store import ensure_schema
    result = ensure_schema()
    assert result is True, "ensure_schema() returned False — check DATABASE_URL and pgvector extension"
    print("✅ pgvector schema created / verified")


@pytest.mark.skipif(not DB_AVAILABLE, reason="DATABASE_URL not set")
def test_upsert_and_search():
    """Store a document and retrieve it by semantic similarity."""
    from rag.embedder import embed
    from rag.vector_store import upsert, search, ensure_schema

    ensure_schema()
    project_id = str(uuid.uuid4())
    content = "This is a test case for login with null password returning HTTP 400"
    embedding = embed(content)

    doc_id = upsert(
        content=content,
        embedding=embedding,
        source_type="test_case",
        source_id=f"tc:{project_id}:auth/login.test.ts",
        project_id=project_id,
        metadata={"file_path": "auth/login.test.ts", "language": "typescript"},
    )
    assert doc_id is not None, "upsert() returned None"

    results = search(
        query_embedding=embed("login null password test"),
        project_id=project_id,
        top_k=3,
        min_similarity=0.1,
    )
    assert len(results) >= 1, "search() returned no results"
    assert any("login" in r["content"].lower() for r in results), "Expected login-related content in results"
    print(f"✅ upsert + search working — similarity: {results[0]['similarity']:.3f}")


@pytest.mark.skipif(not DB_AVAILABLE, reason="DATABASE_URL not set")
def test_ingest_test_case():
    """ingest_test_case stores a test and retrieve_for_file finds it."""
    from rag.ingest import ingest_test_case
    from rag.retriever import retrieve_for_file

    project_id = str(uuid.uuid4())
    test_code = """
    test('null password returns 400', async ({ request }) => {
        const response = await request.post('/api/auth/login',
            { data: { email: 'test@test.com', password: null } });
        expect(response.status()).toBe(400);
    });
    """
    ok = ingest_test_case(
        project_id=project_id,
        file_path="src/auth/login.test.ts",
        test_code=test_code,
        language="typescript",
    )
    assert ok, "ingest_test_case() returned False"

    hits = retrieve_for_file(project_id=project_id, file_path="src/auth/login.test.ts", top_k=3)
    assert len(hits) >= 1, "retrieve_for_file() returned no results"
    print(f"✅ QAIP ingest + retrieve working — {len(hits)} hit(s)")


@pytest.mark.skipif(not DB_AVAILABLE, reason="DATABASE_URL not set")
def test_ingest_defect():
    """ingest_defect stores a defect and retrieve_similar_defects finds it."""
    from rag.ingest import ingest_defect
    from rag.retriever import retrieve_similar_defects

    project_id = str(uuid.uuid4())
    ok = ingest_defect(
        project_id=project_id,
        title="Auth endpoint accepts null password without error",
        severity="P0",
        description="POST /api/auth/login with null password returns 200 instead of 400",
        file_path="src/auth/AuthController.java",
    )
    assert ok, "ingest_defect() returned False"

    hits = retrieve_similar_defects(
        project_id=project_id,
        defect_title="login endpoint accepts null credentials",
        top_k=3,
    )
    assert len(hits) >= 1, "retrieve_similar_defects() returned no results"
    print(f"✅ QAIP defect ingest + retrieve working — {len(hits)} hit(s)")


def test_format_few_shot_examples():
    """format_few_shot_examples returns a non-empty string for non-empty input."""
    from rag.retriever import format_few_shot_examples
    mock_results = [
        {"content": "File: auth/login.ts\nTest code:\ntest('null → 400', ...", "metadata": {"file_path": "auth/login.ts"}, "similarity": 0.85},
    ]
    formatted = format_few_shot_examples(mock_results)
    assert "SIMILAR TEST CASES" in formatted
    assert "auth/login.ts" in formatted
    assert "0.85" in formatted
    print("✅ format_few_shot_examples() produces correct output")
