
import re
from typing import List, Optional, Tuple

# Assembler directives recognised by the parser
DIRECTIVES = {
    '.text', '.data', '.org', '.word', '.half', '.byte',
    '.zero', '.align', '.equ', '.set', '.globl', '.global',
}


def tokenize_line(line: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Parse a single assembly line into (label, mnemonic, operands).
    Strips comments (# ; //) and whitespace.
    Returns (None, None, []) for blank / comment-only lines.
    """
    # Strip comments
    for marker in ['#', ';', '//']:
        idx = line.find(marker)
        if idx != -1:
            line = line[:idx]

    line = line.strip()
    if not line:
        return None, None, []

    label = None
    # Label detection: identifier followed by colon
    label_match = re.match(r'^(\w+):\s*(.*)', line)
    if label_match:
        label = label_match.group(1)
        line = label_match.group(2).strip()

    if not line:
        return label, None, []

    # Split mnemonic from operand string
    parts = line.split(None, 1)
    mnemonic = parts[0]
    operands: List[str] = []

    if len(parts) > 1:
        # Split by commas NOT inside parentheses (preserves memory operands like 0(x1))
        ops = re.split(r',\s*(?![^()]*\))', parts[1])
        operands = [op.strip() for op in ops if op.strip()]

    return label, mnemonic, operands
