# RV32I Programmer's Reference Guide

This guide details everything a programmer needs to know to write assembly code for this custom RV32I assembler, including syntax, supported instructions, registers, macros, and directives.

---

## 1. Registers

The assembler supports both standard hardware register names (`x0`–`x31`) and standard RISC-V ABI aliases.

| Register | ABI Name | Description | Saver |
| :--- | :--- | :--- | :--- |
| `x0` | `zero` | Hardwired zero | — |
| `x1` | `ra` | Return address | Caller |
| `x2` | `sp` | Stack pointer | Callee |
| `x3` | `gp` | Global pointer | — |
| `x4` | `tp` | Thread pointer | — |
| `x5`–`x7` | `t0`–`t2` | Temporary registers | Caller |
| `x8` | `s0` / `fp` | Saved register / Frame pointer | Callee |
| `x9` | `s1` | Saved register | Callee |
| `x10`–`x11` | `a0`–`a1` | Function arguments / Return values | Caller |
| `x12`–`x17` | `a2`–`a7` | Function arguments | Caller |
| `x18`–`x27` | `s2`–`s11` | Saved registers | Callee |
| `x28`–`x31` | `t3`–`t6` | Temporary registers | Caller |

---

## 2. Base Instruction Set (RV32I)

### R-Type (Register-Register ALU)
**Syntax:** `mnemonic rd, rs1, rs2`
* `add`, `sub` (Addition / Subtraction)
* `and`, `or`, `xor` (Bitwise logic)
* `sll`, `srl`, `sra` (Shift left logical, shift right logical, shift right arithmetic)
* `slt`, `sltu` (Set less than, Set less than unsigned)

**Examples:**
```assembly
add t0, a0, a1   # t0 = a0 + a1
sub t1, t0, a2   # t1 = t0 - a2
and s0, s1, s2   # s0 = s1 & s2
sll a0, a0, a1   # a0 = a0 << (a1 & 0x1F)
slt t0, a0, a1   # t0 = (a0 < a1) ? 1 : 0 (signed comparison)
```

### I-Type (Register-Immediate ALU)
**Syntax:** `mnemonic rd, rs1, imm`
* `addi` (Add immediate)
* `andi`, `ori`, `xori` (Bitwise logic immediate)
* `slti`, `sltiu` (Set less than immediate)
* `slli`, `srli`, `srai` (Shift immediate — immediate must be $0 \le \text{imm} \le 31$)

**Examples:**
```assembly
addi sp, sp, -16  # sp = sp - 16 (allocate 16 bytes on stack)
andi a0, a0, 0xFF # a0 = a0 & 255 (mask lower 8 bits)
slli t0, t1, 4    # t0 = t1 << 4 (logical shift left by 4)
```

### Memory Loads & Stores
**Syntax:** `mnemonic rd_or_rs2, offset(rs1)`
* **Loads:** `lb` (byte), `lh` (halfword), `lw` (word), `lbu` (byte unsigned), `lhu` (halfword unsigned)
* **Stores:** `sb` (byte), `sh` (halfword), `sw` (word)

**Examples:**
```assembly
lw  a0, 0(sp)    # Load a 32-bit word from memory at address (sp + 0) into a0
lh  t0, 4(a1)    # Load a 16-bit halfword from (a1 + 4), sign-extend into t0
lbu t1, 5(a1)    # Load an 8-bit byte from (a1 + 5), zero-extend into t1
sw  a0, 12(sp)   # Store the 32-bit word in a0 into memory at (sp + 12)
sb  zero, 0(t0)  # Store an 8-bit zero byte into memory at address in t0
```

### Branches
**Syntax:** `mnemonic rs1, rs2, label` *(offset is calculated automatically)*
* `beq`, `bne` (Branch equal, not equal)
* `blt`, `bge` (Branch less than, greater than or equal — signed)
* `bltu`, `bgeu` (Branch less than, greater than or equal — unsigned)

**Examples:**
```assembly
beq  a0, a1, done   # If a0 == a1, jump to label 'done'
bne  t0, zero, loop # If t0 != 0, jump to label 'loop'
bltu a0, a1, skip   # If a0 < a1 (unsigned comparison), jump to label 'skip'
```

### Jumps
* `jal rd, label` (Jump and link. If `rd` is omitted, defaults to `ra` / `x1`)
* `jalr rd, rs1, imm` or `jalr rd, offset(rs1)` (Jump and link register. `rd` defaults to `ra`, `imm` defaults to `0`)

**Examples:**
```assembly
jal  ra, my_func    # Jump to my_func, save return address in 'ra'
jal  zero, loop     # Jump to loop, discard return address (equivalent to 'j loop')
jalr ra, a0, 0      # Jump to address in a0, save return address in 'ra'
jalr zero, ra, 0    # Jump to address in ra, discard return address (equivalent to 'ret')
```

### U-Type (Upper Immediates)
**Syntax:** `mnemonic rd, imm` *(immediate is a 20-bit value)*
* `lui` (Load upper immediate)
* `auipc` (Add upper immediate to PC)

