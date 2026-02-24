"""
bgdb_utils.py - Shared parsing utilities for the BGDatabase binary format.

Binary file: bgdb_clean.bin (2,702,550 bytes)

Field layout:
    [4-byte LE uint32 name_length][name_length ASCII bytes]
    [31-byte header]
    [4-byte LE uint32 data_size]   <- at offset +31 from data_region start
    [actual data]                  <- at offset +35 from data_region start

Data types:
    int32   : data_size = row_count * 4, LE signed int32 values
    float32 : data_size = row_count * 4, LE IEEE-754 float32 values
    bool    : data_size = row_count, single byte per row (0/1)
    rank    : data_size = 9*row_count - 4 + 4, embedded row_count prefix,
              rank[i] = flat_int32s[2*i + 1]

String table (koKR) starts at offset 629160:
    [4-byte LE uint32 total_data_size]
    [4-byte LE uint32 string_count]
    [string_count * 8 bytes: (LE uint32 str_id, LE uint32 byte_offset)]
    [concatenated UTF-8 string data]

Name map starts at offset 485191:
    [4-byte LE uint32 entry_count]
    [entry_count * 8 bytes: (LE uint32 row_id, LE uint32 str_id)]

Table row ranges in name_map (sequential, zero-based index into name_map entries):
    creatureBase  : entries   0 -  538  (539 rows)
    itemBase      : entries 539 - 1858  (1320 rows)
    enemy         : entries 1859- 2245  (387 rows)
    boss          : entries 2246- 2355  (110 rows)
    stage         : entries 2356- 2855  (500 rows)
    item/equip    : entries 2856- 3388  (533 rows)
    commander     : entries 3389- 3423  (35 rows)
    cmdSpecialty  : entries 3424- 3458  (35 rows)
    artifact      : entries 3459- 4015  (557 rows)
"""

import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Known global constants
# ---------------------------------------------------------------------------

DEFAULT_BIN_PATH = 'bgdb_clean.bin'

#: Byte offset where the koKR string block's total_data_size uint32 lives.
KOKR_OFF: int = 629160

#: Byte offset where the name_map entry_count uint32 lives.
NAME_MAP_OFF: int = 485191


# ---------------------------------------------------------------------------
# Binary loader
# ---------------------------------------------------------------------------

def load_binary(path: Union[str, Path] = DEFAULT_BIN_PATH) -> bytes:
    """Load the BGDatabase binary file into memory.

    Parameters
    ----------
    path : str or Path
        Path to bgdb_clean.bin. Defaults to 'bgdb_clean.bin' in cwd.

    Returns
    -------
    bytes
        Full file contents.
    """
    with open(path, 'rb') as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Field-level helpers
# ---------------------------------------------------------------------------

def _field_data_region(data: bytes, field_off: int):
    """Return (data_region_start, data_size, actual_data_start) for a field.

    The field layout is:
        field_off + 0 : 4-byte LE uint32 name_length
        field_off + 4 : name_length ASCII bytes  (field name)
        data_region   : 31-byte header
        data_region+31: 4-byte LE uint32 data_size
        data_region+35: actual data bytes

    Parameters
    ----------
    data : bytes
        Full binary blob.
    field_off : int
        Byte offset of the 4-byte name_length prefix.

    Returns
    -------
    tuple[int, int, int]
        (data_region_start, data_size, actual_data_start)
    """
    name_len = struct.unpack_from('<I', data, field_off)[0]
    data_region = field_off + 4 + name_len
    data_size = struct.unpack_from('<I', data, data_region + 31)[0]
    actual_start = data_region + 35
    return data_region, data_size, actual_start


# ---------------------------------------------------------------------------
# Typed field parsers
# ---------------------------------------------------------------------------

def parse_int32_field(data: bytes, field_off: int) -> list:
    """Parse an int32 field (4 bytes per row, LE signed).

    Parameters
    ----------
    data : bytes
        Full binary blob.
    field_off : int
        Byte offset of the field's name_length prefix.

    Returns
    -------
    list[int]
        One signed int32 per row.
    """
    _, data_size, actual_start = _field_data_region(data, field_off)
    count = data_size // 4
    return [struct.unpack_from('<i', data, actual_start + i * 4)[0]
            for i in range(count)]


