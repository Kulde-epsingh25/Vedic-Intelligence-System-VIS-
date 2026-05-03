"""
pgvector store wrapper for Supabase-backed semantic search.
"""

from typing import List


class PgVectorStore:
    """Placeholder wrapper around pgvector queries."""

    def query(self, embedding: List[float], k: int = 10) -> List[str]:
        """
        Query pgvector for similar verse IDs.

        Args:
            embedding: Query embedding.
            k: Number of results.

        Returns:
            List of verse IDs.

        Example:
            >>> store = PgVectorStore()
            >>> store.query([0.0] * 768)
        """
        return []