**Examples:**
```assembly
lui   a0, 0x12345   # Load 0x12345000 into a0 (shifts 0x12345 left by 12)
auipc t0, 0         # t0 = PC (useful for reading the current Program Counter)
auipc a1, 0x10      # a1 = PC + 0x10000
```

---

## 3. Pseudo-Instructions (Macros)

The assembler provides high-level macros that automatically expand into 1 or 2 native instructions.

| Pseudo-Instruction | Native Expansion | Purpose |
| :--- | :--- | :--- |
| `nop` | `addi x0, x0, 0` | Do nothing |
| `mv rd, rs` | `addi rd, rs, 0` | Copy register |
| `not rd, rs` | `xori rd, rs, -1` | Bitwise inversion |
| `neg rd, rs` | `sub rd, x0, rs` | Two's complement negation |
| `seqz rd, rs` | `sltiu rd, rs, 1` | Set to 1 if `rs == 0` |
| `snez rd, rs` | `sltu rd, x0, rs` | Set to 1 if `rs != 0` |
| `sltz rd, rs` | `slt rd, rs, x0` | Set to 1 if `rs < 0` |
| `sgtz rd, rs` | `slt rd, x0, rs` | Set to 1 if `rs > 0` |
| `j label` | `jal x0, label` | Unconditional jump |
| `jr rs` | `jalr x0, rs, 0` | Jump register |
| `ret` | `jalr x0, ra, 0` | Return from function |
| `beqz rs, label` | `beq rs, x0, label` | Branch if equal to zero |
| `bnez rs, label` | `bne rs, x0, label` | Branch if not equal to zero |
| `blez rs, label` | `bge x0, rs, label` | Branch if less than or equal to zero |
| `bgez rs, label` | `bge rs, x0, label` | Branch if greater than or equal to zero |
| `bltz rs, label` | `blt rs, x0, label` | Branch if less than zero |
| `bgtz rs, label` | `blt x0, rs, label` | Branch if greater than zero |

### Large Constants and Addresses (Multi-Instruction Macros)
* `li rd, imm`: Loads a 32-bit constant. If `imm` fits in 12 bits, expands to `addi`. Otherwise, expands to `lui` + `addi`.
* `la rd, symbol`: Loads the 32-bit address of a symbol using PC-relative addressing (`auipc` + `addi`).
* `call symbol`: Jumps to a function anywhere in the 32-bit address space, linking the return address (`auipc ra, %hi` + `jalr ra, ra, %lo`).
* `tail symbol`: Jumps to a function anywhere without modifying the return address (`auipc t1, %hi` + `jalr x0, t1, %lo`).

**Examples:**
```assembly
li   a0, 42         # Expands to: addi a0, zero, 42
li   a1, 0x12345678 # Expands to: lui a1, 0x12345; addi a1, a1, 0x678
la   a0, my_string  # Expands to: auipc a0, %hi(my_string); addi a0, a0, %lo(my_string)
call my_func        # Expands to: auipc ra, %hi(my_func); jalr ra, ra, %lo(my_func)
```

---

## 4. Relocations

You can extract the upper 20 bits or lower 12 bits of a 32-bit symbol or number directly in your operands:
* `%hi(symbol)`: Extracts bits `[31:12]`. Automatically adds `1` if the lower 12 bits form a negative number (to compensate for `addi` sign-extension).
* `%lo(symbol)`: Extracts bits `[11:0]`.

Example: Loading an absolute 32-bit address manually:
```assembly
lui  a0, %hi(my_data)
addi a0, a0, %lo(my_data)
```

---

## 5. Directives

Directives control the assembler's behavior, layout, and memory generation.

| Directive | Arguments | Description |
| :--- | :--- | :--- |
| `.org` | `address` | Sets the internal Program Counter (PC) to `address`. |
| `.word` | `val1, val2...` | Emits one or more 32-bit words into memory. |
| `.half` | `val1, val2...` | Emits one or more 16-bit halfwords into memory. |
| `.byte` | `val1, val2...` | Emits one or more 8-bit bytes into memory. |
| `.zero` | `bytes` | Emits `bytes` number of zero-bytes to pad memory. |
| `.align` | `power` | Aligns the PC to a boundary of $2^{\text{power}}$ bytes. |
| `.equ` / `.set`| `name, value` | Creates a constant symbol `name` with `value`. |
| `.text` / `.data`| *None* | Informational flags (ignored by this flat assembler). |
| `.globl` | `symbol` | Informational flag (ignored by this flat assembler). |

**Examples:**
```assembly
.org 0x1000         # The next instruction will be placed at 0x1000
.word 0xDEADBEEF    # Emit the 32-bit constant 0xDEADBEEF directly into memory
.align 2            # Align the PC to a 4-byte boundary (2^2)
.equ MAX_SIZE, 256  # Define a constant 'MAX_SIZE' equal to 256
addi a0, zero, MAX_SIZE # Uses the constant above
```

---

## 6. Literals and Comments

**Constants** can be written in three formats:
* Decimal: `42`, `-100`
* Hexadecimal: `0xFF`, `0x1234abcd`
* Binary: `0b1010`

**Comments** are supported using `#`, `;`, or `//`. Anything after these symbols on a line is ignored.
