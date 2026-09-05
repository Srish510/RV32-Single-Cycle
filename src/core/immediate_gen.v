`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

module immediate_gen(
    input wire [31:0] instruction,
    output reg [31:0] imm_out
);

    always @(*) begin
        case (instruction[6:0])
            `OPCODE_OP_IMM, `OPCODE_LOAD, `OPCODE_JALR: begin // I-type
                imm_out = {{20{instruction[31]}}, instruction[31:20]};
            end
            `OPCODE_STORE: begin // S-type
                imm_out = {{20{instruction[31]}}, instruction[31:25], instruction[11:7]};
            end
            `OPCODE_BRANCH: begin // B-type
                imm_out = {{19{instruction[31]}}, instruction[31], instruction[7], instruction[30:25], instruction[11:8], 1'b0};
            end
            `OPCODE_LUI, `OPCODE_AUIPC: begin // U-type
                imm_out = {instruction[31:12], 12'b0};
            end
            `OPCODE_JAL: begin // J-type
                imm_out = {{11{instruction[31]}}, instruction[31], instruction[19:12], instruction[20], instruction[30:21], 1'b0};
            end
            default: begin // Default case for unsupported opcodes
                imm_out = 32'b0;
            end
        endcase
    end

endmodule