def parse_float32_field(data: bytes, field_off: int) -> list:
    """Parse a float32 field (4 bytes per row, LE IEEE-754).

    Parameters
    ----------
    data : bytes
        Full binary blob.
    field_off : int
        Byte offset of the field's name_length prefix.

    Returns
    -------
    list[float]
        One float32 per row.
    """
    _, data_size, actual_start = _field_data_region(data, field_off)
    count = data_size // 4
    return [struct.unpack_from('<f', data, actual_start + i * 4)[0]
            for i in range(count)]


def parse_bool_field(data: bytes, field_off: int) -> list:
    """Parse a bool field (1 byte per row).

    Parameters
    ----------
    data : bytes
        Full binary blob.
    field_off : int
        Byte offset of the field's name_length prefix.

    Returns
    -------
    list[bool]
        One bool per row (non-zero byte -> True).
    """
    _, data_size, actual_start = _field_data_region(data, field_off)
    return [bool(data[actual_start + i]) for i in range(data_size)]


def parse_rank_field(data: bytes, field_off: int, row_count: int) -> list:
    """Parse the rank field with its special 9-bytes-per-row encoding.

    Layout inside the data block:
        [4-byte LE uint32 embedded_row_count]
        [flat bytes: pairs of (something, rank_value) as int32s]

    rank[i] = flat_int32s[2*i + 1]

    Parameters
    ----------
    data : bytes
        Full binary blob.
    field_off : int
        Byte offset of the field's name_length prefix.
    row_count : int
        Expected number of rows (used to bound index access).

    Returns
    -------
    list[int]
        Rank value per row; 0 for any out-of-bounds index.
    """
    _, data_size, actual_start = _field_data_region(data, field_off)

    # Skip the embedded row_count uint32 (4 bytes)
    flat_start = actual_start + 4
    flat_bytes = data[flat_start: actual_start + data_size]
    n_int32 = len(flat_bytes) // 4
    flat_ints = [struct.unpack_from('<i', flat_bytes, j * 4)[0]
                 for j in range(n_int32)]

    ranks = []
    for i in range(row_count):
        idx = 2 * i + 1
        ranks.append(flat_ints[idx] if idx < len(flat_ints) else 0)
    return ranks


# ---------------------------------------------------------------------------
# Auto-detect parser
# ---------------------------------------------------------------------------

def auto_parse_field(data: bytes, field_off: int) -> tuple:
    """Auto-detect field type from data_size vs implied row count and parse.

    Heuristic:
        data_size % 4 == 0 AND data_size // 4 rows look plausible -> try int32
        data_size % 4 != 0 -> bool (1 byte/row)
        For int32-sized blocks we try float32 vs int32 based on value ranges:
            if all values are between -1e10 and 1e10 and many are non-integer
            -> float32; otherwise -> int32.

    This is a best-effort heuristic; for known fields prefer the typed parsers.

    Parameters
    ----------
    data : bytes
        Full binary blob.
    field_off : int
        Byte offset of the field's name_length prefix.

    Returns
    -------
    tuple[str, list]
        ('int32' | 'float32' | 'bool', parsed_values)
    """
    _, data_size, actual_start = _field_data_region(data, field_off)

    if data_size == 0:
        return ('int32', [])

    if data_size % 4 != 0:
        # Likely bool
        values = [bool(data[actual_start + i]) for i in range(data_size)]
        return ('bool', values)

    count = data_size // 4

    # Read as both int32 and float32 and decide
    int_vals = [struct.unpack_from('<i', data, actual_start + i * 4)[0]
                for i in range(count)]
    float_vals = [struct.unpack_from('<f', data, actual_start + i * 4)[0]
                  for i in range(count)]

    # If any float is NaN or infinite -> not float32
    import math
    has_bad_float = any(math.isnan(v) or math.isinf(v) for v in float_vals)
    if has_bad_float:
        return ('int32', int_vals)

    # If many values have a fractional part -> float32
    non_integer = sum(1 for v in float_vals if v != int(v) if abs(v) < 1e10)
    if non_integer > count * 0.1:
        return ('float32', float_vals)

    return ('int32', int_vals)


