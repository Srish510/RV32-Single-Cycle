`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module pc_writeback_mux(
    input wire [31:0] offset_pc,
    input wire [31:0] pc_incremented,
    input wire pc_writeback_src,
    output reg [31:0] pc_writeback
);

    always @(*) begin
        case (pc_writeback_src)
            `PC_WB_SEL_INC:    pc_writeback = pc_incremented;    // For regular instructions (PC + 4)
            `PC_WB_SEL_OFFSET: pc_writeback = offset_pc;         // For AUIPC instruction
            default:           pc_writeback = 32'b0;              // Default case
        endcase
    end

endmodule
