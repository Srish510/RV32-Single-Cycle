# RV32I Custom Core & Toolchain

A from-scratch, educational implementation of the RISC-V RV32I Base Integer Instruction Set architecture written in Verilog. *(Based on the [Official RISC-V Instruction Set Manual](https://riscv.org/technical/specifications/))* 

This project goes beyond just the hardware core; it includes a custom-built Python assembler and a robust Python-based verification suite (Cocotb) capable of automated fuzzing and full-system software execution.

## Features
*   **RV32I Core**: Single-cycle Verilog implementation supporting all base arithmetic, logic, branch, jump, and memory instructions.
*   **Custom Assembler**: A two-pass Python assembler (`rvasm`) with macro expansion, address relocation (`%hi/%lo`), and custom directives.
*   **Cocotb Verification**: Deeply integrated Python testbenches featuring exhaustive randomized fuzzing for unit tests, and a "motherboard simulator" for top-level code execution.
*   **One-Click Simulation**: Provided PowerShell and Bash scripts for instantly assembling and running your `.s` files on the simulated CPU.

## Architecture

The core utilizes a unified single-cycle datapath. This means that instruction fetch, decode, execute, memory access, and writeback conceptually resolve in a single clock cycle boundary. 

![RV32I Block Diagram Schematic](docs/RV32I_Block_Diagram.png)

*(You can also [download the high-resolution PDF version here](docs/RV32I%20Block%20Diagram.pdf))*

## Supported Instructions

The core and assembler fully support the following native RV32I instructions:

| Instruction | Type | Opcode (bin) | Opcode (hex) | Funct3 | Funct7 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Arithmetic (R-Type)** | | `0110011` | `0x33` | | |
| `add` / `sub` | R | - | - | `000` | `0000000` / `0100000` |
| `sll` | R | - | - | `001` | `0000000` |
| `slt` | R | - | - | `010` | `0000000` |
| `sltu`| R | - | - | `011` | `0000000` |
| `xor` | R | - | - | `100` | `0000000` |
| `srl` / `sra` | R | - | - | `101` | `0000000` / `0100000` |
| `or`  | R | - | - | `110` | `0000000` |
| `and` | R | - | - | `111` | `0000000` |
| **Immediate (I-Type)** | | `0010011` | `0x13` | | |
| `addi` | I | - | - | `000` | - |
| `slli` | I | - | - | `001` | `0000000` (in `imm[11:5]`) |
| `slti` | I | - | - | `010` | - |
| `sltiu`| I | - | - | `011` | - |
| `xori` | I | - | - | `100` | - |
| `srli` / `srai` | I | - | - | `101` | `0000000` / `0100000` |
| `ori`  | I | - | - | `110` | - |
| `andi` | I | - | - | `111` | - |
| **Loads (I-Type)** | | `0000011` | `0x03` | | |
| `lb` / `lh` / `lw` | I | - | - | `000` / `001` / `010` | - |
| `lbu` / `lhu`      | I | - | - | `100` / `101` | - |
| **Stores (S-Type)** | | `0100011` | `0x23` | | |
| `sb` / `sh` / `sw` | S | - | - | `000` / `001` / `010` | - |
| **Branches (B-Type)**| | `1100011` | `0x63` | | |
| `beq` / `bne`      | B | - | - | `000` / `001` | - |
| `blt` / `bge`      | B | - | - | `100` / `101` | - |
| `bltu` / `bgeu`    | B | - | - | `110` / `111` | - |
| **Jumps (J/I-Type)** | | | | | |
| `jal`  | J | `1101111` | `0x6F` | - | - |
| `jalr` | I | `1100111` | `0x67` | `000` | - |
| **Upper Immediates**| | | | | |
| `lui`  | U | `0110111` | `0x37` | - | - |
| `auipc`| U | `0010111` | `0x17` | - | - |

### Pseudo-Instructions (Macros)
The assembler automatically expands these into 1 or 2 native instructions:
* `nop`, `mv`, `not`, `neg`, `seqz`, `snez`, `sltz`, `sgtz`
* `j`, `jr`, `ret`, `call`, `tail`
* `beqz`, `bnez`, `blez`, `bgez`, `bltz`, `bgtz`
* `li`, `la` (Handles full 32-bit constants/addresses via `%hi/%lo` relocations)

## Quick Start & Simulation

### 1. Prerequisites
*   **Python 3.12+** (with `pip install cocotb cocotb-bus`)
*   **Icarus Verilog (`iverilog`)**
*   **GTKWave** (for viewing waveform dumps)

### 2. Running Unit Tests
The `tb/units/` directory contains exhaustive, randomized fuzz-tests for every individual hardware module (ALU, Branch Unit, Decoder, Register File, etc.).

You can run the entire test suite easily using the custom Python runner:
```bash
python tb/units/run_tests.py
```

Alternatively, if you prefer standard `make` for individual modules:
```bash
cd tb/units
make SIM=icarus TOPLEVEL=alu MODULE=test_alu
```

### 3. Assembling and Running on the Core
You can easily write custom RISC-V assembly and run it on the simulated CPU using the provided helper scripts. 

1. Write your assembly program in `tb/asm/my_program.s`. End it with a spin-loop (`end: j end`) to signal completion to the testbench.
2. Run the helper script from the root of the project:
   * **Windows (PowerShell):** `.\tb\simulate.ps1 my_program`
   * **Linux/macOS:** `./tb/simulate.sh my_program`

The script will automatically compile your code using the custom python assembler, inject the `.hex` binary into the CPU's Instruction Memory, and launch the top-level Cocotb simulation (`tb/top/test_rv32i_top.py`). 

### 4. Viewing Waveforms
When the top-level simulation runs, it automatically records all hardware signals. You can debug your program cycle-by-cycle by opening the generated waveform file:
```bash
gtkwave sim/rv32i_top_full/rv32i_top.fst
```

## Directory Structure

```text
.
├── src/            # Verilog source files
│   ├── core/       # CPU modules (ALU, Decoder, LSU, PC, etc.)
│   ├── mem/        # Memory models (ROM and RAM)
│   └── top/        # Top-level wrapper (rv32i_top.v)
├── tb/             # Cocotb verification and testing
│   ├── asm/        # Your custom assembly test programs
│   ├── hex/        # Generated hex binaries for simulation
│   ├── units/      # Isolated unit tests for individual modules
│   └── top/        # Full-system integration testbench
├── scripts/        # Python utilities
│   └── assembler/  # The custom RV32I assembler source code
├── sim/            # Simulation outputs
└── docs/           # Documentation and guides
```

## Documentation

Explore the `docs/` directory to learn how the CPU and toolchain work:

*   **[Getting Started Guide](docs/getting_started.md)**: Setup dependencies (Icarus Verilog, Cocotb), run tests, and simulate your first assembly program.
*   **[Architecture Overview](docs/architecture.md)**: Details the microarchitecture, datapath components, and control flow of the RV32I core.
*   **[Verification & Testing](docs/verification.md)**: Explains the testbench logic, including randomized unit test fuzzing and the top-level execution environment.
*   **[Toolchain & Assembler](docs/toolchain.md)**: Learn about the custom Python assembler and find links to the assembly Programmer's Reference Manual.
*   **[Official RISC-V Specifications](https://riscv.org/technical/specifications/)**: Download the official unprivileged ISA manual (Volume 1) that defines the behavior of these instructions.

## Next Phases of Development (Roadmap)

This core is currently a fully functional, single-cycle RV32I implementation. The following milestones are planned for future development to harden and extend the design:

1. **Instruction Set Architecture (ISA) Compliance Suite**: Integration with the official `riscv-arch-test` framework to rigorously prove complete RV32I compliance.
2. **Coverage Metrics (Closing the Verification Loop)**: Collecting structural and functional coverage data during testbench execution to ensure no edge cases are missed.
3. **Co-Simulation / Golden Reference Model**: Running tests lockstep against a golden reference emulator (such as Spike or Whisper) to immediately detect execution divergence.
4. **Formal Verification**: Utilizing formal property checking (e.g., SymbiYosys and `rvfi`) to mathematically prove bounded correctness of the control logic.
5. **Static Timing Analysis (STA)**: Evaluating the critical path delay and theoretical maximum frequency capabilities of the datapath.
6. **ISA Extensions & System Features**: Adding support for Multiplication/Division (`M` extension), Floating Point (`F` extension), Control and Status Registers (CSRs), exceptions, and hardware interrupts.
7. **Real Memory Interfacing & MMIO**: Transitioning from simulated backdoor ROMs to physical, synchronous RAM and memory-mapped peripherals.
8. **Memory Controller Interface (AXI4)**: Wrapping the core's native memory interface in the standard AMBA AXI4 protocol for broad ecosystem compatibility.
9. **FPGA Validation**: Synthesizing, implementing, and deploying the core onto physical FPGA development boards.
10. **ASIC Backend Design**: Taking the RTL through a standard cell synthesis, placement, and routing flow.

*(Note: A highly optimized, multi-stage pipelined version of this CPU is also planned and will be developed in a separate repository later).*
