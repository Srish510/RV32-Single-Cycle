# Getting Started

This guide will walk you through setting up your environment, running the verification suite, and writing your first assembly program for the RV32I core.

## 1. Prerequisites

To simulate the CPU and run the testbenches, you will need:
*   **Python 3.12+**
*   **Icarus Verilog (`iverilog`)**: The open-source Verilog simulator.
*   **GTKWave**: For viewing `.fst` or `.vcd` waveform files.
*   **Cocotb**: The Python-based coroutine testbench framework.

You can install Cocotb via pip:
```bash
pip install cocotb cocotb-bus
```

## 2. Running Unit Tests

The `tb/units/` directory contains exhaustive, randomized fuzz-tests for every individual hardware module (ALU, Branch Unit, Decoder, Register File, etc.).

You can run the entire test suite easily using the custom Python runner:
```bash
python tb/units/run_tests.py
```

Alternatively, if you prefer using standard `make` for a specific module (for example, the ALU test):
```bash
cd tb/units
make SIM=icarus TOPLEVEL=alu MODULE=test_alu
```
*(Cocotb will launch Icarus Verilog in the background, run thousands of randomized inputs against the module, and report pass/fail).*

## 3. Writing and Running Assembly

The easiest way to write a program and see it execute on the full CPU simulation is to use the provided helper scripts.

1.  Create a new assembly file in the `tb/asm/` directory (e.g., `tb/asm/hello.s`).
2.  Write your RISC-V assembly. To signal to the testbench that your program is finished, end your code with an infinite loop:
    ```assembly
    # tb/asm/hello.s
    .text
    .org 0x0000

    main:
        li a0, 42       # Load 42 into a0
        sw a0, 0(sp)    # Store it to memory

    end:
        j end           # Testbench detects this spin-loop and stops!
    ```
3.  Run the helper script from the project root.
    *   **Windows (PowerShell):** `.\tb\simulate.ps1 hello`
    *   **Linux/macOS (Bash):** `./tb/simulate.sh hello`

The helper script will automatically:
1.  Assemble your code to `tb/hex/hello.hex`.
2.  Inject it into the Instruction Memory of the CPU.
3.  Boot the Cocotb top-level simulation (`tb/top/test_rv32i_top.py`).
4.  Monitor execution until it detects the spin-loop and prints "Test Passed!".

## 4. Viewing Waveforms

Whenever you run the top-level simulation, it automatically records all hardware signals into a waveform file located at:
`sim/rv32i_top_full/rv32i_top.fst`

You can open this file in GTKWave to debug your program cycle-by-cycle:
```bash
gtkwave sim/rv32i_top_full/rv32i_top.fst
```
