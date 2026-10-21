`timescale 1ns/1ps

module rv32i_top (
    input wire clk,
    input wire rst
);

    // Instruction Memory Interconnect
    wire [31:0] instr_addr;
    wire [31:0] instr_data;

    // Data Memory Interconnect
    wire [31:0] data_addr;
    wire [31:0] data_wdata;
    wire [3:0]  data_we;
    wire        data_re;
    wire [31:0] data_rdata;

    // Instantiate the RV32I Core
    rv32i_core core_inst (
        .clk(clk),
        .rst(rst),
        
        // Instruction Memory Interface
        .instr_addr(instr_addr),
        .instr_data(instr_data),
        
        // Data Memory Interface
        .data_addr(data_addr),
        .data_wdata(data_wdata),
        .data_we(data_we),
        .data_re(data_re),
        .data_rdata(data_rdata)
    );

    instr_mem #(
        .ADDR_WIDTH(14) // 14 bits (64KB) for 16384 words of 32 bits
    )imem_inst (
        .read_address(instr_addr),
        .instruction(instr_data)
    );

    data_mem #(
        .ADDR_WIDTH(14) // 14 bits (64KB) for 16384 words of 32 bits
    ) dmem_inst (
        .clk(clk),
        .addr_in(data_addr),
        .data_in(data_wdata),
        .write_enable(data_we),
        .read_enable(data_re),
        .data_out(data_rdata)
    );

endmodule
