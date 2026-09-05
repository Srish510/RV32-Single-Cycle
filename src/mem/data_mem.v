`timescale 1ns/1ps

module data_mem #(
    parameter ADDR_WIDTH = 10 // 10 bits for 1024 words by default
)(
    input  wire        clk,
    /* verilator lint_off UNUSEDSIGNAL */
    input  wire [31:0] addr_in,
    /* verilator lint_on UNUSEDSIGNAL */
    input  wire [31:0] data_in,
    input  wire [3:0]  write_enable,
    input  wire        read_enable,
    output reg  [31:0] data_out
);

    // 4KB memory (1024 words of 32 bits)
    reg [31:0] memory [0:(1<<ADDR_WIDTH)-1];

    // Initialize memory to zero to avoid 'x' propagation
    integer i;
    initial begin
        for (i = 0; i < 1024; i = i + 1) begin
            memory[i] = 32'b0;
        end
    end

    wire [ADDR_WIDTH-1:0] word_addr = addr_in[2 +: ADDR_WIDTH];

    // Synchronous write with 4-bit byte-enable mask
    always @(posedge clk) begin
        if (write_enable[0]) memory[word_addr][7:0]   <= data_in[7:0];
        if (write_enable[1]) memory[word_addr][15:8]  <= data_in[15:8];
        if (write_enable[2]) memory[word_addr][23:16] <= data_in[23:16];
        if (write_enable[3]) memory[word_addr][31:24] <= data_in[31:24];
    end

    // Asynchronous read (common in single-cycle implementations)
    always @(*) begin
        if (read_enable) begin
            data_out = memory[word_addr];
        end else begin
            data_out = 32'b0;
        end
    end

endmodule
