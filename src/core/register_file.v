`timescale 1ns/1ps

module register_file(
    input wire clk,
    input wire [4:0] rs1,
    input wire [4:0] rs2,
    input wire [4:0] rd,
    input wire [31:0] write_data,
    input wire write_enable,
    output wire [31:0] read_data1,
    output wire [31:0] read_data2
);

    reg [31:0] registers [0:31]; // 32 registers of 32 bits each

    // No hardware reset: enables effcient inference during synthesis. Software (crt0) handles GPR initialization.
    always @(posedge clk) begin
        if (write_enable && (rd != 5'b00000)) begin
            registers[rd] <= write_data;
        end
    end

    // Read data from the specified registers
    assign read_data1 = (rs1 == 5'b00000) ? 32'b0 : registers[rs1];
    assign read_data2 = (rs2 == 5'b00000) ? 32'b0 : registers[rs2];

endmodule
