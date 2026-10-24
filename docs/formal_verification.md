# Formal Verification (SymbiYosys + Yosys-SMTBMC + RVFI)

In addition to randomized Cocotb unit fuzzing, the 37-test RISC-V Architectural Compliance Suite, 100% functional/branch coverage closure, and lockstep Golden ISS co-simulation, this core is mathematically verified using **Formal Property Checking**.

While dynamic simulation verifies only the specific input vectors driven during a test run, **Formal Verification** uses **SMT (Satisfiability Modulo Theories) Bit-Vector Solvers** (`Z3`, `Yices2`, `Bitwuzla`, `Boolector`) to exhaustively prove that architectural invariants hold across **100% of the state and input space** ($2^{32}$ instruction words and $2^{64}$ operand combinations).

All RTL and formal verification harnesses are written strictly in **pure IEEE 1364-2005 Verilog (`.v`)**.

---

## 1. Formal Verification Architecture

The formal verification suite is organized under `formal/` and `tb/`:

```text
formal/
├── rvfi/
│   └── rv32i_rvfi_wrapper.v       # Non-invasive RISC-V Formal Interface (RVFI) wrapper (.v)
├── properties/
│   ├── formal_decoder.v           # Exhaustive Main Decoder & Immediate Generator formal proofs (.v)
│   ├── formal_alu.v               # Exhaustive 32-bit ALU arithmetic, shift & overflow proofs (.v)
│   ├── formal_lsu.v               # Exhaustive Load-Store Unit & byte-enable mask proofs (.v)
│   ├── formal_branch_pc.v         # Exhaustive PC Controller, Branch Unit & JALR LSB proofs (.v)
│   └── formal_rvfi_core.v         # Full Core sequential invariants + 37-Instruction RVFI ISA contract (.v)
└── sby/
    ├── decoder.sby                # SymbiYosys config (bmc, prove, cover)
    ├── alu.sby                    # SymbiYosys config (bmc, prove, cover)
    ├── lsu.sby                    # SymbiYosys config (bmc, prove, cover)
    ├── branch_pc.sby              # SymbiYosys config (bmc, prove, cover)
    └── rvfi_core.sby              # SymbiYosys config (bmc, prove, cover)
```

### Non-Invasive RVFI Bridge via Yosys `expose`
To verify the unmodified [`src/core/rv32i_core.v`](../src/core/rv32i_core.v) without adding debug ports to production RTL, the SymbiYosys synthesis script executes Yosys's native `expose` pass:
```tcl
expose rv32i_core/next_pc rv32i_core/reg_write rv32i_core/write_data rv32i_core/read_data1 rv32i_core/read_data2
```
This dynamically exposes the internal combinational datapath wires to [`formal/rvfi/rv32i_rvfi_wrapper.v`](../formal/rvfi/rv32i_rvfi_wrapper.v), which constructs the industry-standard **RISC-V Formal Interface (`rvfi_*`)** retirement packet on every clock edge.

---

## 2. Formal Proof Methods

Every formal target is verified across three complementary SymbiYosys tasks:

1. **Bounded Model Checking (`bmc`)**:
   - Unrolls the circuit across $k$ clock cycles starting from initial reset and uses the SMT solver to search for any sequence of symbolic inputs (`$anyseq`) that violates an `assert(...)` statement.
2. **Unbounded Temporal $k$-Induction (`prove`)**:
   - **Base Case**: Proves no assertion fails in the first $k$ cycles from reset.
   - **Induction Step**: Assumes all properties hold for $k$ consecutive cycles starting from an *arbitrary reachable or unreachable state*, and proves they must also hold in cycle $k+1$. A passing $k$-induction proof mathematically guarantees correctness across **infinite clock cycles** ($\forall t \in [0, \infty)$).
3. **Reachability & Witness Generation (`cover`)**:
   - Proves that the formal constraints (`assume`) are non-vacuous (not over-constrained) by synthesizing concrete input stimuli and dumping `.vcd` waveform traces for every `cover(...)` target.

---

## 3. Mathematically Proven Properties (276 Assertions, 32 Witness Covers)

| # | Formal Target | Top Module | BMC | Prove ($k$-Ind) | Cover | Proven Assertions | Witness Covers | Scope |
| :- | :--- | :--- | :-: | :-: | :-: | :-: | :-: | :--- |
| **1** | **`decoder`** | [`formal_decoder`](../formal/properties/formal_decoder.v) | **PASS** | **PASS** | **PASS** | **72** | **10** | All $2^{32}$ instruction encodings across `main_decoder` & `immediate_gen` |
| **2** | **`alu`** | [`formal_alu`](../formal/properties/formal_alu.v) | **PASS** | **PASS** | **PASS** | **40** | **5** | All $2^{68}$ `(a, b, alu_op)` vectors across `alu` |
| **3** | **`lsu`** | [`formal_lsu`](../formal/properties/formal_lsu.v) | **PASS** | **PASS** | **PASS** | **41** | **6** | All load/store modes, alignments & byte masks in `lsu` |
| **4** | **`branch_pc`** | [`formal_branch_pc`](../formal/properties/formal_branch_pc.v) | **PASS** | **PASS** | **PASS** | **17** | **6** | All control-flow muxing, branch flags & `JALR` LSB masking |
| **5** | **`rvfi_core`** | [`formal_rvfi_core`](../formal/properties/formal_rvfi_core.v) | **PASS** | **PASS** | **PASS** | **106** | **5** | Full sequential `rv32i_core` + all 37 RV32I ISA contracts |
| | **Total** | **All 5 Formal Suites** | **5/5 PASS** | **5/5 PASS** | **5/5 PASS** | **276** | **32** | **100% Formal Property Closure** |

