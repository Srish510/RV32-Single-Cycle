`timescale 1ns/1ps

// ==============================================================================
// SRAM Macro Simulation Model
// 1024 words x 32-bit (4KB)
// Note: Do NOT synthesize this file. It is for simulation only.
// In synthesis, the memory compiler's .db/.lib file will provide this interface.
// ==============================================================================

module sram_macro_1024x32 (
    input  wire        CLK,
    input  wire        CEN,  // Chip Enable (Active Low)
    input  wire [3:0]  WEN,  // Byte Write Enable (Active Low)
    input  wire [9:0]  A,    // Address (1024 words)
    input  wire [31:0] D,    // Data In
    output reg  [31:0] Q     // Data Out
);

    reg [31:0] mem [0:1023];

    // Read Operation
    always @(posedge CLK) begin
        if (!CEN) begin
            Q <= mem[A];
        end
    end

    // Write Operation (Byte Masked)
    always @(posedge CLK) begin
        if (!CEN) begin
            if (!WEN[0]) mem[A][7:0]   <= D[7:0];
            if (!WEN[1]) mem[A][15:8]  <= D[15:8];
            if (!WEN[2]) mem[A][23:16] <= D[23:16];
            if (!WEN[3]) mem[A][31:24] <= D[31:24];
        end
    end

endmodule