# ---------------------------------------------------------------------------
# String table parser
# ---------------------------------------------------------------------------

def parse_kokr_strings(data: bytes, kokr_off: int = KOKR_OFF) -> dict:
    """Parse the koKR string table.

    Layout at kokr_off:
        [4-byte LE uint32 total_data_size]
        [4-byte LE uint32 string_count]
        [string_count * 8 bytes: (LE uint32 str_id, LE uint32 byte_offset)]
        [UTF-8 string data, total_data_size bytes]

    Each string spans from byte_offset[str_id] to byte_offset[next_str_id]
    (or total_data_size for the last entry).

    Parameters
    ----------
    data : bytes
        Full binary blob.
    kokr_off : int
        Byte offset of total_data_size. Defaults to KOKR_OFF (629160).

    Returns
    -------
    dict[int, str]
        Mapping str_id -> decoded UTF-8 string.
    """
    total_data_size = struct.unpack_from('<I', data, kokr_off)[0]
    string_count = struct.unpack_from('<I', data, kokr_off + 4)[0]

    offset_table: dict = {}
    for i in range(string_count):
        entry_off = kokr_off + 8 + i * 8
        sid = struct.unpack_from('<I', data, entry_off)[0]
        boff = struct.unpack_from('<I', data, entry_off + 4)[0]
        offset_table[sid] = boff

    str_data_start = kokr_off + 8 + string_count * 8

    sorted_sids = sorted(offset_table.keys())
    sid_to_next: dict = {}
    for i, sid in enumerate(sorted_sids):
        if i + 1 < len(sorted_sids):
            sid_to_next[sid] = offset_table[sorted_sids[i + 1]]
        else:
            sid_to_next[sid] = total_data_size

    strings: dict = {}
    for sid in sorted_sids:
        b0 = offset_table[sid]
        b1 = sid_to_next[sid]
        raw = data[str_data_start + b0: str_data_start + b1]
        strings[sid] = raw.decode('utf-8', errors='replace')

    return strings


# ---------------------------------------------------------------------------
# Name map parser
# ---------------------------------------------------------------------------

def parse_name_map(data: bytes, off: int = NAME_MAP_OFF) -> list:
    """Parse the global name_map into a flat list of (row_id, str_id) tuples.

    Layout at off:
        [4-byte LE uint32 entry_count]
        [entry_count * 8 bytes: (LE uint32 row_id, LE uint32 str_id)]

    The entries are ordered by table (creatureBase first, then itemBase, etc.).
    Use map_start + row_count slicing to isolate a specific table's entries.

    Parameters
    ----------
    data : bytes
        Full binary blob.
    off : int
        Byte offset of entry_count. Defaults to NAME_MAP_OFF (485191).

    Returns
    -------
    list[tuple[int, int]]
        [(row_id, str_id), ...] in file order.
    """
    entry_count = struct.unpack_from('<I', data, off)[0]
    entries_start = off + 4
    result = []
    for i in range(entry_count):
        entry_off = entries_start + i * 8
        row_id = struct.unpack_from('<I', data, entry_off)[0]
        str_id = struct.unpack_from('<I', data, entry_off + 4)[0]
        result.append((row_id, str_id))
    return result


# ---------------------------------------------------------------------------
# Table-level string accessor
# ---------------------------------------------------------------------------

