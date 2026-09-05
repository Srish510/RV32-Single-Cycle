`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module pc_src_mux(
    input wire [31:0] branch_pc,
    input wire [31:0] pc_incremented,
    input wire [31:0] jal_pc,
    input wire [31:0] jalr_pc,
    input wire [1:0] next_pc_src,
    output reg [31:0] pc_next
);
    always @(*) begin
        case (next_pc_src)
            `PC_SEL_INC:    pc_next = pc_incremented;         // For branch instructions
            `PC_SEL_BRANCH: pc_next = branch_pc;              // For regular instructions (PC + 4)
            `PC_SEL_JAL:    pc_next = jal_pc;                 // For JAL instructions
            `PC_SEL_JALR:   pc_next = jalr_pc;                // For JALR instructions
            default:        pc_next = 32'b0;                  // Default case
        endcase
    end

endmodule
