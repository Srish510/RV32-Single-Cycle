`timescale 1ns/1ps

module instr_mem #(
    parameter ADDR_WIDTH = 10 // 10 bits for 1024 words by default
)(
    /* verilator lint_off UNUSEDSIGNAL */
    input  wire [31:0] read_address,
    /* verilator lint_on UNUSEDSIGNAL */
    output wire [31:0] instruction
);

    // 4KB memory (1024 words of 32 bits)
    reg [31:0] memory [0:(1<<ADDR_WIDTH)-1];


    // Fetch instruction (assuming byte-addressable read_address)
    assign instruction = memory[read_address[2 +: ADDR_WIDTH]];

endmodule
