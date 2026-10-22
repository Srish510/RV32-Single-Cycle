"""
RTL Structural (Code / Toggle / Decision) Coverage Monitor
Tracks bit-level toggle transitions (0->1 and 1->0) across key datapath buses
and tracks branch/multiplexer decision coverage for the RV32I Core.
"""

import json
from pathlib import Path

SIGNAL_SPECS = {
    "instr_addr": 32,
    "instr_data": 32,
    "pc_out": 32,
    "next_pc": 32,
    "alu_result": 32,
    "alu_input_b": 32,
    "read_data1": 32,
    "read_data2": 32,
    "imm_data": 32,
    "write_data": 32,
    "data_addr": 32,
    "data_wdata": 32,
    "data_rdata": 32,
    "data_we": 4,
    "data_re": 1,
    "zero_flag": 1,
    "carry_out": 1,
    "overflow": 1,
}

DECISION_SPECS = {
    "alu_src": [0, 1],
    "reg_src": [0, 1, 2, 3],
    "next_pc_src": [0, 1, 2],
    "pc_writeback_src": [0, 1],
    "reg_write": [0, 1],
    # Hardware ALU opcodes: ADD(0), SLL(1), SLT(2), SLTU(3), XOR(4), SRL(5), OR(6), AND(7), SUB(8), SRA(13)
    "alu_op": [0, 1, 2, 3, 4, 5, 6, 7, 8, 13],
    # Hardware Branch opcodes: NONE(0), BEQ(1), BNE(2), BLT(3), BGE(4)
    "branch_op": [0, 1, 2, 3, 4],
    # Hardware LSU opcodes: NONE(0), LB(1), LH(2), LW(3), LBU(4), LHU(5), SB(9), SH(10), SW(11)
    "lsu_op": [0, 1, 2, 3, 4, 5, 9, 10, 11],
}


