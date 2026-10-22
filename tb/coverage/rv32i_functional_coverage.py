"""
RV32I Functional Coverage Model
Defines comprehensive CoverPoints and CoverCrosses for the RV32I Base Integer ISA
using cocotb-coverage.
"""

from cocotb_coverage.coverage import CoverPoint, CoverCross, coverage_db

# ---------------------------------------------------------------------------
# Instruction Decoding Helpers
# ---------------------------------------------------------------------------

RV32I_OPCODES = {
    0x33: "R_TYPE",
    0x13: "I_TYPE",
    0x03: "LOAD",
    0x23: "STORE",
    0x63: "BRANCH",
    0x6F: "JAL",
    0x67: "JALR",
    0x37: "LUI",
    0x17: "AUIPC",
}

ALL_37_MNEMONICS = [
    # R-Type (10)
    "ADD", "SUB", "SLL", "SLT", "SLTU", "XOR", "SRL", "SRA", "OR", "AND",
    # I-Type ALU (9)
    "ADDI", "SLLI", "SLTI", "SLTIU", "XORI", "SRLI", "SRAI", "ORI", "ANDI",
    # Loads (5)
    "LB", "LH", "LW", "LBU", "LHU",
    # Stores (3)
    "SB", "SH", "SW",
    # Branches (6)
    "BEQ", "BNE", "BLT", "BGE", "BLTU", "BGEU",
    # Jumps (2)
    "JAL", "JALR",
    # Upper Immediates (2)
    "LUI", "AUIPC",
]

def decode_instruction(instr):
    """Decodes a 32-bit RV32I instruction into its mnemonic and fields."""
    opcode = instr & 0x7F
    rd = (instr >> 7) & 0x1F
    funct3 = (instr >> 12) & 0x7
    rs1 = (instr >> 15) & 0x1F
    rs2 = (instr >> 20) & 0x1F
    funct7 = (instr >> 25) & 0x7F

    mnemonic = "UNKNOWN"

    if opcode == 0x33:  # R-Type
        if funct7 == 0x00:
            mnemonic = {
                0x0: "ADD", 0x1: "SLL", 0x2: "SLT", 0x3: "SLTU",
                0x4: "XOR", 0x5: "SRL", 0x6: "OR", 0x7: "AND"
            }.get(funct3, "UNKNOWN")
        elif funct7 == 0x20:
            if funct3 == 0x0:
                mnemonic = "SUB"
            elif funct3 == 0x5:
                mnemonic = "SRA"

    elif opcode == 0x13:  # I-Type ALU
        if funct3 == 0x1 and funct7 == 0x00:
            mnemonic = "SLLI"
        elif funct3 == 0x5 and funct7 == 0x00:
            mnemonic = "SRLI"
        elif funct3 == 0x5 and funct7 == 0x20:
            mnemonic = "SRAI"
        else:
            mnemonic = {
                0x0: "ADDI", 0x2: "SLTI", 0x3: "SLTIU",
                0x4: "XORI", 0x6: "ORI", 0x7: "ANDI"
            }.get(funct3, "UNKNOWN")

    elif opcode == 0x03:  # Load
        mnemonic = {
            0x0: "LB", 0x1: "LH", 0x2: "LW",
            0x4: "LBU", 0x5: "LHU"
        }.get(funct3, "UNKNOWN")

    elif opcode == 0x23:  # Store
        mnemonic = {
            0x0: "SB", 0x1: "SH", 0x2: "SW"
        }.get(funct3, "UNKNOWN")

    elif opcode == 0x63:  # Branch
        mnemonic = {
            0x0: "BEQ", 0x1: "BNE", 0x4: "BLT",
            0x5: "BGE", 0x6: "BLTU", 0x7: "BGEU"
        }.get(funct3, "UNKNOWN")

    elif opcode == 0x6F:
        mnemonic = "JAL"
    elif opcode == 0x67 and funct3 == 0x0:
        mnemonic = "JALR"
    elif opcode == 0x37:
        mnemonic = "LUI"
    elif opcode == 0x17:
        mnemonic = "AUIPC"

    return {
        "opcode": opcode,
        "rd": rd,
        "funct3": funct3,
        "rs1": rs1,
        "rs2": rs2,
        "funct7": funct7,
        "mnemonic": mnemonic
    }

# ---------------------------------------------------------------------------
# Functional CoverPoints & CoverCrosses
# ---------------------------------------------------------------------------

ALL_REGS = [f"x{i}" for i in range(32)]
REG_CORNER_CASES = [
    "rd_is_x0",
    "rs1_is_x0",
    "rs2_is_x0",
    "rs1_eq_rs2",
    "rd_eq_rs1",
    "rd_eq_rs2",
    "rd_eq_rs1_eq_rs2",
    "none"
]

IMM_CATEGORIES = [
    "ZERO",
    "POS_MAX_12BIT",
    "NEG_MAX_12BIT",
    "MINUS_ONE_12BIT",
    "POS_GENERAL",
    "NEG_GENERAL"
]

