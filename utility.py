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

# def decompress_and_write_html(blob: bytes) -> str:
#     """
#     Decompress the given blob into its original file content.
#     Write the original content to a new file.
#     Return the path to that file.
#     :param blob: compressed HTML file content
#     :return: path to the decompressed HTML file
#     """
#     file_to_write = f'usr{os.path.sep}ben31w_{file_hash}.html'
#     with open(file_to_write, 'w') as f:
#         f.write(html_content)
