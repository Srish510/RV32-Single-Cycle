`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module alu(
    input wire [31:0] a,
    input wire [31:0] b,
    input wire [3:0] alu_op,
    output reg [31:0] alu_result,
    output reg zero,
    output reg carry_out,
    output reg overflow
);

    always @(*) begin
        carry_out = 1'b0;
        overflow  = 1'b0;
        case (alu_op)
            `ALU_ADD: begin             // ADD
                {carry_out, alu_result} = {1'b0, a} + {1'b0, b};
                overflow = (a[31] ^ b[31] ^ alu_result[31]) ^ carry_out;
            end
            `ALU_SUB: begin             // SUB
                {carry_out, alu_result} = {1'b0, a} - {1'b0, b};
                overflow = (a[31] ^ ~b[31] ^ alu_result[31]) ^ carry_out;
            end
            `ALU_AND: alu_result = a & b; // AND
            `ALU_OR: alu_result = a | b; // OR
            `ALU_XOR: alu_result = a ^ b; // XOR
            `ALU_SLL: alu_result = a << b[4:0]; // SLL
            `ALU_SRL: alu_result = a >> b[4:0]; // SRL
            `ALU_SRA: alu_result = $signed(a) >>> b[4:0]; // SRA
            `ALU_SLT: alu_result = ($signed(a) < $signed(b)) ? {31'b0,1'b1} : 32'b0; // SLT
            `ALU_SLTU: alu_result = (a < b) ? {31'b0,1'b1} : 32'b0; // SLTU
            default: alu_result = 32'b0; // Default case
        endcase

        zero = (alu_result == 32'b0) ? 1'b1 : 1'b0;     // Set zero flag if result is zero
    end

endmodule
