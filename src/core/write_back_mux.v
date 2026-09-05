`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module write_back_mux(
    input wire [31:0] reg_data,
    input wire [31:0] mem_data,
    input wire [31:0] upp_imm_data,
    input wire [31:0] pc_next,
    input wire [1:0] reg_src,
    output reg [31:0] out_data
);
    always @(*) begin
        case (reg_src)
            `WB_SEL_REG: out_data = reg_data;                // Write back ALU result
            `WB_SEL_MEM: out_data = mem_data;                // Write back memory data
            `WB_SEL_UPP_IMM: out_data = upp_imm_data;        // Write back upper immediate data
            `WB_SEL_PC_NEXT: out_data = pc_next;             // Write back PC value
            default:     out_data = 32'b0;                   // Default case
        endcase
    end

endmodule