BRANCH_TYPES = ["BEQ", "BNE", "BLT", "BGE", "BLTU", "BGEU"]
BRANCH_OUTCOMES = ["TAKEN", "NOT_TAKEN"]
BRANCH_DIRECTIONS = ["FORWARD", "BACKWARD", "SELF"]

LSU_OPERATIONS = ["LB", "LH", "LW", "LBU", "LHU", "SB", "SH", "SW"]
BYTE_OFFSETS = ["OFFSET_0", "OFFSET_1", "OFFSET_2", "OFFSET_3"]


# 1. Instruction CoverPoint
@CoverPoint("rv32i.instruction.opcode",
    xf=lambda info, ctx: RV32I_OPCODES.get(info["opcode"], "UNKNOWN"),
    bins=list(RV32I_OPCODES.values())
)
@CoverPoint("rv32i.instruction.mnemonic",
    xf=lambda info, ctx: info["mnemonic"],
    bins=ALL_37_MNEMONICS
)
# 2. Register CoverPoints
@CoverPoint("rv32i.registers.rd",
    xf=lambda info, ctx: f"x{info['rd']}",
    bins=ALL_REGS
)
@CoverPoint("rv32i.registers.rs1",
    xf=lambda info, ctx: f"x{info['rs1']}",
    bins=ALL_REGS
)
@CoverPoint("rv32i.registers.rs2",
    xf=lambda info, ctx: f"x{info['rs2']}",
    bins=ALL_REGS
)
@CoverPoint("rv32i.registers.corner_cases",
    xf=lambda info, ctx: ctx.get("reg_corner", "none"),
    bins=REG_CORNER_CASES
)
# 3. Immediate Value CoverPoints
@CoverPoint("rv32i.immediate.categories",
    xf=lambda info, ctx: ctx.get("imm_cat", "ZERO"),
    bins=IMM_CATEGORIES
)
@CoverPoint("rv32i.immediate.shamt",
    xf=lambda info, ctx: ctx.get("shamt", 0),
    bins=list(range(32))
)
@CoverPoint("rv32i.immediate.upper_msb",
    xf=lambda info, ctx: ctx.get("upper_msb", "MSB_0"),
    bins=["MSB_0", "MSB_1"]
)
# 4. Branch Dynamics
@CoverPoint("rv32i.branch.type",
    xf=lambda info, ctx: info["mnemonic"] if info["mnemonic"] in BRANCH_TYPES else "NON_BRANCH",
    bins=BRANCH_TYPES + ["NON_BRANCH"]
)
@CoverPoint("rv32i.branch.outcome",
    xf=lambda info, ctx: ctx.get("branch_outcome", "NOT_TAKEN"),
    bins=BRANCH_OUTCOMES
)
@CoverPoint("rv32i.branch.direction",
    xf=lambda info, ctx: ctx.get("branch_dir", "FORWARD"),
    bins=BRANCH_DIRECTIONS
)
# 5. Jump Dynamics
@CoverPoint("rv32i.jump.type",
    xf=lambda info, ctx: info["mnemonic"] if info["mnemonic"] in ["JAL", "JALR"] else "NON_JUMP",
    bins=["JAL", "JALR", "NON_JUMP"]
)
@CoverPoint("rv32i.jump.jalr_align",
    xf=lambda info, ctx: ctx.get("jalr_align", "LSB_0"),
    bins=["LSB_0", "LSB_1"]
)
# 6. LSU Memory Access
@CoverPoint("rv32i.lsu.operation",
    xf=lambda info, ctx: info["mnemonic"] if info["mnemonic"] in LSU_OPERATIONS else "NON_LSU",
    bins=LSU_OPERATIONS + ["NON_LSU"]
)
@CoverPoint("rv32i.lsu.byte_offset",
    xf=lambda info, ctx: ctx.get("byte_offset", "OFFSET_0"),
    bins=BYTE_OFFSETS
)
@CoverPoint("rv32i.lsu.sign_extension",
    xf=lambda info, ctx: ctx.get("lsu_sign", "POSITIVE"),
    bins=["POSITIVE", "NEGATIVE"]
)
# 7. Cross Coverage
@CoverCross("rv32i.cross.branch_type_x_outcome",
    items=["rv32i.branch.type", "rv32i.branch.outcome"],
    ign_bins=[(f, o) for f in ["NON_BRANCH"] for o in BRANCH_OUTCOMES]
)
@CoverCross("rv32i.cross.branch_type_x_direction",
    items=["rv32i.branch.type", "rv32i.branch.direction"],
    ign_bins=[(f, d) for f in ["NON_BRANCH"] for d in BRANCH_DIRECTIONS]
)
@CoverCross("rv32i.cross.lsu_op_x_offset",
    items=["rv32i.lsu.operation", "rv32i.lsu.byte_offset"],
    ign_bins=[(op, off) for op in ["NON_LSU"] for off in BYTE_OFFSETS]
)
def _sample_coverpoints(info, ctx):
    """Internal sampling callback for cocotb-coverage."""
    pass


