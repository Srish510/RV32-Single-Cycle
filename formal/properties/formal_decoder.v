`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

//==============================================================================
// Formal Verification Harness: Main Decoder & Immediate Generator (Verilog-2005)
// Mathematically proves control signal decoding, mutual exclusion, illegal
// opcode safe-NOP fallback, and immediate sign-extension across all 2^32
// possible 32-bit instruction encodings.
//==============================================================================
module formal_decoder (
    input wire        clk,
    input wire [31:0] instruction
);

    wire [1:0]  next_pc_src;
    wire        pc_writeback_src;
    wire [2:0]  branch_op;
    wire [1:0]  reg_src;
    wire [3:0]  lsu_op;
    wire        alu_src;
    wire [3:0]  alu_op;
    wire        reg_write;
    wire [31:0] imm_out;

    // Instantiate DUT: Main Decoder
    main_decoder u_decoder (
        .instruction      (instruction),
        .next_pc_src      (next_pc_src),
        .pc_writeback_src (pc_writeback_src),
        .branch_op        (branch_op),
        .reg_src          (reg_src),
        .lsu_op           (lsu_op),
        .alu_src          (alu_src),
        .alu_op           (alu_op),
        .reg_write        (reg_write)
    );

    // Instantiate DUT: Immediate Generator
    immediate_gen u_imm_gen (
        .instruction      (instruction),
        .imm_out          (imm_out)
    );

    wire [6:0] opcode = instruction[6:0];
    wire [2:0] funct3 = instruction[14:12];
    wire [6:0] funct7 = instruction[31:25];

    wire is_valid_opcode = (opcode == `OPCODE_R_TYPE) ||
                           (opcode == `OPCODE_OP_IMM) ||
                           (opcode == `OPCODE_LOAD)   ||
                           (opcode == `OPCODE_STORE)  ||
                           (opcode == `OPCODE_BRANCH) ||
                           (opcode == `OPCODE_JAL)    ||
                           (opcode == `OPCODE_JALR)   ||
                           (opcode == `OPCODE_LUI)    ||
                           (opcode == `OPCODE_AUIPC);

    wire is_load_lsu  = (lsu_op == `LSU_LB)  || (lsu_op == `LSU_LH)  ||
                        (lsu_op == `LSU_LW)  || (lsu_op == `LSU_LBU) ||
                        (lsu_op == `LSU_LHU);

    wire is_store_lsu = (lsu_op == `LSU_SB)  || (lsu_op == `LSU_SH)  ||
                        (lsu_op == `LSU_SW);

    wire is_valid_alu_op = (alu_op == `ALU_ADD)  || (alu_op == `ALU_SUB) ||
                           (alu_op == `ALU_AND)  || (alu_op == `ALU_OR)  ||
                           (alu_op == `ALU_XOR)  || (alu_op == `ALU_SLL) ||
                           (alu_op == `ALU_SRL)  || (alu_op == `ALU_SRA) ||
                           (alu_op == `ALU_SLT)  || (alu_op == `ALU_SLTU);

