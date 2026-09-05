`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module branch_unit(
    input wire [31:0] pc_prev,
    input wire [31:0] offset,
    input wire lt_flag,
    input wire eq_flag,
    input wire [2:0] branch_op,
    output reg [31:0] pc_next
);

    always @(*) begin
        case (branch_op)
            `BRANCH_NONE: pc_next = pc_prev + 4;                                    // No branch, go to next instruction
            `BRANCH_BEQ:  pc_next = eq_flag ? (pc_prev + offset) : (pc_prev + 4);   // Branch if equal
            `BRANCH_BNE:  pc_next = !eq_flag ? (pc_prev + offset) : (pc_prev + 4);  // Branch if not equal
            `BRANCH_BLT:  pc_next = lt_flag ? (pc_prev + offset) : (pc_prev + 4);   // Branch if less than (signed or unisgned)
            `BRANCH_BGE:  pc_next = !lt_flag ? (pc_prev + offset) : (pc_prev + 4);  // Branch if greater than or equal (signed or unisgned)
            default:      pc_next = pc_prev + 4;                                    // Default case, go to next instruction
        endcase
    end

endmodule
