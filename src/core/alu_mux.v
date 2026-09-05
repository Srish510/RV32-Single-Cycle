`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module alu_mux(
    input wire [31:0] reg_data,
    input wire [31:0] imm_data,
    input wire alu_src,
    output wire [31:0] alu_input_b
);

    assign alu_input_b = (alu_src == `ALU_SRC_IMM) ? imm_data : reg_data;

endmodule
