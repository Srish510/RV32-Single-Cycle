# RV32I Assembler Module Documentation

This document provides a deep dive into the internal architecture of the RV32I assembler. It details the responsibilities of each module, the primary data structures, and the public methods used to transform raw assembly text into 32-bit machine code.

---

## 1. `assembler.py` (Core Engine)

The orchestrator of the assembly process. It implements a two-pass architecture to resolve forward and backward label references.

### Classes & Methods
* **`class Assembler(base_addr: int = 0)`**
  Maintains the state of the assembly process, including the symbol table (`self.labels`), intermediate parsed instructions, and error logs.
  * **`assemble(source: str) -> List[int]`**: The primary entry point. Takes raw assembly string, runs Pass 1, then Pass 2, and returns a list of 32-bit integers representing machine code words.
  * **`_pass1(lines: List[str])`**: Iterates over all text lines, tracking the `pc` (Program Counter). It populates the symbol table with label addresses and evaluates assembler directives (`.org`, `.word`, `.align`).
  * **`_pass2() -> List[int]`**: Uses the completed symbol table to translate the parsed instructions into machine code using `assemble_instruction`. It builds a contiguous memory map and pads skipped memory regions with zeros.

* **`assemble_file(input_path: str, output_path: str, base_addr: int, annotated: bool)`**
  A high-level helper function that reads a `.s` file, instantiates the `Assembler`, checks for errors, and writes the output directly to a `.hex` file.

---

## 2. `parser.py` (Tokenizer)

Responsible for the initial lexical analysis of the source code.

### Methods
* **`tokenize_line(line: str) -> Tuple[Optional[str], Optional[str], List[str]]`**
  Takes a raw string line and strips all comments (`#`, `;`, `//`). It then splits the text into:
  1. `label` (e.g., `"loop"` if the line is `loop: add x1, x2, x3`)
  2. `mnemonic` (e.g., `"add"`)
  3. `operands` (e.g., `["x1", "x2", "x3"]`). It uses a specific regex (`r',\s*(?![^()]*\))'`) to split by commas *unless* the comma is inside parentheses, which preserves memory addressing like `0(a0)`.

---

## 3. `instructions.py` (Dispatcher)

Validates operands and dispatches them to the correct binary encoder based on the instruction type.

### Methods
* **`assemble_instruction(mnemonic: str, operands: List[str], labels: Dict[str, int], pc: int) -> List[int]`**
  1. Tries to expand the mnemonic using `try_pseudo()`. If successful, it returns the expanded words.
  2. Otherwise, identifies the instruction type (R, I, Load, Store, Branch, JAL, U).
  3. Parses the registers and immediate values (enforcing range checks).
  4. Calls the relevant encoding function in `encoding.py`.
* **`parse_mem_operand(operand: str) -> Tuple[str, str]`**
  Extracts the offset and base register from a memory operand string. E.g., `"8(sp)"` -> `("8", "sp")`.

---

## 4. `pseudo.py` (Macro Expansion)

Translates high-level pseudo-instructions into one or more native RV32I instructions.

### Methods
* **`try_pseudo(mn: str, operands: List[str], labels: Dict[str, int], pc: int) -> Optional[List[int]]`**
  Returns a list of 32-bit encoded words if `mn` is a pseudo-instruction, or `None` if it is a standard native instruction.
  * *Notable Expansions:*
    * `li rd, imm`: Expands to `addi` if the immediate fits in 12 bits. Otherwise, expands to `lui` + `addi` to load a 32-bit constant.
    * `call` / `tail`: Expands to `auipc` + `jalr` to allow PC-relative function calls anywhere within a $\pm$ 2GB range.
    * `j label`: Expands to `jal x0, offset`.
    * `bnez rs1, label`: Expands to `bne rs1, x0, offset`.

---

## 5. `encoding.py` (Binary Packers)

Performs low-level bitwise operations to pack arguments into 32-bit hardware instruction formats.

### Methods
* **`encode_r_type(rd, rs1, rs2, funct3, funct7)`**: Packs standard ALU ops.
* **`encode_i_type(rd, rs1, imm, funct3, opcode)`**: Packs immediates into bits `[31:20]`.
* **`encode_s_type(rs1, rs2, imm, funct3)`**: Stores split their immediate into bits `[31:25]` and `[11:7]`.
* **`encode_b_type(rs1, rs2, imm, funct3)`**: Branches require complex immediate swizzling to match hardware wiring. Bits are scrambled into `imm[12|10:5|4:1|11]`.
* **`encode_u_type(rd, imm, opcode)`**: Shifts a 20-bit immediate into bits `[31:12]`.
* **`encode_j_type(rd, imm)`**: Jump targets are scrambled into `imm[20|10:1|11|19:12]`.

---

## 6. `utils.py` (Math & Resolvers)

Provides arbitrary-precision conversion and symbol evaluations.

### Methods
* **`to_unsigned(val: int, bits: int) -> int`**
  Masks a Python integer to extract exactly `bits` width, stripping off Python's infinite sign-extension bits for negative numbers.
* **`sign_extend(val: int, bits: int) -> int`**
  Reads a binary bit pattern of length `bits`. If the MSB is set, it converts the pattern back into a native negative Python integer.
* **`check_range(val, bits, signed)`**
  Validates that an immediate value doesn't overflow its hardware bit field (e.g., testing if an I-type immediate is within `[-2048, 2047]`).
* **`parse_imm(token, labels, pc, relative) -> int`**
  The most complex utility. It:
  1. Resolves labels (e.g., `"loop"` -> `0x40`).
  2. Parses numeric literals (`0x`, `0b`, decimal).
  3. Resolves `%hi()` and `%lo()` relocations. For `%hi`, if the lower 12 bits are negative, it automatically adds `1` to the upper 20 bits to compensate for the sign-extension that will occur in the subsequent `addi` instruction.
  4. Subtracts the `pc` if the `relative` flag is True (used for branch/jump offsets).

---

## 7. `registers.py` & `opcodes.py` (Constants)

Data-only modules defining the RISC-V specification parameters.

* **`registers.py`**:
  * `REG_MAP`: Maps string names (`"x1"`, `"ra"`) to integer indices (`1`).
  * `parse_reg(token)`: Cleans a token and looks it up in `REG_MAP`.
* **`opcodes.py`**:
  * Defines bit constants like `OP_R_TYPE = 0b0110011`.
  * `FUNCT3` / `FUNCT7` dictionaries: Maps mnemonics (`"add"`) to their specific hardware function codes.
  * Sets like `R_TYPE_INSTRS`: Used by `instructions.py` to quickly determine an instruction's format category.

---

## 8. `output.py` (Formatters)

Formats an array of 32-bit integers into text output.

### Methods
* **`to_hex_file(words, base_addr)`**: Outputs raw 8-character hex strings per line (perfect for Verilog `$readmemh`).
* **`to_annotated_hex(words, base_addr)`**: Outputs hex strings with inline C-style comments showing the memory address and word offset.
* **`to_binary_listing(words, base_addr)`**: Outputs a debug view showing the address, hex value, and the full 32-bit binary string (`10110011...`).
