`timescale 1ns/1ps

// ==============================================================================
// ASIC Top-Level Module
// Instantiates the RV32I Core and the On-Chip SRAM macros.
// During synthesis, the SRAM macros are treated as black boxes.
// ==============================================================================

module rv32i_asic_top (
    input wire clk,
    input wire rst
);

    // ------------------------------------------------------------------------
    // Interconnect Wires
    // ------------------------------------------------------------------------
    wire [31:0] instr_addr;
    wire [31:0] instr_data;

    wire [31:0] data_addr;
    wire [31:0] data_wdata;
    wire [3:0]  data_we;
    wire        data_re;
    wire [31:0] data_rdata;

    // ------------------------------------------------------------------------
    // Core Instantiation
    // ------------------------------------------------------------------------
    rv32i_core core_inst (
        .clk        (clk),
        .rst        (rst),
        .instr_addr (instr_addr),
        .instr_data (instr_data),
        .data_addr  (data_addr),
        .data_wdata (data_wdata),
        .data_we    (data_we),
        .data_re    (data_re),
        .data_rdata (data_rdata)
    );

    // ------------------------------------------------------------------------
    // On-Chip SRAM (Instruction Memory)
    // 4KB (1024 x 32-bit)
    // ------------------------------------------------------------------------
    // In a physical design flow, this is replaced by a memory compiler macro.
    sram_macro_1024x32 imem_macro (
        .CLK   (clk),
        .CEN   (1'b0),             // Chip Enable (Active Low)
        .WEN   (4'b1111),          // Write Enable (Active Low) - All 1s = Read Only
        .A     (instr_addr[11:2]), // Word address
        .D     (32'h00000000),
        .Q     (instr_data)
    );

    // ------------------------------------------------------------------------
    // On-Chip SRAM (Data Memory)
    // 4KB (1024 x 32-bit)
    // ------------------------------------------------------------------------
    sram_macro_1024x32 dmem_macro (
        .CLK   (clk),
        .CEN   (~(data_re | (|data_we))), // Enable when reading or writing
        .WEN   (~data_we),                // Write Enable per byte (Active Low)
        .A     (data_addr[11:2]),         // Word address
        .D     (data_wdata),
        .Q     (data_rdata)
    );

endmodule
