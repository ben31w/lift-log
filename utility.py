"""
Contains utility functions.
"""

import hashlib
import zlib


def hash_html(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def compress_html(content: str) -> bytes:
    return zlib.compress(content.encode('utf-8'))

def decompress_html(blob: bytes) -> str:
    return zlib.decompress(blob).decode('utf-8')