class FunctionalCoverageCollector:
    """Orchestrates functional coverage sampling for the RV32I Core."""

    def __init__(self):
        self.total_samples = 0

    def sample(self, instr_val, pc_val, next_pc_val, imm_val, mem_addr_val, mem_rdata_val):
        """Samples a committed instruction and execution state."""
        self.total_samples += 1
        info = decode_instruction(instr_val)
        mnemonic = info["mnemonic"]
        rd, rs1, rs2 = info["rd"], info["rs1"], info["rs2"]

        ctx = {}

        # 1. Register corner cases
        corners = []
        if rd == 0:
            corners.append("rd_is_x0")
        if rs1 == 0:
            corners.append("rs1_is_x0")
        if rs2 == 0:
            corners.append("rs2_is_x0")
        if rs1 == rs2 and rs1 != 0:
            corners.append("rs1_eq_rs2")
        if rd == rs1 and rd != 0:
            corners.append("rd_eq_rs1")
        if rd == rs2 and rd != 0:
            corners.append("rd_eq_rs2")
        if rd == rs1 == rs2 and rd != 0:
            corners.append("rd_eq_rs1_eq_rs2")

        if not corners:
            corners = ["none"]

        # 2. Immediate categorisation
        # Convert imm_val to signed 32-bit
        simm = imm_val if imm_val < 0x80000000 else imm_val - 0x100000000
        imm12 = simm & 0xFFF
        if simm == 0:
            imm_cat = "ZERO"
        elif simm == 2047:
            imm_cat = "POS_MAX_12BIT"
        elif simm == -2048:
            imm_cat = "NEG_MAX_12BIT"
        elif simm == -1:
            imm_cat = "MINUS_ONE_12BIT"
        elif simm > 0:
            imm_cat = "POS_GENERAL"
        else:
            imm_cat = "NEG_GENERAL"
        ctx["imm_cat"] = imm_cat

        if mnemonic in ["SLL", "SRL", "SRA", "SLLI", "SRLI", "SRAI"]:
            ctx["shamt"] = rs2 if mnemonic in ["SLL", "SRL", "SRA"] else (imm_val & 0x1F)
        else:
            ctx["shamt"] = 0

        if mnemonic in ["LUI", "AUIPC"]:
            ctx["upper_msb"] = "MSB_1" if (imm_val & 0x80000000) != 0 else "MSB_0"
        else:
            ctx["upper_msb"] = "MSB_0"

        # 3. Branch Dynamics
        if mnemonic in BRANCH_TYPES:
            taken = (next_pc_val != ((pc_val + 4) & 0xFFFFFFFF))
            ctx["branch_outcome"] = "TAKEN" if taken else "NOT_TAKEN"
            if simm > 0:
                ctx["branch_dir"] = "FORWARD"
            elif simm < 0:
                ctx["branch_dir"] = "BACKWARD"
            else:
                ctx["branch_dir"] = "SELF"
        else:
            ctx["branch_outcome"] = "NOT_TAKEN"
            ctx["branch_dir"] = "FORWARD"

        # 4. Jump Dynamics
        if mnemonic == "JALR":
            # Check if target address had bit 0 set (which must be cleared by hardware)
            raw_target = (rs1 + imm_val) & 0xFFFFFFFF
            ctx["jalr_align"] = "LSB_1" if (raw_target & 1) else "LSB_0"
        else:
            ctx["jalr_align"] = "LSB_0"

        # 5. LSU Memory Access
        if mnemonic in LSU_OPERATIONS:
            offset_bin = f"OFFSET_{mem_addr_val & 0x3}"
            ctx["byte_offset"] = offset_bin
            
            # Check sign extension for signed byte/halfword loads
            if mnemonic == "LB":
                byte_val = (mem_rdata_val >> ((mem_addr_val & 3) * 8)) & 0xFF
                ctx["lsu_sign"] = "NEGATIVE" if (byte_val & 0x80) else "POSITIVE"
            elif mnemonic == "LH":
                hw_val = (mem_rdata_val >> ((mem_addr_val & 2) * 8)) & 0xFFFF
                ctx["lsu_sign"] = "NEGATIVE" if (hw_val & 0x8000) else "POSITIVE"
            else:
                ctx["lsu_sign"] = "POSITIVE"
        else:
            ctx["byte_offset"] = "OFFSET_0"
            ctx["lsu_sign"] = "POSITIVE"

        # Sample for each identified corner case
        for corner in corners:
            ctx_copy = dict(ctx)
            ctx_copy["reg_corner"] = corner
            _sample_coverpoints(info, ctx_copy)

    def get_summary(self):
        """Returns dictionary of coverage metrics and statistics."""
        summary = {
            "total_samples": self.total_samples,
            "groups": {}
        }
        for key in sorted(coverage_db.keys()):
            item = coverage_db[key]
            cov = getattr(item, "coverage", 0)
            size = getattr(item, "size", 0)
            pct = (cov / size * 100.0) if size > 0 else 0.0
            summary["groups"][key] = {
                "coverage": cov,
                "size": size,
                "percentage": round(pct, 2)
            }
        return summary
