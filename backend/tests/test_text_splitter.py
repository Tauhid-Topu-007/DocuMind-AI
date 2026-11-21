from app.services.text_splitter import split_text


def test_short_text_single_chunk():
    assert split_text("hello world", 1000, 200) == ["hello world"]


def test_empty():
    assert split_text("   ", 1000, 200) == []


def test_chunks_cover_text_and_respect_size():
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = split_text(text, 500, 100)
    assert len(chunks) > 5
    assert all(len(c) <= 500 for c in chunks)
    assert chunks[0].startswith("word0") and chunks[-1].endswith("word1999")


def test_overlap_exists():
    text = " ".join(f"w{i}" for i in range(500))
    a, b = split_text(text, 300, 80)[:2]
    assert a.split()[-1] in b.split()
