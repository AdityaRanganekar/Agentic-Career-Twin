import hashlib

def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    """Computes a hexadecimal hash of raw byte data."""
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()

def hash_text(text: str, algorithm: str = "sha256") -> str:
    """Computes a hexadecimal hash of text strings."""
    return hash_bytes((text or "").strip().encode("utf-8"), algorithm=algorithm)

def hash_file(filepath: str, algorithm: str = "sha256") -> str:
    """Computes a hash of an on-disk file in chunks."""
    hasher = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

