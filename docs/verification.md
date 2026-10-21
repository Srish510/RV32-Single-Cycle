# Verification & Testing Strategy

This project exclusively uses **[Cocotb](https://docs.cocotb.org/)** (Coroutine based Co-simulation Testbench) and Python for hardware verification, completely avoiding traditional SystemVerilog or Verilog testbenches.

This allows us to leverage the massive Python ecosystem to perform complex randomized testing, parse hex files, and orchestrate the top-level simulation using standard programming paradigms.

## 1. Unit Tests (Isolated Fuzzing)
**Location:** `tb/units/`

Every core component (ALU, Branch Unit, Main Decoder, Register File, LSU, etc.) has its own isolated unit test suite.

Instead of hardcoding a few "select values" to test, we use **Exhaustive Randomized Fuzzing**. For example, in `test_alu.py` and `test_branch_unit.py`, the Python testbench:
1. Spawns an isolated coroutine for every distinct operation (e.g., a specific test for `ADD`, a specific test for `XOR`).
2. Generates thousands of randomized 32-bit integers, alongside intentional edge cases (like `0`, `0xFFFFFFFF`, `0x80000000`).
3. Drives these values into the Verilog module.
4. Computes the *expected result* purely in Python using native operators.
5. Asserts that the Verilog hardware output matches the Python calculation exactly.

This approach guarantees extremely high coverage across tens of thousands of dynamic assertions per test run.

## 2. Full-System Integration (Top-Level)
**Location:** `tb/top/test_rv32i_top.py`

The top-level testbench simulates the complete environment (acting like a virtual motherboard). When you run a simulation, the testbench orchestrates the following lifecycle:

### A. Clock Generation & Reset
The testbench starts a background coroutine that constantly toggles the `clk` signal every 10ns to simulate a free-running oscillator. It asserts the `rst` line high for 5 clock cycles to flush the pipeline and initialize all registers, then drops it low to begin CPU execution at `PC = 0x00000000`.

### B. Memory Backdoor Injection
Before the reset is even released, the testbench reads the compiled `.hex` machine code file specified by the `$PROG_HEX` environment variable. Instead of relying on a complex bootloader, it uses a "backdoor write" to directly flash the raw binary integers into the `imem_inst` (Instruction ROM) array via the Cocotb hierarchy (`dut.imem_inst.memory[idx].value`).

### C. Program Completion Detection
Because this is a bare-metal core without operating system syscalls, exceptions, or `FENCE` instructions, the CPU has no native concept of "exiting". The testbench must determine when the program has successfully finished executing. 

It does this by monitoring the CPU signals on every clock edge for two specific conditions:

1. **The Spin-Loop:** If the testbench detects that the Program Counter is no longer changing (`PC == Next_PC`), it assumes the program has intentionally halted (e.g., executing a `end: j end` loop).
2. **The `tohost` Write:** A standard technique used in official RISC-V compliance tests. If the CPU performs a data memory write to the magic address `0x80001000` (the `tohost` interface), the testbench intercepts it. If the CPU writes a `1`, the test is considered a PASS. If it writes anything > `1`, it is considered a specific error code.

If neither condition is met after 100,000 cycles, the testbench forces a timeout failure.

## 3. RISC-V Architectural Compliance Testing

In addition to randomized unit fuzzing and custom assembly simulations, this core has been formally validated against the official **[RISC-V Architectural Test Suite](https://github.com/riscv/riscv-arch-test)** (`riscv-arch-test`).

### A. Compliance Scope & Microarchitectural Considerations

The CPU implements the unprivileged **RV32I Base Integer Instruction Set**. As a lean, educational single-cycle design, certain features are intentionally not implemented:
* **Privileged Modes & System Traps (`ecall`, `ebreak`)**: The core operates purely in user mode without trap handlers, CSR registers, or privilege switches.
* **Memory Ordering (`fence`)**: Because instructions and memory accesses complete deterministically in a single clock cycle, out-of-order memory effects do not exist, rendering `fence` unnecessary. The `fence-01.S` test is therefore excluded from the test matrix.

### B. Target Environment & Test Termination (`tohost`)

Official compliance tests typically invoke the host environment using `ecall` or memory-mapped control registers. To support this cleanly on a bare-metal core:

1. **Target Environment Directory (`compliance/`)**:
   - `compliance/rv32i_core/env/model_test.h`: Defines the test framework macros. The test halt macro (`RVMODEL_HALT`) writes `1` to the `.tohost` section address and spins in a tight loop:
     ```assembly
     #define RVMODEL_HALT \
       li x1, 1; \
       write_tohost: \
         sw x1, tohost, t5; \
         j write_tohost;
     ```
   - `compliance/rv32i_core/env/link.ld`: The linker script aligns code and data starting at address `0x00000000` to match the CPU reset vector (`PC = 0x00000000`), placing `.tohost` at `0x00001000`.
   - `compliance/rv32i_core/rv32i_core_isa.yaml`: Defines architectural parameters (`XLEN=32`, `I` extension).
   - `compliance/config.ini`: RISCOF configuration referencing `rv32i_core` and `sail_cSim` plugins.

2. **ELF Loading & Backdoor Injection**:
   - Tests are compiled directly from assembly using `riscv64-unknown-elf-gcc` into ELF binaries (`-march=rv32i -mabi=ilp32`).
   - The testbench uses `pyelftools` to inspect ELF program segments (`PT_LOAD`) and the `.symtab` symbol table. It dynamically extracts the address of the `tohost` symbol and initializes the CPU's instruction and data memories.

3. **Pass / Fail Determination**:
   - The testbench monitors the CPU data memory interface (`data_we`, `data_addr`, `data_wdata`).
   - When a write occurs to the `tohost` address:
     - `wdata == 1`: **PASS** (the test passed all internal assertions).
     - `wdata > 1`: **FAIL** (indicates the failure code corresponding to the failed test case).
   - If an infinite spin loop occurs without a `tohost` write, `x3` (`gp`) register state is inspected.

### C. Test Results (37 / 37 PASSED - 100% Compliant)

All 37 applicable base integer instruction tests pass:

| Category | Instructions Tested | Status |
| :--- | :--- | :---: |
| **Arithmetic (R-Type)** | `add`, `sub`, `sll`, `slt`, `sltu`, `xor`, `srl`, `sra`, `or`, `and` | **PASS (10/10)** |
| **Immediate (I-Type)** | `addi`, `slli`, `slti`, `sltiu`, `xori`, `srli`, `srai`, `ori`, `andi` | **PASS (9/9)** |
| **Branches (B-Type)** | `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu` | **PASS (6/6)** |
| **Jumps (J/I-Type)** | `jal`, `jalr` | **PASS (2/2)** |
| **Memory Loads** | `lb`, `lbu`, `lh`, `lhu`, `lw` | **PASS (5/5)** |
| **Memory Stores** | `sb`, `sh`, `sw` | **PASS (3/3)** |
| **Upper Immediates** | `lui`, `auipc` | **PASS (2/2)** |
| **Total** | **All Base RV32I Instructions** | **37 / 37 (100%)** |

## Running the Tests

To run the unit tests:
```bash
python tb/units/run_tests.py
```

To run the top-level integration test with a custom program:
```bash
# Windows
.\tb\simulate.ps1 my_program

# Linux / macOS
./tb/simulate.sh my_program
```

To run the complete RISC-V Architectural Compliance suite:
```bash
# Windows (PowerShell)
.\tb\run_compliance.ps1

# Linux / macOS (Bash)
./tb/run_compliance.sh
```
