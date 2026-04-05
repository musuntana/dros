from .base import BaseRepository


class ManuscriptRepository(BaseRepository):
    """Owns assertions, manuscript aggregates, and block-to-assertion mappings."""

    store_names = ("assertions", "manuscripts", "manuscript_blocks", "block_assertion_links")
