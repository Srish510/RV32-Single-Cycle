// src/include/rv32i_defs.vh
`ifndef RV32I_DEFS_VH
`define RV32I_DEFS_VH

// Opcode Definitions
`define OPCODE_R_TYPE  7'b0110011
`define OPCODE_OP_IMM  7'b0010011
`define OPCODE_LOAD    7'b0000011
`define OPCODE_STORE   7'b0100011
`define OPCODE_BRANCH  7'b1100011
`define OPCODE_JAL     7'b1101111
`define OPCODE_JALR    7'b1100111
`define OPCODE_LUI     7'b0110111
`define OPCODE_AUIPC   7'b0010111

// Funct7 Definitions
`define FUNCT7_BASE 7'h00  // ADD, SLL, SLT, SLTU, XOR, SRL, OR, AND
`define FUNCT7_ALT  7'h20  // SUB, SRA

// Funct3 Definitions for ALU operations
`define FUNCT3_ADD_SUB 3'h0
`define FUNCT3_SLL     3'h1
`define FUNCT3_SLT     3'h2
`define FUNCT3_SLTU    3'h3
`define FUNCT3_XOR     3'h4
`define FUNCT3_SRL_SRA 3'h5
`define FUNCT3_OR      3'h6
`define FUNCT3_AND     3'h7

// Funct3 Definitions for Load operations
`define FUNCT3_LB  3'h0
`define FUNCT3_LH  3'h1
`define FUNCT3_LW  3'h2
`define FUNCT3_LBU 3'h4
`define FUNCT3_LHU 3'h5

// Funct3 Definitions for Store operations
`define FUNCT3_SB 3'h0
`define FUNCT3_SH 3'h1
`define FUNCT3_SW 3'h2

// Funct3 Definitions for Branch operations
`define FUNCT3_BEQ 3'h0
`define FUNCT3_BNE 3'h1
`define FUNCT3_BLT 3'h4
`define FUNCT3_BGE 3'h5
`define FUNCT3_BLTU 3'h6
`define FUNCT3_BGEU 3'h7

// ALU Control Signals
`define ALU_ADD  4'b0000
`define ALU_SUB  4'b1000
`define ALU_AND  4'b0111
`define ALU_OR   4'b0110
`define ALU_XOR  4'b0100
`define ALU_SLL  4'b0001
`define ALU_SRL  4'b0101
`define ALU_SRA  4'b1101
`define ALU_SLT  4'b0010
`define ALU_SLTU 4'b0011

// ALU Source Select
`define ALU_SRC_REG 1'b0
`define ALU_SRC_IMM 1'b1

// Load/Store Control Signals
`define LSU_NONE 4'b0000
`define LSU_LB   4'b0001
`define LSU_LH   4'b0010
`define LSU_LW   4'b0011
`define LSU_LBU  4'b0100
`define LSU_LHU  4'b0101
`define LSU_SB   4'b1001
`define LSU_SH   4'b1010
`define LSU_SW   4'b1011

// Write Back Control Signals
`define WB_SEL_REG  2'b00
`define WB_SEL_MEM  2'b01
`define WB_SEL_UPP_IMM 2'b10
`define WB_SEL_PC_NEXT 2'b11

// Branch Control Signals
`define BRANCH_NONE 3'b000
`define BRANCH_BEQ  3'b001
`define BRANCH_BNE  3'b010
`define BRANCH_BLT  3'b011
`define BRANCH_BGE  3'b100

// Next PC Source Control Signals
`define PC_SEL_INC    2'b00
`define PC_SEL_BRANCH   2'b01
`define PC_SEL_JAL    2'b10
`define PC_SEL_JALR   2'b11

// PC Writeback Control Signals
`define PC_WB_SEL_INC   1'b0
`define PC_WB_SEL_OFFSET 1'b1

// Register File Control Signals
`define REG_WRITE_DISABLE 1'b0
`define REG_WRITE_ENABLE 1'b1

`endif // RV32I_DEFS_VH
