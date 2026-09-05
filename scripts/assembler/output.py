
from typing import List


def to_hex_file(words: List[int], base_addr: int = 0) -> str:
    """Generate a Verilog $readmemh compatible hex file (one word per line)."""
    lines = [f"{w:08X}" for w in words]
    return '\n'.join(lines) + '\n'


def to_annotated_hex(words: List[int], base_addr: int = 0) -> str:
    """Hex file with address annotations as comments."""
    lines = []
    for i, w in enumerate(words):
        addr = base_addr + i * 4
        lines.append(f"{w:08X} // @0x{addr:08X} (word {i})")
    return '\n'.join(lines) + '\n'


def to_binary_listing(words: List[int], base_addr: int = 0) -> str:
    """Binary listing for debugging (address, hex, binary)."""
    lines = []
    for i, w in enumerate(words):
        addr = base_addr + i * 4
        lines.append(f"0x{addr:08X}:  0x{w:08X}  {w:032b}")
    return '\n'.join(lines) + '\n'
