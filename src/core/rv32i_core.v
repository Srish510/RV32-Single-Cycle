`timescale 1ns/1ps

module rv32i_core (
    input wire clk,
    input wire rst,

    // Instruction Memory Interface
    output wire [31:0] instr_addr,
    input  wire [31:0] instr_data,

    // Data Memory Interface
    output wire [31:0] data_addr,
    output wire [31:0] data_wdata,
    output wire [3:0]  data_we,
    output wire        data_re,
    input  wire [31:0] data_rdata
);

    // PC Wires
    wire [31:0] pc_out;
    wire [31:0] next_pc;
    wire [31:0] offset_pc;
    wire [31:0] pc_incremented;
    wire [31:0] pc_writeback;

    // Decoder Wires
    wire [1:0]  next_pc_src;
    wire        pc_writeback_src;
    wire [2:0]  branch_op;
    wire [1:0]  reg_src;
    wire [3:0]  lsu_op;
    wire        alu_src;
    wire [3:0]  alu_op;
    wire        reg_write;

    // Immediate Gen Wire
    wire [31:0] imm_data;

    // Register File Wires
    wire [31:0] read_data1;
    wire [31:0] read_data2;
    wire [31:0] write_data;

    // ALU Wires
    wire [31:0] alu_input_b;
    wire [31:0] alu_result;
    wire        zero_flag;
    /* verilator lint_off UNUSEDSIGNAL */
    wire        carry_out;
    wire        overflow;
    /* verilator lint_on UNUSEDSIGNAL */

    // LSU Wire
    wire [31:0] lsu_reg_write_data;
    
    // Instruction fetch assignment
    assign instr_addr = pc_out;
    wire [31:0] instruction = instr_data;

    // Data memory address assignment
    assign data_addr = alu_result;

    // 1. Program Counter
    program_counter pc_inst (
        .clk(clk),
        .rst(rst),
        .next_pc(next_pc),
        .pc(pc_out)
    );

    // 2. PC Controller (Includes Branch Unit & PC Src Mux)
    pc_controller pc_ctrl_inst (
        .pc(pc_out),
        .offset(imm_data),
        .lt_flag(alu_result[0]),
        .eq_flag(zero_flag),
        .branch_op(branch_op),
        .next_pc_src(next_pc_src),
        .jalr_pc(alu_result),
        .next_pc(next_pc),
        .offset_pc(offset_pc),
        .pc_incremented(pc_incremented)
    );

    // 3. Main Decoder
    main_decoder decoder_inst (
        .instruction(instruction),
        .next_pc_src(next_pc_src),
        .pc_writeback_src(pc_writeback_src),
        .branch_op(branch_op),
        .reg_src(reg_src),
        .lsu_op(lsu_op),
        .alu_src(alu_src),
        .alu_op(alu_op),
        .reg_write(reg_write)
    );

    // 4. Register File
    register_file reg_file_inst (
        .clk(clk),
        .rs1(instruction[19:15]),
        .rs2(instruction[24:20]),
        .rd(instruction[11:7]),
        .write_data(write_data),
        .write_enable(reg_write),
        .read_data1(read_data1),
        .read_data2(read_data2)
    );

    // 5. Immediate Generator
    immediate_gen imm_gen_inst (
        .instruction(instruction),
        .imm_out(imm_data)
    );

    // 6. ALU Mux
    alu_mux alu_mux_inst (
        .reg_data(read_data2),
        .imm_data(imm_data),
        .alu_src(alu_src),
        .alu_input_b(alu_input_b)
    );

    // 7. ALU
    alu alu_inst (
        .a(read_data1),
        .b(alu_input_b),
        .alu_op(alu_op),
        .alu_result(alu_result),
        .zero(zero_flag),
        .carry_out(carry_out),
        .overflow(overflow)
    );

    // 8. LSU (Load Store Unit)
    lsu lsu_inst (
        .addr_in(alu_result),
        .mem_read_data(data_rdata),
        .reg_read_data(read_data2),
        .lsu_op(lsu_op),
        .mem_re(data_re),
        .mem_we(data_we),
        .mem_write_data(data_wdata),
        .reg_write_data(lsu_reg_write_data)
    );

    // 9. PC Writeback Mux
    pc_writeback_mux pc_wb_mux_inst (
        .offset_pc(offset_pc),
        .pc_incremented(pc_incremented),
        .pc_writeback_src(pc_writeback_src),
        .pc_writeback(pc_writeback)
    );

    // 10. Write Back Mux
    write_back_mux wb_mux_inst (
        .reg_data(alu_result),
        .mem_data(lsu_reg_write_data),
        .upp_imm_data(imm_data),
        .pc_next(pc_writeback),
        .reg_src(reg_src),
        .out_data(write_data)
    );

endmodule
