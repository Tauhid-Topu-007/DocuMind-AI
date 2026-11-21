import re


def split_text(text: str, size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into ~`size` char chunks with `overlap`, preferring natural breaks."""
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    if overlap >= size // 2:
        overlap = size // 5
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            window_start = start + size // 2
            for sep in ("\n\n", "\n", ". ", " "):
                cut = text.rfind(sep, window_start, end)
                if cut != -1:
                    end = cut + len(sep)
                    break
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks
