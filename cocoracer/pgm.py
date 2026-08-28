from pathlib import Path

import numpy as np
from scipy.ndimage import label

DEFAULT_THRESHOLD = 250


class PgmError(ValueError):
    pass


def parse_pgm(path: Path | str) -> np.ndarray:
    """Parse a binary (P5) PGM file into a uint8 image.

    Comment lines in the header are skipped. The returned array is shaped
    (height, width).

    Args:
        path: Path to the .pgm file.

    Returns:
        The image as a uint8 array.

    Raises:
        PgmError: If the file is not a P5 PGM or its pixel data is short.
    """
    data = Path(path).read_bytes()
    width, height, maxval, offset = _read_header(data)
    if maxval > 255:
        raise PgmError(f"unsupported PGM maxval {maxval}, expected <= 255")
    pixel_count = width * height
    if len(data) < offset + pixel_count:
        raise PgmError(f"expected {pixel_count} pixel bytes, got {len(data) - offset}")
    return np.frombuffer(data[offset : offset + pixel_count], dtype=np.uint8).reshape(
        height, width
    )


def drivable_mask(image: np.ndarray, threshold: int = DEFAULT_THRESHOLD) -> np.ndarray:
    """Build the boolean drivable mask of a PGM image.

    A pixel at or above the threshold is drivable; everything else is wall.
    Only the largest drivable connected component is kept, so the
    anti-aliasing specks carried by the shipped maps are dropped.

    Args:
        image: uint8 image shaped (height, width).
        threshold: Minimum pixel value that counts as drivable.

    Returns:
        Boolean array shaped like the image.
    """
    mask = (image >= threshold).astype(bool)
    if not mask.any():
        return mask
    labeled = np.zeros(mask.shape, dtype=np.int32)
    label(mask, output=labeled)
    counts = np.bincount(labeled.ravel())
    largest = int(np.argmax(counts[1:]) + 1)
    return np.equal(labeled, largest)


def _read_header(data: bytes) -> tuple[int, int, int, int]:
    pos = 0

    def next_token() -> bytes:
        nonlocal pos
        while True:
            while pos < len(data) and data[pos] in b" \t\r\n":
                pos += 1
            if data[pos : pos + 1] == b"#":
                newline = data.find(b"\n", pos)
                if newline == -1:
                    raise PgmError("unterminated comment in PGM header")
                pos = newline + 1
            else:
                break
        start = pos
        while pos < len(data) and data[pos] not in b" \t\r\n":
            pos += 1
        return data[start:pos]

    magic = next_token()
    if magic != b"P5":
        raise PgmError(f"expected P5 magic, got {magic!r}")
    try:
        width = int(next_token())
        height = int(next_token())
        maxval = int(next_token())
    except ValueError:
        raise PgmError("non-numeric PGM header field") from None
    if width <= 0 or height <= 0 or maxval <= 0:
        raise PgmError("non-positive PGM header field")
    # One whitespace byte separates maxval from the pixel data.
    pos += 1
    return width, height, maxval, pos
