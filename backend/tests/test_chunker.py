"""
Chunker unit tests - no database or network required.
"""
import tiktoken

from app.services.chunker import ChunkRecord, _hard_split, chunk_document
from app.services.extract import ExtractedBlock


def _token_count(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def _make_blocks(text: str, page: int | None = None) -> list[ExtractedBlock]:
    return [ExtractedBlock(text=text, page_number=page, section_ref=None)]


def test_short_text_not_split():
    blocks = _make_blocks("Hello world.")
    chunks = chunk_document(blocks, "txt")
    assert len(chunks) == 1
    assert chunks[0].content == "Hello world."


def test_overlap_continuity():
    """Last `overlap` tokens of chunk i must appear at the start of chunk i+1."""
    enc = tiktoken.get_encoding("cl100k_base")
    # Build a long text that will require multiple chunks
    long_text = " ".join(f"word{i}" for i in range(3000))
    chunks = _hard_split(long_text, max_tok=100, overlap=20)

    assert len(chunks) >= 2, "Expected at least 2 chunks"

    for i in range(len(chunks) - 1):
        tail_tokens = enc.encode(chunks[i])[-20:]
        head_tokens = enc.encode(chunks[i + 1])[:20]
        # The tail of chunk i must appear at the start of chunk i+1
        assert tail_tokens == head_tokens, (
            f"Overlap mismatch at chunk boundary {i}/{i+1}"
        )


def test_code_file_uses_500_100():
    """Python files get max_tokens=500, overlap=100."""
    enc = tiktoken.get_encoding("cl100k_base")
    # Build text that's ~1200 tokens to force 3 chunks at 500/100
    long_text = " ".join(f"tok{i}" for i in range(1200))
    blocks = _make_blocks(long_text)
    chunks = chunk_document(blocks, "py")

    for c in chunks:
        assert _token_count(c.content) <= 500, f"Chunk too large: {_token_count(c.content)}"
    assert len(chunks) >= 3


def test_default_uses_1000_200():
    """Default config (txt) gets max_tokens=1000, overlap=200."""
    enc = tiktoken.get_encoding("cl100k_base")
    long_text = " ".join(f"tok{i}" for i in range(2500))
    blocks = _make_blocks(long_text)
    chunks = chunk_document(blocks, "txt")

    for c in chunks:
        assert _token_count(c.content) <= 1000


def test_page_numbers_survive():
    """Page number from the ExtractedBlock is preserved on every chunk."""
    long_text = " ".join(f"tok{i}" for i in range(3000))
    blocks = [ExtractedBlock(text=long_text, page_number=7, section_ref="Introduction")]
    chunks = chunk_document(blocks, "txt")
    assert len(chunks) > 1
    for c in chunks:
        assert c.page_number == 7
        assert c.section_ref == "Introduction"


def test_chunk_index_sequential():
    blocks = [
        ExtractedBlock(text=" ".join(f"w{i}" for i in range(800)), page_number=1, section_ref=None),
        ExtractedBlock(text=" ".join(f"x{i}" for i in range(800)), page_number=2, section_ref=None),
    ]
    chunks = chunk_document(blocks, "md")
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_custom_chunk_config():
    long_text = " ".join(f"tok{i}" for i in range(500))
    blocks = _make_blocks(long_text)
    chunks = chunk_document(blocks, "txt", chunk_config={"max_tokens": 100, "overlap": 10})
    for c in chunks:
        assert _token_count(c.content) <= 100


def test_empty_block_skipped():
    blocks = [
        ExtractedBlock(text="   ", page_number=None, section_ref=None),
        ExtractedBlock(text="Hello.", page_number=1, section_ref=None),
    ]
    chunks = chunk_document(blocks, "md")
    assert len(chunks) == 1
    assert chunks[0].content == "Hello."