class StructuralCoverageMonitor:
    """Monitors signal toggles and control decisions across RTL execution cycles."""

    def __init__(self):
        # bit_toggles[sig][bit] = {"0->1": bool, "1->0": bool}
        self.toggles = {}
        for sig, width in SIGNAL_SPECS.items():
            self.toggles[sig] = [{"0->1": False, "1->0": False} for _ in range(width)]

        self.prev_values = {}

        # decisions[name][val] = hit_count
        self.decisions = {}
        for name, values in DECISION_SPECS.items():
            self.decisions[name] = {v: 0 for v in values}

        self.total_cycles = 0

    def sample_cycle(self, dut):
        """Samples all signals and decision states on a simulation clock cycle."""
        self.total_cycles += 1
        
        # 1. Sample Signal Toggles
        signals_to_read = {
            "instr_addr": dut.core_inst.instr_addr,
            "instr_data": dut.core_inst.instr_data,
            "pc_out": dut.core_inst.pc_out,
            "next_pc": dut.core_inst.next_pc,
            "alu_result": dut.core_inst.alu_result,
            "alu_input_b": dut.core_inst.alu_input_b,
            "read_data1": dut.core_inst.read_data1,
            "read_data2": dut.core_inst.read_data2,
            "imm_data": dut.core_inst.imm_data,
            "write_data": dut.core_inst.write_data,
            "data_addr": dut.core_inst.data_addr,
            "data_wdata": dut.core_inst.data_wdata,
            "data_rdata": dut.core_inst.data_rdata,
            "data_we": dut.core_inst.data_we,
            "data_re": dut.core_inst.data_re,
            "zero_flag": dut.core_inst.zero_flag,
            "carry_out": dut.core_inst.carry_out,
            "overflow": dut.core_inst.overflow,
        }

        for sig, handle in signals_to_read.items():
            try:
                val = int(handle.value)
            except ValueError:
                continue

            width = SIGNAL_SPECS[sig]
            prev = self.prev_values.get(sig, None)
            if prev is not None:
                # Compare each bit
                diff = prev ^ val
                if diff != 0:
                    for b in range(width):
                        if (diff >> b) & 1:
                            if (val >> b) & 1:
                                self.toggles[sig][b]["0->1"] = True
                            else:
                                self.toggles[sig][b]["1->0"] = True
            self.prev_values[sig] = val

        # 2. Sample Decision States (Multiplexers and Control Lines)
        decisions_to_read = {
            "alu_src": dut.core_inst.alu_src,
            "reg_src": dut.core_inst.reg_src,
            "next_pc_src": dut.core_inst.next_pc_src,
            "pc_writeback_src": dut.core_inst.pc_writeback_src,
            "reg_write": dut.core_inst.reg_write,
            "alu_op": dut.core_inst.alu_op,
            "branch_op": dut.core_inst.branch_op,
            "lsu_op": dut.core_inst.lsu_op,
        }

        for name, handle in decisions_to_read.items():
            try:
                d_val = int(handle.value)
                if d_val in self.decisions[name]:
                    self.decisions[name][d_val] += 1
            except ValueError:
                pass

    def get_summary(self):
        """Computes summary statistics for toggle and decision coverage."""
        total_transitions = 0
        hit_transitions = 0
        signal_breakdown = {}

        for sig, bits in self.toggles.items():
            sig_total = len(bits) * 2
            sig_hits = sum((1 if b["0->1"] else 0) + (1 if b["1->0"] else 0) for b in bits)
            total_transitions += sig_total
            hit_transitions += sig_hits
            signal_breakdown[sig] = {
                "hits": sig_hits,
                "total": sig_total,
                "percentage": round(sig_hits / sig_total * 100.0, 2)
            }

        total_decisions = sum(len(v) for v in self.decisions.values())
        hit_decisions = sum(sum(1 for count in v.values() if count > 0) for v in self.decisions.values())

        toggle_pct = round(hit_transitions / total_transitions * 100.0, 2) if total_transitions > 0 else 0.0
        decision_pct = round(hit_decisions / total_decisions * 100.0, 2) if total_decisions > 0 else 0.0

        return {
            "total_cycles": self.total_cycles,
            "toggle": {
                "hit_transitions": hit_transitions,
                "total_transitions": total_transitions,
                "percentage": toggle_pct,
                "signals": signal_breakdown
            },
            "decision": {
                "hit_decisions": hit_decisions,
                "total_decisions": total_decisions,
                "percentage": decision_pct,
                "controls": {
                    k: {
                        "hits": sum(1 for c in v.values() if c > 0),
                        "total": len(v),
                        "percentage": round(sum(1 for c in v.values() if c > 0) / len(v) * 100.0, 2),
                        "unhit": [val for val, count in v.items() if count == 0]
                    } for k, v in self.decisions.items()
                }
            }
        }

    def save_json(self, filepath):
        """Saves current structural coverage state to JSON file."""
        data = {
            "toggles": self.toggles,
            "decisions": {k: {str(val): cnt for val, cnt in v.items()} for k, v in self.decisions.items()},
            "total_cycles": self.total_cycles
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_and_merge(self, filepath):
        """Loads and merges another structural coverage JSON file into this instance."""
        p = Path(filepath)
        if not p.exists():
            return
        with open(p, "r") as f:
            data = json.load(f)

        self.total_cycles += data.get("total_cycles", 0)

        other_toggles = data.get("toggles", {})
        for sig, bits in other_toggles.items():
            if sig in self.toggles:
                for idx, b in enumerate(bits):
                    if idx < len(self.toggles[sig]):
                        if b.get("0->1", False):
                            self.toggles[sig][idx]["0->1"] = True
                        if b.get("1->0", False):
                            self.toggles[sig][idx]["1->0"] = True

        other_decisions = data.get("decisions", {})
        for name, vals in other_decisions.items():
            if name in self.decisions:
                for val_str, count in vals.items():
                    val = int(val_str)
                    if val in self.decisions[name]:
                        self.decisions[name][val] += count
