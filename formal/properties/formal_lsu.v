`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

//==============================================================================
// Formal Verification Harness: Load-Store Unit (LSU) (Verilog-2005)
// Mathematically proves read/write mutual exclusion, byte/halfword lane
// extraction, sign/zero extension, and store byte-enable mask legality.
//==============================================================================
module formal_lsu (
    input wire        clk,
    input wire [31:0] addr_in,
    input wire [31:0] mem_read_data,
    input wire [31:0] reg_read_data,
    input wire [3:0]  lsu_op
);

    wire        mem_re;
    wire [3:0]  mem_we;
    wire [31:0] mem_write_data;
    wire [31:0] reg_write_data;

    // Instantiate DUT: Load-Store Unit
    lsu u_lsu (
        .addr_in        (addr_in),
        .mem_read_data  (mem_read_data),
        .reg_read_data  (reg_read_data),
        .lsu_op         (lsu_op),
        .mem_re         (mem_re),
        .mem_we         (mem_we),
        .mem_write_data (mem_write_data),
        .reg_write_data (reg_write_data)
    );

    wire is_load_op  = (lsu_op == `LSU_LB)  || (lsu_op == `LSU_LH)  ||
                       (lsu_op == `LSU_LW)  || (lsu_op == `LSU_LBU) ||
                       (lsu_op == `LSU_LHU);

    wire is_store_op = (lsu_op == `LSU_SB)  || (lsu_op == `LSU_SH)  ||
                       (lsu_op == `LSU_SW);

    wire is_legal_we = (mem_we == 4'b0000) ||
                       (mem_we == 4'b0001) || (mem_we == 4'b0010) ||
                       (mem_we == 4'b0100) || (mem_we == 4'b1000) ||
                       (mem_we == 4'b0011) || (mem_we == 4'b1100) ||
                       (mem_we == 4'b1111);

`ifdef FORMAL
    always @(*) begin
        //----------------------------------------------------------------------
        // 1. Read/Write Mutual Exclusion & Byte-Mask Legality
        //----------------------------------------------------------------------
        assert (!(mem_re && (|mem_we)));
        assert (is_legal_we);
        assert (mem_re == is_load_op);
        assert ((|mem_we) == is_store_op);

`ifdef FORMAL_BUG_INJECT
        // Intentional false assertion for fault injection demonstration
        assert (!(lsu_op == `LSU_SB && addr_in[1:0] == 2'b11));
`endif

        //----------------------------------------------------------------------
        // 2. Load Sign-Extension, Zero-Extension & Lane Alignment Proofs
        //----------------------------------------------------------------------
        if (lsu_op == `LSU_LB) begin
            assert (mem_re && mem_we == 4'b0000);
            assert (reg_write_data[31:7] == {25{reg_write_data[7]}});
            if (addr_in[1:0] == 2'b00) assert (reg_write_data[7:0] == mem_read_data[7:0]);
            if (addr_in[1:0] == 2'b01) assert (reg_write_data[7:0] == mem_read_data[15:8]);
            if (addr_in[1:0] == 2'b10) assert (reg_write_data[7:0] == mem_read_data[23:16]);
            if (addr_in[1:0] == 2'b11) assert (reg_write_data[7:0] == mem_read_data[31:24]);
        end

        if (lsu_op == `LSU_LBU) begin
            assert (mem_re && mem_we == 4'b0000);
            assert (reg_write_data[31:8] == 24'b0);
            if (addr_in[1:0] == 2'b00) assert (reg_write_data[7:0] == mem_read_data[7:0]);
            if (addr_in[1:0] == 2'b01) assert (reg_write_data[7:0] == mem_read_data[15:8]);
            if (addr_in[1:0] == 2'b10) assert (reg_write_data[7:0] == mem_read_data[23:16]);
            if (addr_in[1:0] == 2'b11) assert (reg_write_data[7:0] == mem_read_data[31:24]);
        end

        if (lsu_op == `LSU_LH) begin
            assert (mem_re && mem_we == 4'b0000);
            assert (reg_write_data[31:15] == {17{reg_write_data[15]}});
            if (addr_in[1] == 1'b0) assert (reg_write_data[15:0] == mem_read_data[15:0]);
            if (addr_in[1] == 1'b1) assert (reg_write_data[15:0] == mem_read_data[31:16]);
        end

        if (lsu_op == `LSU_LHU) begin
            assert (mem_re && mem_we == 4'b0000);
            assert (reg_write_data[31:16] == 16'b0);
            if (addr_in[1] == 1'b0) assert (reg_write_data[15:0] == mem_read_data[15:0]);
            if (addr_in[1] == 1'b1) assert (reg_write_data[15:0] == mem_read_data[31:16]);
        end

        if (lsu_op == `LSU_LW) begin
            assert (mem_re && mem_we == 4'b0000);
            assert (reg_write_data == mem_read_data);
        end

        //----------------------------------------------------------------------
        // 3. Store Byte-Enable & Data Replication Proofs
        //----------------------------------------------------------------------
        if (lsu_op == `LSU_SB) begin
            assert (!mem_re);
            assert (mem_we == (4'b0001 << addr_in[1:0]));
            if (addr_in[1:0] == 2'b00) assert (mem_write_data[7:0]   == reg_read_data[7:0]);
            if (addr_in[1:0] == 2'b01) assert (mem_write_data[15:8]  == reg_read_data[7:0]);
            if (addr_in[1:0] == 2'b10) assert (mem_write_data[23:16] == reg_read_data[7:0]);
            if (addr_in[1:0] == 2'b11) assert (mem_write_data[31:24] == reg_read_data[7:0]);
        end

        if (lsu_op == `LSU_SH) begin
            assert (!mem_re);
            if (addr_in[1] == 1'b0) begin
                assert (mem_we == 4'b0011);
                assert (mem_write_data[15:0] == reg_read_data[15:0]);
            end else begin
                assert (mem_we == 4'b1100);
                assert (mem_write_data[31:16] == reg_read_data[15:0]);
            end
        end

        if (lsu_op == `LSU_SW) begin
            assert (!mem_re);
            assert (mem_we == 4'b1111);
            assert (mem_write_data == reg_read_data);
        end

        if (!is_load_op && !is_store_op) begin
            assert (!mem_re && mem_we == 4'b0000 && mem_write_data == 32'b0 && reg_write_data == 32'b0);
        end
    end

    //--------------------------------------------------------------------------
    // 4. Reachability / Witness Cover Properties
    //--------------------------------------------------------------------------
    always @(posedge clk) begin
        cover (lsu_op == `LSU_LB  && addr_in[1:0] == 2'b11 && reg_write_data[31] == 1'b1);
        cover (lsu_op == `LSU_LBU && addr_in[1:0] == 2'b11 && mem_read_data[31] == 1'b1 && reg_write_data[31] == 1'b0);
        cover (lsu_op == `LSU_LH  && addr_in[1]   == 1'b1  && reg_write_data[31] == 1'b1);
        cover (lsu_op == `LSU_SB  && addr_in[1:0] == 2'b10 && mem_we == 4'b0100);
        cover (lsu_op == `LSU_SH  && addr_in[1]   == 1'b1  && mem_we == 4'b1100);
        cover (lsu_op == `LSU_SW  && mem_we == 4'b1111);
    end
`endif

endmodule
