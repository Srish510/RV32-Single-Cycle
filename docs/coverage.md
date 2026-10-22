# RV32I Verification & Coverage Summary

**Verification Status:** ✅ **LOOP CLOSED (100% Functional Coverage Met)**

## High-Level Metrics

* **Functional (ISA) Coverage:** 100.00% (284 / 284 bins)
* **Verilator Branch Coverage:** 100.00% (50 / 50 branches)
* **Verilator Line Coverage:** 89.00% (97 / 109 lines)
* **Verilator Signal Toggle Coverage:** 88.40% (4322 / 4888 toggles)
* **Cocotb Signal Toggle Coverage:** 0.00% (0 / 0 transitions)
* **Control/Mux Decision Coverage:** 0.00% (0 / 0 states)

## Verilator Structural Coverage by Design Unit

| Design Unit | Branch Coverage | Line Coverage | Toggle Coverage |
| :--- | :---: | :---: | :---: |
| `alu` | 100.0% | 91.7% | 100.0% |
| `alu_mux` | 100.0% | N/A | 100.0% |
| `branch_unit` | 100.0% | 85.7% | 73.3% |
| `data_mem__A13` | 100.0% | 100.0% | 96.7% |
| `immediate_gen` | N/A | 100.0% | 98.4% |
| `instr_mem__A13` | N/A | N/A | 77.3% |
| `lsu` | 100.0% | 100.0% | 94.7% |
| `main_decoder` | N/A | 86.3% | 97.0% |
| `pc_controller` | N/A | N/A | 76.6% |
| `pc_src_mux` | N/A | 83.3% | 74.4% |
| `pc_writeback_mux` | N/A | 75.0% | 84.0% |
| `program_counter` | 100.0% | 100.0% | 59.1% |
| `register_file` | 100.0% | 100.0% | 100.0% |
| `rv32i_core` | N/A | N/A | 89.6% |
| `rv32i_top` | N/A | N/A | 88.9% |
| `write_back_mux` | N/A | 83.3% | 98.1% |

## Functional Coverage Breakdown

| CoverGroup | Hit / Total | Percentage |
| :--- | :---: | :---: |
| `branch` | 12 / 12 | 100.00% |
| &nbsp;&nbsp;`direction` | 3 / 3 | 100.00% |
| &nbsp;&nbsp;`outcome` | 2 / 2 | 100.00% |
| &nbsp;&nbsp;`type` | 7 / 7 | 100.00% |
| `cross` | 62 / 62 | 100.00% |
| &nbsp;&nbsp;`branch_type_x_direction` | 18 / 18 | 100.00% |
| &nbsp;&nbsp;`branch_type_x_outcome` | 12 / 12 | 100.00% |
| &nbsp;&nbsp;`lsu_op_x_offset` | 32 / 32 | 100.00% |
| `immediate` | 40 / 40 | 100.00% |
| &nbsp;&nbsp;`categories` | 6 / 6 | 100.00% |
| &nbsp;&nbsp;`shamt` | 32 / 32 | 100.00% |
| &nbsp;&nbsp;`upper_msb` | 2 / 2 | 100.00% |
| `instruction` | 46 / 46 | 100.00% |
| &nbsp;&nbsp;`mnemonic` | 37 / 37 | 100.00% |
| &nbsp;&nbsp;`opcode` | 9 / 9 | 100.00% |
| `jump` | 5 / 5 | 100.00% |
| &nbsp;&nbsp;`jalr_align` | 2 / 2 | 100.00% |
| &nbsp;&nbsp;`type` | 3 / 3 | 100.00% |
| `lsu` | 15 / 15 | 100.00% |
| &nbsp;&nbsp;`byte_offset` | 4 / 4 | 100.00% |
| &nbsp;&nbsp;`operation` | 9 / 9 | 100.00% |
| &nbsp;&nbsp;`sign_extension` | 2 / 2 | 100.00% |
| `registers` | 104 / 104 | 100.00% |
| &nbsp;&nbsp;`corner_cases` | 8 / 8 | 100.00% |
| &nbsp;&nbsp;`rd` | 32 / 32 | 100.00% |
| &nbsp;&nbsp;`rs1` | 32 / 32 | 100.00% |
| &nbsp;&nbsp;`rs2` | 32 / 32 | 100.00% |

## Control Decision Breakdown

| Control Signal | Hits / Total | Percentage | Unhit States |
| :--- | :---: | :---: | :--- |