`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

//==============================================================================
// RISC-V Formal Interface (RVFI) Wrapper for rv32i_core (Pure Verilog-2005)
// Exposes the standard riscv-formal RVFI trace port bundle alongside live
// combinational taps from rv32i_core (via Yosys `expose` pass).
//==============================================================================
module rv32i_rvfi_wrapper (
    input  wire        clk,
    input  wire        rst,

    // Instruction Memory Interface
    output wire [31:0] instr_addr,
    input  wire [31:0] instr_data,

    // Data Memory Interface
    output wire [31:0] data_addr,
    output wire [31:0] data_wdata,
    output wire [3:0]  data_we,
    output wire        data_re,
    input  wire [31:0] data_rdata,

    // Combinational Core Taps
    output wire [31:0] comb_next_pc,
    output wire        comb_reg_write,
    output wire [31:0] comb_write_data,
    output wire [31:0] comb_rs1_rdata,
    output wire [31:0] comb_rs2_rdata,

    // Standard RISC-V Formal Interface (RVFI) Outputs (Registered on Commit)
    output reg         rvfi_valid,
    output reg  [63:0] rvfi_order,
    output reg  [31:0] rvfi_insn,
    output reg         rvfi_trap,
    output reg         rvfi_halt,
    output reg         rvfi_intr,
    output reg  [1:0]  rvfi_mode,
    output reg  [1:0]  rvfi_ixl,
    output reg  [4:0]  rvfi_rs1_addr,
    output reg  [4:0]  rvfi_rs2_addr,
    output reg  [31:0] rvfi_rs1_rdata,
    output reg  [31:0] rvfi_rs2_rdata,
    output reg  [4:0]  rvfi_rd_addr,
    output reg  [31:0] rvfi_rd_wdata,
    output reg  [31:0] rvfi_pc_rdata,
    output reg  [31:0] rvfi_pc_wdata,
    output reg  [31:0] rvfi_mem_addr,
    output reg  [3:0]  rvfi_mem_rmask,
    output reg  [3:0]  rvfi_mem_wmask,
    output reg  [31:0] rvfi_mem_rdata,
    output reg  [31:0] rvfi_mem_wdata
);

    wire [31:0] core_next_pc;
    wire        core_reg_write;
    wire [31:0] core_write_data;
    wire [31:0] core_read_data1;
    wire [31:0] core_read_data2;

    assign comb_next_pc    = core_next_pc;
    assign comb_reg_write  = core_reg_write;
    assign comb_write_data = core_write_data;
    assign comb_rs1_rdata  = core_read_data1;
    assign comb_rs2_rdata  = core_read_data2;

    // Instantiate unmodified rv32i_core (internal wires exposed by Yosys `expose`)
    rv32i_core u_core (
        .clk        (clk),
        .rst        (rst),
        .instr_addr (instr_addr),
        .instr_data (instr_data),
        .data_addr  (data_addr),
        .data_wdata (data_wdata),
        .data_we    (data_we),
        .data_re    (data_re),
        .data_rdata (data_rdata),
        .next_pc    (core_next_pc),
        .reg_write  (core_reg_write),
        .write_data (core_write_data),
        .read_data1 (core_read_data1),
        .read_data2 (core_read_data2)
    );

    wire [6:0] opcode = instr_data[6:0];
    wire [2:0] funct3 = instr_data[14:12];
    wire [4:0] rs1    = instr_data[19:15];
    wire [4:0] rs2    = instr_data[24:20];
    wire [4:0] rd     = instr_data[11:7];

    // Determine whether the current instruction format reads rs1 / rs2
    wire uses_rs1 = (opcode == `OPCODE_R_TYPE) ||
                    (opcode == `OPCODE_OP_IMM) ||
                    (opcode == `OPCODE_LOAD)   ||
                    (opcode == `OPCODE_STORE)  ||
                    (opcode == `OPCODE_BRANCH) ||
                    (opcode == `OPCODE_JALR);

    wire uses_rs2 = (opcode == `OPCODE_R_TYPE) ||
                    (opcode == `OPCODE_STORE)  ||
                    (opcode == `OPCODE_BRANCH);

    // Compute RVFI memory read byte mask
    reg [3:0] calc_rmask;
    always @(*) begin
        calc_rmask = 4'b0000;
        if (data_re) begin
            case (funct3)
                `FUNCT3_LB, `FUNCT3_LBU: calc_rmask = (4'b0001 << data_addr[1:0]);
                `FUNCT3_LH, `FUNCT3_LHU: calc_rmask = data_addr[1] ? 4'b1100 : 4'b0011;
                `FUNCT3_LW:              calc_rmask = 4'b1111;
                default:                 calc_rmask = 4'b0000;
            endcase
        end
    end

    initial begin
        rvfi_valid     = 1'b0;
        rvfi_order     = 64'd0;
        rvfi_insn      = 32'd0;
        rvfi_trap      = 1'b0;
        rvfi_halt      = 1'b0;
        rvfi_intr      = 1'b0;
        rvfi_mode      = 2'd3;
        rvfi_ixl       = 2'd1;
        rvfi_rs1_addr  = 5'd0;
        rvfi_rs2_addr  = 5'd0;
        rvfi_rs1_rdata = 32'd0;
        rvfi_rs2_rdata = 32'd0;
        rvfi_rd_addr   = 5'd0;
        rvfi_rd_wdata  = 32'd0;
        rvfi_pc_rdata  = 32'd0;
        rvfi_pc_wdata  = 32'd0;
        rvfi_mem_addr  = 32'd0;
        rvfi_mem_rmask = 4'd0;
        rvfi_mem_wmask = 4'd0;
        rvfi_mem_rdata = 32'd0;
        rvfi_mem_wdata = 32'd0;
    end

    always @(posedge clk) begin
        if (rst) begin
            rvfi_valid     <= 1'b0;
            rvfi_order     <= 64'd0;
            rvfi_insn      <= 32'd0;
            rvfi_trap      <= 1'b0;
            rvfi_halt      <= 1'b0;
            rvfi_intr      <= 1'b0;
            rvfi_mode      <= 2'd3;
            rvfi_ixl       <= 2'd1;
            rvfi_rs1_addr  <= 5'd0;
            rvfi_rs2_addr  <= 5'd0;
            rvfi_rs1_rdata <= 32'd0;
            rvfi_rs2_rdata <= 32'd0;
            rvfi_rd_addr   <= 5'd0;
            rvfi_rd_wdata  <= 32'd0;
            rvfi_pc_rdata  <= 32'd0;
            rvfi_pc_wdata  <= 32'd0;
            rvfi_mem_addr  <= 32'd0;
            rvfi_mem_rmask <= 4'd0;
            rvfi_mem_wmask <= 4'd0;
            rvfi_mem_rdata <= 32'd0;
            rvfi_mem_wdata <= 32'd0;
        end else begin
            rvfi_valid     <= 1'b1;
            rvfi_order     <= rvfi_order + 64'd1;
            rvfi_insn      <= instr_data;
            rvfi_trap      <= 1'b0;
            rvfi_halt      <= 1'b0;
            rvfi_intr      <= 1'b0;
            rvfi_mode      <= 2'd3;
            rvfi_ixl       <= 2'd1;
            rvfi_rs1_addr  <= uses_rs1 ? rs1 : 5'd0;
            rvfi_rs2_addr  <= uses_rs2 ? rs2 : 5'd0;
            rvfi_rs1_rdata <= uses_rs1 ? core_read_data1 : 32'd0;
            rvfi_rs2_rdata <= uses_rs2 ? core_read_data2 : 32'd0;
            rvfi_rd_addr   <= core_reg_write ? rd : 5'd0;
            // Per RVFI specification: rvfi_rd_wdata MUST be 0 when rvfi_rd_addr == 0
            rvfi_rd_wdata  <= (core_reg_write && (rd != 5'd0)) ? core_write_data : 32'd0;
            rvfi_pc_rdata  <= instr_addr;
            rvfi_pc_wdata  <= core_next_pc;
            rvfi_mem_addr  <= (data_re || (|data_we)) ? data_addr : 32'd0;
            rvfi_mem_rmask <= calc_rmask;
            rvfi_mem_wmask <= data_we;
            rvfi_mem_rdata <= data_re ? data_rdata : 32'd0;
            rvfi_mem_wdata <= (|data_we) ? data_wdata : 32'd0;
        end
    end

endmodule