def get_table_strings(
    name_map_entries: list,
    strings: dict,
    map_start: int,
    row_count: int,
    default_stride: int = 5,
) -> list:
    """Return per-row string lists for a table's slice of the name_map.

    Each name_map entry carries a str_id that points to the FIRST of N
    consecutive strings in the koKR table.  N (stride) varies by table type;
    pass the appropriate default_stride for the table you are parsing.

    For each row the function returns up to default_stride strings starting at
    the mapped str_id.  If the str_id exceeds the koKR range (> 9703) or is
    missing from the strings dict the list for that row will be empty.

    Parameters
    ----------
    name_map_entries : list[tuple[int, int]]
        Full name_map as returned by parse_name_map().
    strings : dict[int, str]
        koKR string dict as returned by parse_kokr_strings().
    map_start : int
        Zero-based index into name_map_entries where this table's rows begin.
        E.g. 0 for creatureBase, 539 for itemBase.
    row_count : int
        Number of rows in this table.
    default_stride : int
        How many consecutive str_ids to fetch per row. Defaults to 5.

    Returns
    -------
    list[list[str]]
        Outer list has row_count elements; inner list has up to default_stride
        strings (stripped, may be empty strings if str_id not in koKR).
    """
    max_kokr_sid = max(strings.keys()) if strings else 0

    result = []
    for row in range(row_count):
        map_idx = map_start + row
        if map_idx >= len(name_map_entries):
            result.append([])
            continue

        _row_id, base_sid = name_map_entries[map_idx]

        if base_sid > max_kokr_sid:
            # This table's strings are outside the koKR range
            result.append([])
            continue

        row_strs = []
        for offset in range(default_stride):
            sid = base_sid + offset
            s = strings.get(sid, '')
            row_strs.append(s.strip() if s else '')
        result.append(row_strs)

    return result


# ---------------------------------------------------------------------------
# Convenience: read field name from binary
# ---------------------------------------------------------------------------

def read_field_name(data: bytes, field_off: int) -> str:
    """Read the ASCII field name stored at field_off.

    Parameters
    ----------
    data : bytes
        Full binary blob.
    field_off : int
        Byte offset of the 4-byte name_length prefix.

    Returns
    -------
    str
        The field name as an ASCII string.
    """
    name_len = struct.unpack_from('<I', data, field_off)[0]
    return data[field_off + 4: field_off + 4 + name_len].decode('ascii', errors='replace')


# ---------------------------------------------------------------------------
# Convenience: next field offset
# ---------------------------------------------------------------------------

def next_field_offset(data: bytes, field_off: int) -> int:
    """Compute the byte offset immediately after this field's data block.

    Useful for walking fields sequentially when offsets are not pre-computed.

    Note: fields are separated by a 22-byte gap (4-byte type marker +
    18-byte GUID) before the next field's name_length prefix.

    Parameters
    ----------
    data : bytes
        Full binary blob.
    field_off : int
        Byte offset of the current field's name_length prefix.

    Returns
    -------
    int
        Byte offset where the next field's name_length prefix begins
        (i.e. end_of_current_field + 22).
    """
    name_len = struct.unpack_from('<I', data, field_off)[0]
    data_region = field_off + 4 + name_len
    data_size = struct.unpack_from('<I', data, data_region + 31)[0]
    end_of_data = data_region + 35 + data_size
    return end_of_data + 22  # skip inter-field separator


# ---------------------------------------------------------------------------
# Dictionary Block parser (BGDatabase localization system)
# ---------------------------------------------------------------------------

@dataclass
class DictBlock:
    """A parsed BGDatabase dictionary block."""
    start: int
    total_len: int
    count: int
    pairs: List[Tuple[int, int]]
    blob_start: int
    blob: bytes


def try_parse_dict_block(buf: bytes, start: int) -> Optional[DictBlock]:
    """Try to parse a dictionary block at the given byte offset.

    Block structure:
        [total_len: 4B][count: 4B][pairs: count * 8B (key, offset)][blob: total_len B]
    """
    if start < 0 or start + 8 > len(buf):
        return None

    total_len = struct.unpack_from('<I', buf, start)[0]
    count = struct.unpack_from('<I', buf, start + 4)[0]

    if not (1 <= count <= 200_000):
        return None
    if not (1 <= total_len <= len(buf)):
        return None

    pair_start = start + 8
    blob_start = pair_start + count * 8
    blob_end = blob_start + total_len
    if blob_end > len(buf):
        return None

    pairs: List[Tuple[int, int]] = []
    last_off = -1
    last_key = -1
    for i in range(count):
        k = struct.unpack_from('<I', buf, pair_start + i * 8)[0]
        off = struct.unpack_from('<I', buf, pair_start + i * 8 + 4)[0]
        if off < last_off or k < last_key or off >= total_len:
            return None
        pairs.append((k, off))
        last_off = off
        last_key = k

    blob = buf[blob_start:blob_end]
    return DictBlock(start=start, total_len=total_len, count=count,
                     pairs=pairs, blob_start=blob_start, blob=blob)


