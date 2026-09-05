
import re
from typing import Dict

def sign_extend(val: int, bits: int) -> int:
    """Sign extend a value from 'bits' width to a Python signed int."""
    if val & (1 << (bits - 1)):
        return val - (1 << bits)
    return val

def to_unsigned(val: int, bits: int) -> int:
    """Mask a value to 'bits' width (unsigned representation)."""
    return val & ((1 << bits) - 1)

def check_range(val: int, bits: int, signed: bool = True, name: str = "immediate"):
    """Check that a value fits in the given number of bits."""
    if signed:
        lo = -(1 << (bits - 1))
        hi = (1 << (bits - 1)) - 1
    else:
        lo = 0
        hi = (1 << bits) - 1
    if val < lo or val > hi:
        raise ValueError(f"{name} value {val} out of range [{lo}, {hi}]")

def resolve_value(token: str, labels: Dict[str, int]) -> int:
    """Resolve a token to an integer value (label, decimal, hex, or binary literal)."""
    token = token.strip()
    if token in labels:
        return labels[token]
    try:
        if token.startswith('0x') or token.startswith('0X'):
            return int(token, 16)
        elif token.startswith('0b') or token.startswith('0B'):
            return int(token, 2)
        else:
            return int(token)
    except ValueError:
        raise ValueError(f"Cannot resolve value: '{token}'")

def parse_imm(token: str, labels: Dict[str, int], pc: int = 0, relative: bool = False) -> int:
    """
    Parse an immediate value. Supports:
      - Decimal, hex (0x), binary (0b) literals
      - Label names
      - %hi(symbol) / %lo(symbol) relocations
      - PC-relative offsets (when relative=True)
    """
    token = token.strip().rstrip(',')

    # %hi() modifier -> upper 20 bits, adjusted for %lo sign extension
    hi_match = re.match(r'%hi\((.+)\)', token)
    if hi_match:
        val = resolve_value(hi_match.group(1), labels)
        lo = val & 0xFFF
        if lo & 0x800:
            return ((val >> 12) + 1) & 0xFFFFF
        return (val >> 12) & 0xFFFFF

    # %lo() modifier -> lower 12 bits, sign extended
    lo_match = re.match(r'%lo\((.+)\)', token)
    if lo_match:
        val = resolve_value(lo_match.group(1), labels)
        return sign_extend(val & 0xFFF, 12)

    val = resolve_value(token, labels)

    if relative:
        val = val - pc

    return val
