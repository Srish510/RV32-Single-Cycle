`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

//==============================================================================
// Formal Verification Harness: PC Controller, Branch Unit & PC Writeback Mux
// (Verilog-2005)
// Mathematically proves next-PC control flow multiplexing, JALR LSB clearing,
// branch condition evaluation, and 4-byte alignment preservation.
//==============================================================================
module formal_branch_pc (
    input wire        clk,
    input wire [31:0] pc,
    input wire [31:0] offset,
    input wire        lt_flag,
    input wire        eq_flag,
    input wire [2:0]  branch_op,
    input wire [1:0]  next_pc_src,
    input wire [31:0] jalr_pc,
    input wire        pc_writeback_src
);

    wire [31:0] next_pc;
    wire [31:0] offset_pc;
    wire [31:0] pc_incremented;
    wire [31:0] pc_writeback;

    // Instantiate DUT: PC Controller (includes branch_unit and pc_src_mux)
    pc_controller u_pc_ctrl (
        .pc             (pc),
        .offset         (offset),
        .lt_flag        (lt_flag),
        .eq_flag        (eq_flag),
        .branch_op      (branch_op),
        .next_pc_src    (next_pc_src),
        .jalr_pc        (jalr_pc),
        .next_pc        (next_pc),
        .offset_pc      (offset_pc),
        .pc_incremented (pc_incremented)
    );

    // Instantiate DUT: PC Writeback Mux
    pc_writeback_mux u_pc_wb_mux (
        .offset_pc        (offset_pc),
        .pc_incremented   (pc_incremented),
        .pc_writeback_src (pc_writeback_src),
        .pc_writeback     (pc_writeback)
    );

`ifdef FORMAL
    always @(*) begin
        //----------------------------------------------------------------------
        // 1. Continuous Adder Invariants
        //----------------------------------------------------------------------
        assert (pc_incremented == (pc + 32'd4));
        assert (offset_pc      == (pc + offset));

`ifdef FORMAL_BUG_INJECT
        // Intentional false assertion for fault injection demonstration
        assert (!(next_pc_src == `PC_SEL_JALR && jalr_pc[0] == 1'b1));
`endif

        //----------------------------------------------------------------------
        // 2. Next-PC Multiplexer & JALR LSB Masking Proofs
        //----------------------------------------------------------------------
        if (next_pc_src == `PC_SEL_INC) begin
            assert (next_pc == (pc + 32'd4));
        end

        if (next_pc_src == `PC_SEL_JAL) begin
            assert (next_pc == (pc + offset));
        end

        if (next_pc_src == `PC_SEL_JALR) begin
            // RISC-V Spec 2.5: JALR clears the least-significant bit of target address
            assert (next_pc[0]    == 1'b0);
            assert (next_pc[31:1] == jalr_pc[31:1]);
            assert (next_pc       == (jalr_pc & 32'hFFFF_FFFE));
        end

        //----------------------------------------------------------------------
        // 3. Branch Decision Unit Proofs
        //----------------------------------------------------------------------
        if (next_pc_src == `PC_SEL_BRANCH) begin
            assert (next_pc == (pc + 32'd4) || next_pc == (pc + offset));

            if (branch_op == `BRANCH_NONE) begin
                assert (next_pc == (pc + 32'd4));
            end
            if (branch_op == `BRANCH_BEQ) begin
                assert (next_pc == (eq_flag ? (pc + offset) : (pc + 32'd4)));
            end
            if (branch_op == `BRANCH_BNE) begin
                assert (next_pc == (!eq_flag ? (pc + offset) : (pc + 32'd4)));
            end
            if (branch_op == `BRANCH_BLT) begin
                assert (next_pc == (lt_flag ? (pc + offset) : (pc + 32'd4)));
            end
            if (branch_op == `BRANCH_BGE) begin
                assert (next_pc == (!lt_flag ? (pc + offset) : (pc + 32'd4)));
            end
            if (branch_op > `BRANCH_BGE) begin
                assert (next_pc == (pc + 32'd4));
            end
        end

        //----------------------------------------------------------------------
        // 4. 4-Byte Alignment Preservation Theorem
        //----------------------------------------------------------------------
        if (pc[1:0] == 2'b00 && offset[1:0] == 2'b00) begin
            if (next_pc_src != `PC_SEL_JALR || jalr_pc[1] == 1'b0) begin
                assert (next_pc[1:0] == 2'b00);
            end
        end

        //----------------------------------------------------------------------
        // 5. PC Writeback Mux Proofs (Link Address vs AUIPC Target)
        //----------------------------------------------------------------------
        if (pc_writeback_src == `PC_WB_SEL_INC) begin
            assert (pc_writeback == (pc + 32'd4));
        end else begin
            assert (pc_writeback == (pc + offset));
        end
    end

    //--------------------------------------------------------------------------
    // 6. Reachability / Witness Cover Properties
    //--------------------------------------------------------------------------
    always @(posedge clk) begin
        cover (next_pc_src == `PC_SEL_JALR   && jalr_pc[0] == 1'b1 && next_pc[0] == 1'b0);
        cover (next_pc_src == `PC_SEL_BRANCH && branch_op == `BRANCH_BEQ && eq_flag  && offset != 32'd4);
        cover (next_pc_src == `PC_SEL_BRANCH && branch_op == `BRANCH_BNE && !eq_flag && offset != 32'd4);
        cover (next_pc_src == `PC_SEL_BRANCH && branch_op == `BRANCH_BLT && lt_flag  && offset[31] == 1'b1);
        cover (next_pc_src == `PC_SEL_BRANCH && branch_op == `BRANCH_BGE && !lt_flag && offset[31] == 1'b1);
        cover (next_pc_src == `PC_SEL_JAL    && offset[31] == 1'b1);
    end
`endif

endmodule
