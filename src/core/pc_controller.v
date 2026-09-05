`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module pc_controller (
    input wire [31:0] pc,             // Current PC from external register
    input wire [31:0] offset,         // Shared immediate for branch or JAL targets
    input wire lt_flag,
    input wire eq_flag,
    input wire [2:0] branch_op,
    input wire [1:0] next_pc_src,
    input wire [31:0] jalr_pc,        // Fed from external ALU result 
    output wire [31:0] next_pc,       // Calculated next PC to feed back to the register
    output wire [31:0] offset_pc,     // PC + offset for branch instructions
    output wire [31:0] pc_incremented // PC + 4, output for rd linking in JAL/JALR
);

    // Internal routing wires
    wire [31:0] branch_pc_wire;

    // Continuous assignments mapping to the physical adders
    assign pc_incremented = pc + 32'd4;
    assign offset_pc = pc + offset;

    // Branch Decision Unit
    branch_unit branch_unit_inst (
        .pc_prev(pc),
        .offset(offset),
        .lt_flag(lt_flag),
        .eq_flag(eq_flag),
        .branch_op(branch_op),
        .pc_next(branch_pc_wire)
    );

    // Next PC Multiplexer
    pc_src_mux pc_mux_inst (
        .branch_pc(branch_pc_wire),
        .pc_incremented(pc_incremented),
        .jal_pc(offset_pc), 
        .jalr_pc(jalr_pc),
        .next_pc_src(next_pc_src),
        .pc_next(next_pc)
    );

endmodule