### Detailed Invariant Breakdown

#### A. Main Decoder & Immediate Generator (`formal_decoder.v`)
- **Mutual Exclusion**: Load and store LSU opcodes are mutually exclusive; stores and branches never assert `reg_write`.
- **Control Flow Bi-Implications**: `PC_SEL_BRANCH`, `PC_SEL_JAL`, and `PC_SEL_JALR` are asserted *if and only if* the opcode is `BRANCH`, `JAL`, or `JALR` respectively.
- **Writeback Isolation**: `WB_SEL_MEM` $\iff$ `LOAD`; `WB_SEL_UPP_IMM` $\iff$ `LUI`; `PC_WB_SEL_OFFSET` $\iff$ `AUIPC`.
- **Illegal Opcode Safe-NOP Fallback**: Any unimplemented or illegal opcode (including `ECALL`/`EBREAK` `0x73`, `FENCE` `0x0F`, and all reserved opcodes) strictly deasserts `reg_write == 0`, `lsu_op == LSU_NONE`, `next_pc_src == PC_SEL_INC`, and `branch_op == BRANCH_NONE`.
- **Immediate Sign-Extension**: Proves exact sign-bit replication and LSB alignment (`imm[0] == 0` for B/J types, `imm[11:0] == 0` for U-type).

#### B. 32-Bit Arithmetic Logic Unit (`formal_alu.v`)
- **Universal Zero Flag Bi-Implication**: `zero <==> (alu_result == 32'h0000_0000)`.
- **Two's Complement Signed Overflow Theorems**:
  - Addition (`ALU_ADD`): `overflow <==> ((a[31] == b[31]) && (alu_result[31] != a[31]))`.
  - Subtraction (`ALU_SUB`): `overflow <==> ((a[31] != b[31]) && (alu_result[31] != a[31]))`.
- **Shift Invariants**: `SRA` preserves `a[31]`; shifting `0xFFFFFFFF` by any `b[4:0]` via `SRA` yields `0xFFFFFFFF`; `SRL` by non-zero `shamt` clears bit 31.
- **Comparison Exactness**: `SLT` and `SLTU` zero-extend bit 0 (`alu_result[31:1] == 0`) and satisfy strict irreflexivity (`a == b ==> alu_result == 0`).

#### C. Load-Store Unit (`formal_lsu.v`)
- **Read/Write Mutual Exclusion**: `!(mem_re && (|mem_we))` across all inputs.
- **Byte-Enable Mask Legality**: `mem_we` is strictly restricted to `{4'b0000, 4'b0001, 4'b0010, 4'b0100, 4'b1000, 4'b0011, 4'b1100, 4'b1111}` — fragmented masks (e.g., `4'b0101` or `4'b1001`) are impossible.
- **Sign & Zero Extension**: Proves upper 24/16 bits are sign-replicated for `LB`/`LH` and zeroed for `LBU`/`LHU`.

#### D. PC Controller & Branch Unit (`formal_branch_pc.v`)
- **`JALR` Target LSB Clearing**: Proves `next_pc[0] == 1'b0` whenever `next_pc_src == PC_SEL_JALR`, regardless of `jalr_pc[0]`.
- **4-Byte Alignment Preservation**: If `pc[1:0] == 2'b00` and `offset[1:0] == 2'b00` (and `jalr_pc[1] == 0` for `JALR`), then `next_pc[1:0] == 2'b00`.

#### E. End-to-End Sequential Core & RVFI ISA Contract (`formal_rvfi_core.v`)
- **Reset Determinism**: Asserting `rst` drives `pc_out == 32'h0000_0000`, `rvfi_valid == 0`, and `rvfi_order == 0`.
- **PC Sequential Continuity**: On every active cycle, `instr_addr == rvfi_pc_wdata` and `rvfi_pc_rdata == $past(instr_addr)`.
- **`x0` Hardwired-Zero Invariance**: Reading `rs1 == 0` or `rs2 == 0` always yields `0`, and `rvfi_rd_wdata == 0` whenever `rvfi_rd_addr == 0`, even after arbitrary instructions targeting `rd = x0`.
- **Register File Read-After-Write (RAW) & Frame Non-Interference**:
  - Writing to register $R \neq 0$ in cycle $t-1$ and reading $R$ in cycle $t$ returns `rvfi_rd_wdata`.
  - Any register $R$ not targeted by `rvfi_rd_addr` in cycle $t-1$ strictly retains its previous value (`comb_rs1_rdata == $past(comb_rs1_rdata)`), proving absence of unintended register clobbering.
