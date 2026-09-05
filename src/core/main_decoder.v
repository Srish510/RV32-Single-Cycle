`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module main_decoder(
    /* verilator lint_off UNUSEDSIGNAL */
    input  wire [31:0] instruction,
    /* verilator lint_on UNUSEDSIGNAL */
    output reg  [1:0]  next_pc_src,
    output reg         pc_writeback_src,
    output reg  [2:0]  branch_op,
    output reg  [1:0]  reg_src,
    output reg  [3:0]  lsu_op,
    output reg         alu_src,
    output reg  [3:0]  alu_op,
    output reg         reg_write
);

    wire [6:0] opcode;
    wire [2:0] funct3;
    wire [6:0] funct7;
    
    assign opcode = instruction[6:0];
    assign funct3 = instruction[14:12];
    assign funct7 = instruction[31:25];

    always @(*) begin
        // Default assignments to prevent latches
        next_pc_src      = `PC_SEL_INC;   
        pc_writeback_src = `PC_WB_SEL_INC;    
        branch_op        = `BRANCH_NONE;  
        reg_src          = `WB_SEL_REG;   
        lsu_op           = `LSU_NONE; 
        alu_src          = `ALU_SRC_REG;    
        alu_op           = `ALU_ADD;   
        reg_write        = `REG_WRITE_DISABLE;   

        case (opcode)
            `OPCODE_R_TYPE: begin                // R-type instructions
                alu_src   = `ALU_SRC_REG;
                reg_src   = `WB_SEL_REG;
                reg_write = `REG_WRITE_ENABLE;
                case ({funct7, funct3})
                    {`FUNCT7_BASE, `FUNCT3_ADD_SUB}: alu_op = `ALU_ADD;
                    {`FUNCT7_ALT,  `FUNCT3_ADD_SUB}: alu_op = `ALU_SUB;
                    
                    {`FUNCT7_BASE, `FUNCT3_AND}:     alu_op = `ALU_AND;
                    {`FUNCT7_BASE, `FUNCT3_OR}:      alu_op = `ALU_OR;
                    {`FUNCT7_BASE, `FUNCT3_XOR}:     alu_op = `ALU_XOR;
                    
                    {`FUNCT7_BASE, `FUNCT3_SLL}:     alu_op = `ALU_SLL;
                    {`FUNCT7_BASE, `FUNCT3_SRL_SRA}: alu_op = `ALU_SRL;
                    {`FUNCT7_ALT,  `FUNCT3_SRL_SRA}: alu_op = `ALU_SRA;
                    
                    {`FUNCT7_BASE, `FUNCT3_SLT}:     alu_op = `ALU_SLT;
                    {`FUNCT7_BASE, `FUNCT3_SLTU}:    alu_op = `ALU_SLTU;
                    
                    default:                         alu_op = `ALU_ADD;
                endcase
            end

            `OPCODE_OP_IMM: begin              // I-type ALU instructions
                alu_src   = `ALU_SRC_IMM;
                reg_src   = `WB_SEL_REG;
                reg_write = `REG_WRITE_ENABLE;
                case (funct3)
                    `FUNCT3_ADD_SUB: alu_op = `ALU_ADD;
                    `FUNCT3_AND:     alu_op = `ALU_AND;
                    `FUNCT3_OR:      alu_op = `ALU_OR;
                    `FUNCT3_XOR:     alu_op = `ALU_XOR;
                    `FUNCT3_SLL:     alu_op = `ALU_SLL;
                    `FUNCT3_SRL_SRA: begin
                        if (funct7 == `FUNCT7_BASE) begin
                            alu_op = `ALU_SRL; 
                        end else if (funct7 == `FUNCT7_ALT) begin
                            alu_op = `ALU_SRA; 
                        end else begin
                            alu_op = `ALU_ADD; // Default to ADD for safety
                        end
                    end
                    `FUNCT3_SLT:  alu_op = `ALU_SLT;
                    `FUNCT3_SLTU: alu_op = `ALU_SLTU;
                    default:      alu_op = `ALU_ADD; // Default to ADD for safety
                endcase
            end

            `OPCODE_LOAD: begin                 // Load instructions
                alu_src   = `ALU_SRC_IMM;
                reg_src   = `WB_SEL_MEM;
                reg_write = `REG_WRITE_ENABLE;
                alu_op    = `ALU_ADD;           // Address calculation
                case (funct3)
                    `FUNCT3_LB:  lsu_op = `LSU_LB;
                    `FUNCT3_LH:  lsu_op = `LSU_LH;
                    `FUNCT3_LW:  lsu_op = `LSU_LW;
                    `FUNCT3_LBU: lsu_op = `LSU_LBU;
                    `FUNCT3_LHU: lsu_op = `LSU_LHU;
                    default:     lsu_op = `LSU_NONE; // Default to no operation
                endcase
            end

            `OPCODE_STORE: begin                // Store instructions
                alu_src   = `ALU_SRC_IMM;
                reg_write = `REG_WRITE_DISABLE;  
                alu_op    = `ALU_ADD;            // Address calculation
                case (funct3)
                    `FUNCT3_SB: lsu_op = `LSU_SB;
                    `FUNCT3_SH: lsu_op = `LSU_SH;
                    `FUNCT3_SW: lsu_op = `LSU_SW;
                    default:    lsu_op = `LSU_NONE; // Default to no operation
                endcase
            end

            `OPCODE_BRANCH: begin               // Branch instructions
                alu_src   = `ALU_SRC_REG;
                reg_write = `REG_WRITE_DISABLE;  
                alu_op    = `ALU_SUB;            // For comparison
                next_pc_src = `PC_SEL_BRANCH;    
                case (funct3)
                    `FUNCT3_BEQ:  branch_op = `BRANCH_BEQ;
                    `FUNCT3_BNE:  branch_op = `BRANCH_BNE;
                    `FUNCT3_BLT: begin 
                        branch_op = `BRANCH_BLT;
                        alu_op = `ALU_SLT; 
                    end
                    `FUNCT3_BGE:  begin
                        branch_op = `BRANCH_BGE;
                        alu_op = `ALU_SLT;
                    end
                    `FUNCT3_BLTU: begin
                        branch_op = `BRANCH_BLT;
                        alu_op = `ALU_SLTU;
                    end
                    `FUNCT3_BGEU: begin
                        branch_op = `BRANCH_BGE;
                        alu_op = `ALU_SLTU;
                    end
                    default:      branch_op = `BRANCH_NONE; // Default to no operation
                endcase
            end

            `OPCODE_JAL: begin                  // JAL instruction
                next_pc_src      = `PC_SEL_JAL;
                pc_writeback_src = `PC_WB_SEL_INC; 
                reg_src          = `WB_SEL_PC_NEXT; 
                reg_write        = `REG_WRITE_ENABLE;  
            end

            `OPCODE_JALR: begin                 // JALR instruction
                next_pc_src      = `PC_SEL_JALR;
                pc_writeback_src = `PC_WB_SEL_INC; 
                alu_src          = `ALU_SRC_IMM;
                alu_op           = `ALU_ADD;
                reg_src          = `WB_SEL_PC_NEXT; 
                reg_write        = `REG_WRITE_ENABLE;  
            end

            `OPCODE_LUI: begin                  // LUI instruction
                alu_src   = `ALU_SRC_IMM;
                reg_src   = `WB_SEL_UPP_IMM; 
                reg_write = `REG_WRITE_ENABLE;  
                alu_op    = `ALU_ADD;           
            end

            `OPCODE_AUIPC: begin                // AUIPC instruction
                alu_src   = `ALU_SRC_IMM;
                reg_src   = `WB_SEL_PC_NEXT; 
                reg_write = `REG_WRITE_ENABLE;  
                alu_op    = `ALU_ADD;           
                pc_writeback_src = `PC_WB_SEL_OFFSET; 
            end

            default: ; // Use default zeroed assignments
        endcase
    end

endmodule
