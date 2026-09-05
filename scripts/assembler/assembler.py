
import sys
from typing import Dict, List, Tuple

from .parser import tokenize_line, DIRECTIVES
from .utils import parse_imm
from .instructions import assemble_instruction
from .pseudo import EXPANDS_TO_TWO
from .output import to_hex_file, to_annotated_hex


class Assembler:

    def __init__(self, base_addr: int = 0):
        self.base_addr = base_addr
        self.labels: Dict[str, int] = {}
        self.instructions: List[Tuple[int, int, str, List[str]]] = []  # (pc, line_num, mnemonic, operands)
        self.errors: List[str] = []
        

    def assemble(self, source: str) -> List[int]:
        """Assemble source text and return a list of 32-bit machine code words."""
        lines = source.splitlines()
        self._pass1(lines)
        if self.errors:
            return []
        return self._pass2()

    """PASS 1 – label collection and instruction sizing"""
    def _pass1(self, lines: List[str]):
        pc = self.base_addr
        labels: Dict[str, int] = {}

        for line_num, line in enumerate(lines, 1):
            try:
                label, mnemonic, operands = tokenize_line(line)

                if label:
                    if label in labels:
                        self.errors.append(f"Line {line_num}: Duplicate label '{label}'")
                    else:
                        labels[label] = pc

                if mnemonic is None:
                    continue

                mn = mnemonic.lower()

                # Handle assembler directives
                if mn in DIRECTIVES or mn.startswith('.'):
                    pc = self._handle_directive(mn, operands, labels, pc, line_num)
                    continue

                # Regular instruction – compute size
                size = self._instruction_size(mn, operands, labels)
                self.instructions.append((pc, line_num, mn, operands))
                pc += size

            except Exception as e:
                self.errors.append(f"Line {line_num}: {e}")

        self.labels = labels

    def _handle_directive(self, mn: str, operands: List[str],
                          labels: Dict[str, int], pc: int, line_num: int) -> int:
        """Process a directive and return the updated PC."""
        if mn == '.org':
            return parse_imm(operands[0], labels)
        if mn == '.word':
            return pc + 4 * len(operands)
        if mn == '.half':
            return pc + 2 * len(operands)
        if mn == '.byte':
            return pc + len(operands)
        if mn == '.zero':
            return pc + parse_imm(operands[0], labels)
        if mn == '.align':
            alignment = 1 << parse_imm(operands[0], labels)
            while pc % alignment != 0:
                pc += 1
            return pc
        if mn in ('.equ', '.set'):
            name = operands[0].rstrip(',')
            val = parse_imm(operands[1], labels)
            labels[name] = val
            return pc
        if mn in ('.globl', '.global', '.text', '.data'):
            return pc  # informational only
        self.errors.append(f"Line {line_num}: Unknown directive '{mn}'")
        return pc

    @staticmethod
    def _instruction_size(mn: str, operands: List[str], labels: Dict[str, int]) -> int:
        """Return instruction size in bytes (4 or 8 for multi-word pseudo-instructions)."""
        if mn in EXPANDS_TO_TWO:
            if mn == 'li':
                try:
                    imm = parse_imm(operands[1], labels)
                    if -2048 <= imm <= 2047:
                        return 4
                except (ValueError, IndexError):
                    pass
            return 8
        return 4

    """PASS 2 – encode instructions"""
    def _pass2(self) -> List[int]:
        output: Dict[int, int] = {}

        for pc, line_num, mnemonic, operands in self.instructions:
            try:
                words = assemble_instruction(mnemonic, operands, self.labels, pc)
                for i, word in enumerate(words):
                    output[pc + i * 4] = word & 0xFFFFFFFF
            except Exception as e:
                self.errors.append(f"Line {line_num}: {e}")

        if self.errors:
            return []
        if not output:
            return []

        # Build a contiguous word list from the address map
        min_addr = min(output) & ~3
        max_addr = (max(output) + 3) & ~3
        return [output.get(addr, 0x00000000) for addr in range(min_addr, max_addr + 1, 4)]




def assemble_file(input_path: str, output_path: str,
                  base_addr: int = 0, annotated: bool = False):
    """Assemble an input .s file and write the output .hex file."""
    with open(input_path, 'r') as f:
        source = f.read()

    asm = Assembler(base_addr)
    words = asm.assemble(source)

    if asm.errors:
        print(f"Assembly failed with {len(asm.errors)} error(s):", file=sys.stderr)
        for err in asm.errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    hex_content = to_annotated_hex(words, base_addr) if annotated else to_hex_file(words, base_addr)

    with open(output_path, 'w') as f:
        f.write(hex_content)

    print(f"Assembled {len(words)} words ({len(words) * 4} bytes)")
    print(f"Output written to: {output_path}")
    return words