`ifdef FORMAL
    always @(*) begin
        //----------------------------------------------------------------------
        // 1. Control Signal Encoding Validity Invariants
        //----------------------------------------------------------------------
        assert (is_valid_alu_op);
        assert (branch_op <= `BRANCH_BGE);
        assert (lsu_op == `LSU_NONE || is_load_lsu || is_store_lsu);

        //----------------------------------------------------------------------
        // 2. Mutual Exclusion & Architectural Safety Invariants
        //----------------------------------------------------------------------
        // Load and Store LSU codes are mutually exclusive
        assert (!(is_load_lsu && is_store_lsu));

`ifdef FORMAL_BUG_INJECT
        // Intentional false assertion for fault injection demonstration
        assert (!(opcode == `OPCODE_STORE && funct3 == `FUNCT3_SW));
`endif

        // Store instructions never write to the register file
        assert (opcode != `OPCODE_STORE || !reg_write);
        assert (!is_store_lsu || (opcode == `OPCODE_STORE && !reg_write));
        assert (!is_load_lsu  || (opcode == `OPCODE_LOAD  &&  reg_write));

        // Branch instructions never write to register file or access data memory
        assert (opcode != `OPCODE_BRANCH || (!reg_write && lsu_op == `LSU_NONE));

        // Control flow source bi-implications
        assert ((next_pc_src == `PC_SEL_BRANCH) == (opcode == `OPCODE_BRANCH));
        assert ((next_pc_src == `PC_SEL_JAL)    == (opcode == `OPCODE_JAL));
        assert ((next_pc_src == `PC_SEL_JALR)   == (opcode == `OPCODE_JALR));
        assert ((branch_op == `BRANCH_NONE)     || (opcode == `OPCODE_BRANCH));

        // Writeback mux source bi-implications
        assert ((reg_src == `WB_SEL_MEM)     == (opcode == `OPCODE_LOAD));
        assert ((reg_src == `WB_SEL_UPP_IMM) == (opcode == `OPCODE_LUI));
        assert ((reg_src == `WB_SEL_PC_NEXT) ==
                (opcode == `OPCODE_JAL || opcode == `OPCODE_JALR || opcode == `OPCODE_AUIPC));
        assert ((pc_writeback_src == `PC_WB_SEL_OFFSET) == (opcode == `OPCODE_AUIPC));

        // ALU Operand B source selection
        assert (!(opcode == `OPCODE_R_TYPE || opcode == `OPCODE_BRANCH) || (alu_src == `ALU_SRC_REG));
        assert (!(opcode == `OPCODE_OP_IMM || opcode == `OPCODE_LOAD ||
                  opcode == `OPCODE_STORE  || opcode == `OPCODE_JALR ||
                  opcode == `OPCODE_LUI    || opcode == `OPCODE_AUIPC) || (alu_src == `ALU_SRC_IMM));

        //----------------------------------------------------------------------
        // 3. Unimplemented / Illegal Opcode Safe-NOP Invariant
        //    (Includes ECALL/EBREAK 0x73, FENCE 0x0F, and all reserved opcodes)
        //----------------------------------------------------------------------
        if (!is_valid_opcode) begin
            assert (reg_write == `REG_WRITE_DISABLE);
            assert (lsu_op == `LSU_NONE);
            assert (next_pc_src == `PC_SEL_INC);
            assert (branch_op == `BRANCH_NONE);
            assert (imm_out == 32'b0);
        end

        //----------------------------------------------------------------------
        // 4. Exact Decoding Proofs for All 37 Base RV32I Instructions
        //----------------------------------------------------------------------
        if (opcode == `OPCODE_R_TYPE) begin
            assert (reg_write && alu_src == `ALU_SRC_REG && reg_src == `WB_SEL_REG &&
                    lsu_op == `LSU_NONE && next_pc_src == `PC_SEL_INC);
            if (funct7 == `FUNCT7_BASE && funct3 == `FUNCT3_ADD_SUB) assert (alu_op == `ALU_ADD);
            if (funct7 == `FUNCT7_ALT  && funct3 == `FUNCT3_ADD_SUB) assert (alu_op == `ALU_SUB);
            if (funct7 == `FUNCT7_BASE && funct3 == `FUNCT3_SLL)     assert (alu_op == `ALU_SLL);
            if (funct7 == `FUNCT7_BASE && funct3 == `FUNCT3_SLT)     assert (alu_op == `ALU_SLT);
            if (funct7 == `FUNCT7_BASE && funct3 == `FUNCT3_SLTU)    assert (alu_op == `ALU_SLTU);
            if (funct7 == `FUNCT7_BASE && funct3 == `FUNCT3_XOR)     assert (alu_op == `ALU_XOR);
            if (funct7 == `FUNCT7_BASE && funct3 == `FUNCT3_SRL_SRA) assert (alu_op == `ALU_SRL);
            if (funct7 == `FUNCT7_ALT  && funct3 == `FUNCT3_SRL_SRA) assert (alu_op == `ALU_SRA);
            if (funct7 == `FUNCT7_BASE && funct3 == `FUNCT3_OR)      assert (alu_op == `ALU_OR);
            if (funct7 == `FUNCT7_BASE && funct3 == `FUNCT3_AND)     assert (alu_op == `ALU_AND);
        end

        if (opcode == `OPCODE_OP_IMM) begin
            assert (reg_write && alu_src == `ALU_SRC_IMM && reg_src == `WB_SEL_REG &&
                    lsu_op == `LSU_NONE && next_pc_src == `PC_SEL_INC);
            if (funct3 == `FUNCT3_ADD_SUB)                           assert (alu_op == `ALU_ADD);
            if (funct3 == `FUNCT3_SLT)                               assert (alu_op == `ALU_SLT);
            if (funct3 == `FUNCT3_SLTU)                              assert (alu_op == `ALU_SLTU);
            if (funct3 == `FUNCT3_XOR)                               assert (alu_op == `ALU_XOR);
            if (funct3 == `FUNCT3_OR)                                assert (alu_op == `ALU_OR);
            if (funct3 == `FUNCT3_AND)                               assert (alu_op == `ALU_AND);
            if (funct3 == `FUNCT3_SLL)                               assert (alu_op == `ALU_SLL);
            if (funct3 == `FUNCT3_SRL_SRA && funct7 == `FUNCT7_BASE) assert (alu_op == `ALU_SRL);
            if (funct3 == `FUNCT3_SRL_SRA && funct7 == `FUNCT7_ALT)  assert (alu_op == `ALU_SRA);
        end

        if (opcode == `OPCODE_LOAD) begin
            assert (reg_write && alu_src == `ALU_SRC_IMM && alu_op == `ALU_ADD &&
                    reg_src == `WB_SEL_MEM && next_pc_src == `PC_SEL_INC);
            if (funct3 == `FUNCT3_LB)  assert (lsu_op == `LSU_LB);
            if (funct3 == `FUNCT3_LH)  assert (lsu_op == `LSU_LH);
            if (funct3 == `FUNCT3_LW)  assert (lsu_op == `LSU_LW);
            if (funct3 == `FUNCT3_LBU) assert (lsu_op == `LSU_LBU);
            if (funct3 == `FUNCT3_LHU) assert (lsu_op == `LSU_LHU);
        end

        if (opcode == `OPCODE_STORE) begin
            assert (!reg_write && alu_src == `ALU_SRC_IMM && alu_op == `ALU_ADD &&
                    next_pc_src == `PC_SEL_INC);
            if (funct3 == `FUNCT3_SB) assert (lsu_op == `LSU_SB);
            if (funct3 == `FUNCT3_SH) assert (lsu_op == `LSU_SH);
            if (funct3 == `FUNCT3_SW) assert (lsu_op == `LSU_SW);
        end

        if (opcode == `OPCODE_BRANCH) begin
            if (funct3 == `FUNCT3_BEQ)  assert (branch_op == `BRANCH_BEQ && alu_op == `ALU_SUB);
            if (funct3 == `FUNCT3_BNE)  assert (branch_op == `BRANCH_BNE && alu_op == `ALU_SUB);
            if (funct3 == `FUNCT3_BLT)  assert (branch_op == `BRANCH_BLT && alu_op == `ALU_SLT);
            if (funct3 == `FUNCT3_BGE)  assert (branch_op == `BRANCH_BGE && alu_op == `ALU_SLT);
            if (funct3 == `FUNCT3_BLTU) assert (branch_op == `BRANCH_BLT && alu_op == `ALU_SLTU);
            if (funct3 == `FUNCT3_BGEU) assert (branch_op == `BRANCH_BGE && alu_op == `ALU_SLTU);
        end

        //----------------------------------------------------------------------
        // 5. Immediate Generator Format & Sign-Extension Invariants
        //----------------------------------------------------------------------
        if (opcode == `OPCODE_OP_IMM || opcode == `OPCODE_LOAD || opcode == `OPCODE_JALR) begin
            assert (imm_out == {{20{instruction[31]}}, instruction[31:20]});
            assert (imm_out[31:11] == {21{instruction[31]}});
        end

        if (opcode == `OPCODE_STORE) begin
            assert (imm_out == {{20{instruction[31]}}, instruction[31:25], instruction[11:7]});
            assert (imm_out[31:11] == {21{instruction[31]}});
        end

        if (opcode == `OPCODE_BRANCH) begin
            assert (imm_out == {{19{instruction[31]}}, instruction[31], instruction[7],
                                instruction[30:25], instruction[11:8], 1'b0});
            assert (imm_out[0] == 1'b0);
            assert (imm_out[31:12] == {20{instruction[31]}});
        end

        if (opcode == `OPCODE_LUI || opcode == `OPCODE_AUIPC) begin
            assert (imm_out == {instruction[31:12], 12'b0});
            assert (imm_out[11:0] == 12'b0);
        end

        if (opcode == `OPCODE_JAL) begin
            assert (imm_out == {{11{instruction[31]}}, instruction[31], instruction[19:12],
                                instruction[20], instruction[30:21], 1'b0});
            assert (imm_out[0] == 1'b0);
            assert (imm_out[31:20] == {12{instruction[31]}});
        end
    end

    //--------------------------------------------------------------------------
    // 6. Reachability / Witness Cover Properties
    //--------------------------------------------------------------------------
    always @(posedge clk) begin
        cover (opcode == `OPCODE_R_TYPE && funct7 == `FUNCT7_ALT && funct3 == `FUNCT3_ADD_SUB);
        cover (opcode == `OPCODE_OP_IMM && funct3 == `FUNCT3_SRL_SRA && funct7 == `FUNCT7_ALT);
        cover (opcode == `OPCODE_LOAD   && funct3 == `FUNCT3_LW);
        cover (opcode == `OPCODE_STORE  && funct3 == `FUNCT3_SW);
        cover (opcode == `OPCODE_BRANCH && funct3 == `FUNCT3_BLTU);
        cover (opcode == `OPCODE_JAL);
        cover (opcode == `OPCODE_JALR);
        cover (opcode == `OPCODE_LUI);
        cover (opcode == `OPCODE_AUIPC);
        cover (!is_valid_opcode);
    end
`endif

endmodule
