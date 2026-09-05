# RV32I Assembler

A custom, two-pass, modular Python assembler for the RISC-V RV32I base integer instruction set. This tool is designed to take standard RISC-V assembly code (`.s` or `.asm` files) and compile it directly into hex files (`.hex`) that are fully compatible with Verilog's `$readmemh` system task for CPU simulation.

## Features

- **Two-Pass Architecture**: Fully supports forward and backward label references.
- **Pseudo-instruction Expansion**: Automatically expands macros like `li`, `la`, `call`, `tail`, `j`, `ret`, `mv`, and branch-zero variants into their native RV32I equivalents.
- **Relocations**: Supports `%hi(symbol)` and `%lo(symbol)` modifiers for 32-bit address loading, accurately handling sign-extension compensation.
- **PC-Relative Addressing**: Automatically calculates absolute-to-relative offsets for branch (`B-type`) and jump (`J-type`) instructions.
- **Assembler Directives**: Supports `.word`, `.half`, `.byte`, `.zero`, `.align`, `.org`, `.equ`, and `.set`.
- **Multiple Output Formats**: Generates raw hex, address-annotated hex, and binary listing formats for debugging.

## Usage

You can run the assembler using the top-level convenience script `rvasm.py` located in the `scripts/` directory, or by invoking the module directly.

```bash
# Basic usage (outputs to program.hex)
python scripts/rvasm.py path/to/program.s

# Specify a custom output file
python scripts/rvasm.py path/to/program.s -o out.hex

# Generate an annotated hex file (adds inline comments with addresses)
python scripts/rvasm.py path/to/program.s -a

# Print a binary listing to stdout for debugging
python scripts/rvasm.py path/to/program.s -l

# Specify a base memory address (e.g., if ROM starts at 0x1000)
python scripts/rvasm.py path/to/program.s -b 0x1000
```

Alternatively, run it as a Python module from within the `scripts` directory:
```bash
python -m assembler path/to/program.s
```

## Supported Instructions

For full details on syntax, registers, memory addressing, macros, and assembler directives, see the [Programmer's Reference Guide](REFERENCE.md).

| Format | Instructions |
| :--- | :--- |
| **R-Type** | `add`, `sub`, `sll`, `slt`, `sltu`, `xor`, `srl`, `sra`, `or`, `and` |
| **I-Type** | `addi`, `slti`, `sltiu`, `xori`, `ori`, `andi`, `slli`, `srli`, `srai` |
| **Load** | `lb`, `lh`, `lw`, `lbu`, `lhu` |
| **Store** | `sb`, `sh`, `sw` |
| **Branch** | `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu` |
| **Jump** | `jal`, `jalr` |
| **U-Type** | `lui`, `auipc` |
| **Pseudo** | `nop`, `li`, `la`, `mv`, `not`, `neg`, `seqz`, `snez`, `sltz`, `sgtz`, `j`, `jr`, `ret`, `call`, `tail`, `beqz`, `bnez`, `blez`, `bgez`, `bltz`, `bgtz` |

*(Note: `fence`, `ecall`, and `ebreak` are intentionally omitted as they are not implemented in the target CPU core).*

## Modular Architecture

The assembler is built using a clean, multi-module architecture to ensure it remains easy to maintain and extend. For a deep dive into the specific classes, methods, and responsibilities of each module, see the [Module Documentation](MODULE_DOCS.md).

* `assembler.py` - The core orchestrator handling Pass 1 (label resolution/sizing) and Pass 2 (code generation).
* `parser.py` - Tokenizes raw text lines, strips comments, extracts labels, and identifies directives.
* `instructions.py` - Validates operands and dispatches mnemonics to their respective binary encoders.
* `pseudo.py` - Detects pseudo-instructions and expands them into 1 or 2 native RV32I instructions.
* `encoding.py` - Handles the low-level bit-packing and immediate swizzling (e.g., scrambling branch offsets) for all formats.
* `opcodes.py` - Contains the dictionaries mapping mnemonics to their RISC-V `opcode`, `funct3`, and `funct7` constants.
* `registers.py` - Maps standard hardware names (`x0`-`x31`) and ABI names (`zero`, `ra`, `sp`, `a0`, etc.) to integer IDs.
* `utils.py` - Helper math functions for sign-extension, two's complement masking, range checking, and relocation evaluation.
* `output.py` - Formats the array of generated 32-bit words into various text outputs.

## Testing

A comprehensive golden test suite is provided in `tests/test_all_instructions.s`. It exercises every supported instruction, pseudo-instruction, and edge-case (such as negative immediates and backward jumps).

To verify the assembler:
```bash
python scripts/rvasm.py scripts/assembler/tests/test_all_instructions.s -l
```