- **Complete 37-Instruction RVFI Specification**: Proves that every retired RV32I instruction (`LUI`, `AUIPC`, `JAL`, `JALR`, `BEQ`, `BNE`, `BLT`, `BGE`, `BLTU`, `BGEU`, `LB`, `LH`, `LW`, `LBU`, `LHU`, `SB`, `SH`, `SW`, `ADDI`, `SLTI`, `SLTIU`, `XORI`, `ORI`, `ANDI`, `SLLI`, `SRLI`, `SRAI`, `ADD`, `SUB`, `SLL`, `SLT`, `SLTU`, `XOR`, `SRL`, `SRA`, `OR`, `AND`) produces the exact architectural `rvfi_rd_wdata`, `rvfi_pc_wdata`, `rvfi_mem_addr`, `rvfi_mem_rmask`, `rvfi_mem_wmask`, and `rvfi_mem_wdata`.

---

## 4. Real RTL Bug Discovered & Fixed by Formal Verification

During initial execution of [`formal/properties/formal_alu.v`](../formal/properties/formal_alu.v), SymbiYosys + Z3 falsified the subtraction signed overflow theorem (`a_sub_overflow`) in 0.2 seconds and emitted the counterexample `a = 0x06000000`, `b = 0x06000000`, `alu_op = ALU_SUB`:

- **Root Cause in [`src/core/alu.v`](../src/core/alu.v#L22-L25)**:
  ```verilog
  // BEFORE (Buggy):
  {carry_out, alu_result} = {1'b0, a} - {1'b0, b};
  overflow = (a[31] ^ ~b[31] ^ alu_result[31]) ^ carry_out;
  ```
  In Verilog, `{1'b0, a} - {1'b0, b}` assigns `carry_out` to the **unsigned borrow** ($b_{32} = (a < b)$), whereas `~b[31]` assumed `carry_out` was the inverted adder carry ($1 - b_{32}$). Because `overflow` is an unused port at the core boundary, neither unit tests nor the 37 RISC-V architectural compliance tests checked it.
- **Fix Applied**:
  ```verilog
  // AFTER (Mathematically Proven):
  {carry_out, alu_result} = {1'b0, a} - {1'b0, b};
  overflow = (a[31] ^ b[31] ^ alu_result[31]) ^ carry_out;
  ```
  Here $(a[31] \oplus b[31] \oplus \text{alu\_result}[31])$ is the borrow *into* bit 31 ($b_{31}$), and $\text{carry\_out}$ is the borrow *out of* bit 31 ($b_{32}$), so $b_{31} \oplus b_{32}$ is identically equal to the two's complement subtraction overflow condition $(a[31] \neq b[31]) \land (\text{alu\_result}[31] \neq a[31])$.

---

## 5. Running the Formal Verification Suite

### Run All Formal Suites (BMC + $k$-Induction + Cover)
```powershell
# Windows (PowerShell)
.\tb\run_formal.ps1 --all

# Linux / macOS (Bash)
./tb/run_formal.sh --all

# Direct Python CLI
python tb/run_formal.py --all
```

### Run a Specific Target or Solver
```powershell
# Verify only the Decoder & Immediate Generator
python tb/run_formal.py --target decoder

# Verify the full RVFI core using a specific SMT solver (z3, yices, bitwuzla, boolector)
python tb/run_formal.py --target rvfi_core --solver z3
```

### Intentional Bug Injection / Counterexample Demo (`--inject-bug`)
To see how SymbiYosys + Z3 immediately falsifies a violated property and generates a concrete counterexample waveform (`.vcd`) and constraint file (`.smtc`):
```powershell
python tb/run_formal.py --inject-bug decoder
```
Sample output:
```text
====================================================================================
      [!] RV32I FORMAL VERIFICATION - INTENTIONAL BUG INJECTION DEMO [!]
====================================================================================
  Target Suite:  decoder (formal_decoder)
  Description:   Main Decoder & Immediate Generator (All 2^32 Encodings)
  SMT Solver:    Z3
  Macro Injected: -DFORMAL_BUG_INJECT
====================================================================================

  [PASS - VIOLATION CAUGHT] SymbiYosys + SMT Solver falsified the property!
  * Elapsed Time:      1.03s
  * Violated Property: core/formal_decoder.v:88.9-88.59
  * Falsified at Step: 0
  * Witness VCD Trace: sim\formal\decoder_bug_bmc\engine_0\trace.vcd
  * Counterexample Input Assignments (.smtc):
      assume (= [clk] false)
      assume (= [instruction] #x01dfa123)
====================================================================================
```
