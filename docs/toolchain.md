# Toolchain & Assembler

To write programs for this RV32I core, we have built a custom, Python-based, two-pass assembler from scratch.

Because standard GCC toolchains (`riscv64-unknown-elf-gcc`) produce highly complex ELF binaries that require loaders, linker scripts, and C-runtime (`crt0`) initialization, a custom assembler was created to generate pure, lightweight `.hex` files. These hex files can be directly loaded into our Verilog simulation using the `$readmemh` system task.

## Assembler Features
*   **Two-Pass Design:** Fully supports forward and backward label jumps.
*   **Pseudo-instructions:** Automatically expands macros like `li`, `la`, `j`, `ret`, `mv`, and `call` into 1 or 2 native RV32I instructions.
*   **Directives:** Supports standard memory layout directives (`.word`, `.align`, `.org`, etc.).
*   **Address Relocations:** Supports `%hi(symbol)` and `%lo(symbol)` modifiers, including automatic sign-extension compensation for 32-bit addresses.

## Documentation

The complete documentation for the Assembler lives alongside its source code in the `scripts/assembler` directory:

1.  **[Assembler README](../scripts/assembler/README.md)**: High-level overview of the assembler.
2.  **[Programmer's Reference Guide](../scripts/assembler/REFERENCE.md)**: The "User Manual" for writing assembly. It includes the syntax for every supported instruction, memory addressing, registers, macros, and directives.
3.  **[Internal Module Docs](../scripts/assembler/MODULE_DOCS.md)**: Documentation on the internal Python architecture (`parser.py`, `assembler.py`, `encoding.py`, etc.) if you wish to modify the assembler source code.

## Quick Usage

You can assemble a program from the root directory using the `rvasm.py` wrapper script:

```bash
# Basic Assembly
python scripts/rvasm.py my_program.s -o my_program.hex

# Assembly with an address-annotated debug output
python scripts/rvasm.py my_program.s -o my_program.hex -a

# Print binary/hex listing to the terminal
python scripts/rvasm.py my_program.s -l
```