def find_dict_block_by_probe(buf: bytes, probe: str,
                              min_count: int = 1000) -> DictBlock:
    """Find a dictionary block by probing for a known string nearby.

    Searches for the length-prefixed `probe` string in the binary, then
    scans forward to find a valid DictBlock header.
    """
    probe_bytes = struct.pack('<I', len(probe)) + probe.encode('utf-8')
    candidates: List[DictBlock] = []

    search_pos = 0
    while True:
        pos = buf.find(probe_bytes, search_pos)
        if pos == -1:
            break
        search_pos = pos + 1

        scan_start = pos + len(probe_bytes)
        scan_end = min(pos + 700, len(buf) - 16)
        for pair_start in range(scan_start, scan_end):
            start = pair_start - 8
            block = try_parse_dict_block(buf, start)
            if block is None:
                continue
            if block.count < min_count:
                continue
            candidates.append(block)

    if not candidates:
        raise RuntimeError(f"Dictionary block not found for probe='{probe}'")

    candidates.sort(key=lambda b: (b.count, b.total_len), reverse=True)
    return candidates[0]


def decode_dict_block(block: DictBlock) -> Dict[int, str]:
    """Decode a DictBlock into an {id: string} mapping."""
    out: Dict[int, str] = {}
    for i, (k, off) in enumerate(block.pairs):
        next_off = (block.pairs[i + 1][1]
                    if i + 1 < len(block.pairs)
                    else block.total_len)
        chunk = block.blob[off:next_off]
        out[k] = chunk.decode('utf-8', errors='ignore')
    return out


# ---------------------------------------------------------------------------
# Localization system
# ---------------------------------------------------------------------------

_COLOR_TAG_RE = re.compile(r'\[[0-9A-Fa-f]{6}\]|\[-\]')


def build_localization(data: bytes) -> Tuple[Dict[str, int], Dict[int, str]]:
    """Build the full localization lookup from the binary payload.

    The BGDatabase stores two parallel dictionary blocks:
        - 'name' block:  numeric_id -> key string  (e.g. "sn97", "hn96", "Race26")
        - 'koKR' block:  numeric_id -> Korean text  (e.g. "발목 공격", "제리", "인간")

    Returns
    -------
    tuple[dict[str, int], dict[int, str]]
        (key_to_id, ko_map) where:
        - key_to_id maps localization key string -> numeric id
        - ko_map maps numeric id -> Korean text
    """
    name_block = find_dict_block_by_probe(data, 'name', min_count=4000)
    ko_block = find_dict_block_by_probe(data, 'koKR', min_count=4000)

    key_id_map = decode_dict_block(name_block)   # id -> key string
    ko_map = decode_dict_block(ko_block)          # id -> Korean text
    key_to_id = {v: k for k, v in key_id_map.items()}

    return key_to_id, ko_map


def loc_text(key_to_id: Dict[str, int], ko_map: Dict[int, str],
             key: str) -> Optional[str]:
    """Look up Korean text for a localization key.

    Keys follow the pattern: prefix + numeric_id, e.g.:
        hn96  -> hero name for hero_id 96 (제리)
        hc96  -> hero class/subtitle (칼라무쉬 백정)
        hs96  -> hero story
        sn97  -> skill name for skill_id 97 (발목 공격)
        ss97  -> skill story/description
        Race26 -> race label (인간)
        Location4 -> location label (칼라무쉬 왕국)
        Gender0 -> gender label (남성)
        House3  -> house label
        Religion1 -> religion label
        Individuality0 -> individuality label

    Returns None if key not found.
    """
    idx = key_to_id.get(key)
    if idx is None:
        return None
    text = ko_map.get(idx, '')
    return _COLOR_TAG_RE.sub('', text).strip()
