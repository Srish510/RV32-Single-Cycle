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
