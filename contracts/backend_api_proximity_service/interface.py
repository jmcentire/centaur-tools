# === Proximity Service (backend_api_proximity_service) v1 ===
#  Dependencies: uuid, sqlalchemy, sqlalchemy.ext.asyncio, backend.api.config, backend.api.database, backend.api.models, backend.api.search.router
# Generates embeddings for tool problem statements, finds semantically similar tools via vector cosine similarity, creates bidirectional proximity links, and notifies authors of newly discovered tool neighbors.

# Module invariants:
#   - ProximityLink records maintain canonical ordering: tool_a_id < tool_b_id
#   - Similarity scores are rounded to 3 decimal places in output and notification data
#   - Proximity links are only created for similarity >= settings.proximity_threshold
#   - Maximum of 20 nearest neighbors considered per scan
#   - Notifications are not created for self-authored tool matches (nt.author_id != tool.author_id)
#   - Function uses isolated database session independent of caller's session
#   - tool_id in output is serialized as string via str(neighbor_tool_id)

async def scan_proximity(
    tool: Tool,
    _db: AsyncSession,
) -> list[dict]:
    """
    Generate embedding for tool's problem statement and find neighbors. Uses its own DB session to avoid closed-connection issues. Returns list of similar tools above proximity threshold with similarity scores.

    Preconditions:
      - tool.problem_statement must be a non-empty string
      - tool.id must be a valid UUID
      - settings.proximity_threshold must be defined
      - Database connection must be available via async_session()

    Postconditions:
      - ToolEmbedding record exists for tool.id with current embedding
      - ProximityLink records created for all neighbors above threshold (canonical ordering: tool_a_id < tool_b_id)
      - Notification records created for neighbor authors (excluding self-authored tools)
      - Returns empty list if embedding generation fails
      - Returns list of dicts with 'tool_id' (str) and 'similarity' (float, rounded to 3 decimals) for neighbors above threshold
      - Maximum 20 neighbors considered (LIMIT 20)
      - All database changes committed before return

    Errors:
      - EmbeddingFailure (SilentFailure): get_embedding returns None or empty value
          behavior: Returns empty list []
      - DatabaseConnectionFailure (Exception): async_session() context manager fails to acquire connection
          exception_type: sqlalchemy.exc.OperationalError or similar
      - DatabaseQueryFailure (Exception): SELECT, INSERT, or UPDATE operations fail
          exception_type: sqlalchemy.exc.SQLAlchemyError
      - CommitFailure (Exception): db.commit() fails due to constraint violation or transaction error
          exception_type: sqlalchemy.exc.IntegrityError or sqlalchemy.exc.SQLAlchemyError

    Side effects: Calls get_embedding(tool.problem_statement) via network/external service, Upserts ToolEmbedding record for tool.id, Inserts ProximityLink records for new neighbors above threshold, Inserts Notification records for neighbor authors, Executes vector similarity search using cosine_distance, Commits database transaction
    Idempotent: no
    """
    ...

# ── REQUIRED EXPORTS ──────────────────────────────────
# Your implementation module MUST export ALL of these names
# with EXACTLY these spellings. Tests import them by name.
# __all__ = ['scan_proximity', 'SilentFailure']
