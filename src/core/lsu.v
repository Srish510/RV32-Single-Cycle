`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module lsu(
    /* verilator lint_off UNUSEDSIGNAL */
    input wire [31:0] addr_in,
    /* verilator lint_on UNUSEDSIGNAL */
    input wire [31:0] mem_read_data,
    input wire [31:0] reg_read_data,
    input wire [3:0] lsu_op,
    output reg mem_re,
    output reg [3:0] mem_we,
    output reg [31:0] mem_write_data,
    output reg [31:0] reg_write_data
);

    wire [7:0] extracted_byte;
    assign extracted_byte = (addr_in[1:0] == 2'b00) ? mem_read_data[7:0]   :
                            (addr_in[1:0] == 2'b01) ? mem_read_data[15:8]  :
                            (addr_in[1:0] == 2'b10) ? mem_read_data[23:16] :
                                                      mem_read_data[31:24];

    wire [15:0] extracted_halfword;
    assign extracted_halfword = (addr_in[1] == 1'b0) ? mem_read_data[15:0] : mem_read_data[31:16];

    wire [31:0] extracted_word;
    assign extracted_word = mem_read_data; 

    always @(*) begin
        mem_re = 1'b0;
        mem_we = 4'b0000;
        mem_write_data = 32'b0;
        reg_write_data = 32'b0;

        case (lsu_op)
            `LSU_LB: begin
                mem_re = 1'b1;
                reg_write_data = {{24{extracted_byte[7]}}, extracted_byte}; // Sign-extend byte
            end
            `LSU_LH: begin
                mem_re = 1'b1;
                reg_write_data = {{16{extracted_halfword[15]}}, extracted_halfword}; // Sign-extend halfword
            end
            `LSU_LW: begin
                mem_re = 1'b1;
                reg_write_data = extracted_word; // Load word
            end
            `LSU_LBU: begin
                mem_re = 1'b1;
                reg_write_data = {24'b0, extracted_byte}; // Zero-extend byte
            end
            `LSU_LHU: begin
                mem_re = 1'b1;
                reg_write_data = {16'b0, extracted_halfword}; // Zero-extend halfword
            end
            `LSU_SB: begin                                          // Write byte
                mem_we = (addr_in[1:0] == 2'b00) ? 4'b0001:   //Write Enable Mask
                         (addr_in[1:0] == 2'b01) ? 4'b0010:
                         (addr_in[1:0] == 2'b10) ? 4'b0100: 
                                                   4'b1000; 

                mem_write_data = {reg_read_data[7:0], reg_read_data[7:0], reg_read_data[7:0], reg_read_data[7:0]};
            end
            `LSU_SH: begin                                          // Write halfword
                mem_we = (addr_in[1] == 1'b0) ? 4'b0011 : 4'b1100; // Write Enable Mask
                mem_write_data = {reg_read_data[15:0], reg_read_data[15:0]};
            end
            `LSU_SW: begin                                         // Write word
                mem_we = 4'b1111; 
                mem_write_data = reg_read_data;
            end
            default: begin
                // No operation for unsupported LSU operations
            end
        endcase
    end

endmodule
