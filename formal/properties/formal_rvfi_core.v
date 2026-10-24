`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

//==============================================================================
// Formal Verification Harness: Full RV32I Core + RVFI ISA Contract (Verilog-2005)
// Mathematically proves multi-cycle sequential execution, PC transitions,
// x0 hardwired-zero invariance, Register File Read-After-Write (RAW) & Frame
// non-interference, and end-to-end RVFI ISA correctness for all 37 RV32I
// base instructions.
//==============================================================================
module formal_rvfi_core (
    input wire        clk,
    input wire        rst,
    input wire [31:0] instr_data,
    input wire [31:0] data_rdata
);

    wire [31:0] instr_addr;
    wire [31:0] data_addr;
    wire [31:0] data_wdata;
    wire [3:0]  data_we;
    wire        data_re;

    wire [31:0] comb_next_pc;
    wire        comb_reg_write;
    wire [31:0] comb_write_data;
    wire [31:0] comb_rs1_rdata;
    wire [31:0] comb_rs2_rdata;

    wire        rvfi_valid;
    wire [63:0] rvfi_order;
    wire [31:0] rvfi_insn;
    wire        rvfi_trap;
    wire        rvfi_halt;
    wire        rvfi_intr;
    wire [1:0]  rvfi_mode;
    wire [1:0]  rvfi_ixl;
    wire [4:0]  rvfi_rs1_addr;
    wire [4:0]  rvfi_rs2_addr;
    wire [31:0] rvfi_rs1_rdata;
    wire [31:0] rvfi_rs2_rdata;
    wire [4:0]  rvfi_rd_addr;
    wire [31:0] rvfi_rd_wdata;
    wire [31:0] rvfi_pc_rdata;
    wire [31:0] rvfi_pc_wdata;
    wire [31:0] rvfi_mem_addr;
    wire [3:0]  rvfi_mem_rmask;
    wire [3:0]  rvfi_mem_wmask;
    wire [31:0] rvfi_mem_rdata;
    wire [31:0] rvfi_mem_wdata;

    // Instantiate DUT: RVFI-Wrapped RV32I Core
    rv32i_rvfi_wrapper u_dut (
        .clk             (clk),
        .rst             (rst),
        .instr_addr      (instr_addr),
        .instr_data      (instr_data),
        .data_addr       (data_addr),
        .data_wdata      (data_wdata),
        .data_we         (data_we),
        .data_re         (data_re),
        .data_rdata      (data_rdata),
        .comb_next_pc    (comb_next_pc),
        .comb_reg_write  (comb_reg_write),
        .comb_write_data (comb_write_data),
        .comb_rs1_rdata  (comb_rs1_rdata),
        .comb_rs2_rdata  (comb_rs2_rdata),
        .rvfi_valid      (rvfi_valid),
        .rvfi_order      (rvfi_order),
        .rvfi_insn       (rvfi_insn),
        .rvfi_trap       (rvfi_trap),
        .rvfi_halt       (rvfi_halt),
        .rvfi_intr       (rvfi_intr),
        .rvfi_mode       (rvfi_mode),
        .rvfi_ixl        (rvfi_ixl),
        .rvfi_rs1_addr   (rvfi_rs1_addr),
        .rvfi_rs2_addr   (rvfi_rs2_addr),
        .rvfi_rs1_rdata  (rvfi_rs1_rdata),
        .rvfi_rs2_rdata  (rvfi_rs2_rdata),
        .rvfi_rd_addr    (rvfi_rd_addr),
        .rvfi_rd_wdata   (rvfi_rd_wdata),
        .rvfi_pc_rdata   (rvfi_pc_rdata),
        .rvfi_pc_wdata   (rvfi_pc_wdata),
        .rvfi_mem_addr   (rvfi_mem_addr),
        .rvfi_mem_rmask  (rvfi_mem_rmask),
        .rvfi_mem_wmask  (rvfi_mem_wmask),
        .rvfi_mem_rdata  (rvfi_mem_rdata),
        .rvfi_mem_wdata  (rvfi_mem_wdata)
    );

    //--------------------------------------------------------------------------
    // Decoded fields of the retired instruction (from rvfi_insn)
    //--------------------------------------------------------------------------
    wire [6:0] ret_opcode = rvfi_insn[6:0];
    wire [4:0] ret_rd     = rvfi_insn[11:7];
    wire [2:0] ret_funct3 = rvfi_insn[14:12];
    wire [4:0] ret_rs1    = rvfi_insn[19:15];
    wire [4:0] ret_rs2    = rvfi_insn[24:20];
    wire [6:0] ret_funct7 = rvfi_insn[31:25];

    wire [31:0] ret_imm_i = {{20{rvfi_insn[31]}}, rvfi_insn[31:20]};
    wire [31:0] ret_imm_s = {{20{rvfi_insn[31]}}, rvfi_insn[31:25], rvfi_insn[11:7]};
    wire [31:0] ret_imm_b = {{19{rvfi_insn[31]}}, rvfi_insn[31], rvfi_insn[7], rvfi_insn[30:25], rvfi_insn[11:8], 1'b0};
    wire [31:0] ret_imm_u = {rvfi_insn[31:12], 12'b0};
    wire [31:0] ret_imm_j = {{11{rvfi_insn[31]}}, rvfi_insn[31], rvfi_insn[19:12], rvfi_insn[20], rvfi_insn[30:21], 1'b0};

    // Signed arithmetic right shift helper wires (self-determined signed context)
    wire signed [31:0] ret_sra_r = $signed(rvfi_rs1_rdata) >>> rvfi_rs2_rdata[4:0];
    wire signed [31:0] ret_sra_i = $signed(rvfi_rs1_rdata) >>> ret_imm_i[4:0];

    // Load byte/halfword extraction helpers for retired instruction
    wire [7:0] ret_load_byte = (rvfi_mem_addr[1:0] == 2'b00) ? rvfi_mem_rdata[7:0]   :
                               (rvfi_mem_addr[1:0] == 2'b01) ? rvfi_mem_rdata[15:8]  :
                               (rvfi_mem_addr[1:0] == 2'b10) ? rvfi_mem_rdata[23:16] :
                                                               rvfi_mem_rdata[31:24];

    wire [15:0] ret_load_half = (rvfi_mem_addr[1] == 1'b0) ? rvfi_mem_rdata[15:0] :
                                                             rvfi_mem_rdata[31:16];

    // Live instruction source register indices
    wire [4:0] live_rs1 = instr_data[19:15];
    wire [4:0] live_rs2 = instr_data[24:20];

`ifdef FORMAL
    reg f_past_valid;
    initial f_past_valid = 1'b0;
    always @(posedge clk) f_past_valid <= 1'b1;

    // Require synchronous reset at step 0, then deasserted for active run
    always @(*) begin
        if (!f_past_valid) begin
            assume (rst == 1'b1);
        end else begin
            assume (rst == 1'b0);
        end
    end

    //==========================================================================
    // PART A: Combinational Core & x0 Hardwired-Zero Invariants
    //==========================================================================
    always @(*) begin
        // 1. x0 read ports are hardwired to 0 on every cycle
        if (live_rs1 == 5'd0) assert (comb_rs1_rdata == 32'd0);
        if (live_rs2 == 5'd0) assert (comb_rs2_rdata == 32'd0);

        // 2. Data memory read and write never occur simultaneously
        assert (!(data_re && (|data_we)));

`ifdef FORMAL_BUG_INJECT
        // Intentional false assertion for fault injection demonstration
        assert (!(rvfi_valid && ret_opcode == `OPCODE_JAL));
`endif
    end

    //==========================================================================
    // PART B: Sequential State & RVFI Architectural Proofs
    //==========================================================================
    always @(posedge clk) begin
        if (f_past_valid) begin
            //------------------------------------------------------------------
            // 1. Reset State Proof
            //------------------------------------------------------------------
            if ($past(rst)) begin
                assert (instr_addr == 32'h0000_0000);
                assert (rvfi_valid == 1'b0);
                assert (rvfi_order == 64'd0);
            end

            //------------------------------------------------------------------
            // 2. Active Retirement Proofs (when previous cycle was not in reset)
            //------------------------------------------------------------------
            if (!$past(rst)) begin
                assert (rvfi_valid == 1'b1);
                assert (rvfi_order == $past(rvfi_order) + 64'd1);

                // Program Counter sequential continuity: current PC == retired next_pc
                assert (instr_addr == rvfi_pc_wdata);
                assert (rvfi_pc_rdata == $past(instr_addr));

                // RVFI x0 invariants
                if (rvfi_rs1_addr == 5'd0) assert (rvfi_rs1_rdata == 32'd0);
                if (rvfi_rs2_addr == 5'd0) assert (rvfi_rs2_rdata == 32'd0);
                if (rvfi_rd_addr  == 5'd0) assert (rvfi_rd_wdata  == 32'd0);

                //--------------------------------------------------------------
                // 3. Register File Read-After-Write (RAW) & Frame Stability
                //--------------------------------------------------------------
                // If previous instruction wrote to register R != x0, reading R now yields rvfi_rd_wdata
                if (rvfi_rd_addr != 5'd0 && live_rs1 == rvfi_rd_addr) begin
                    assert (comb_rs1_rdata == rvfi_rd_wdata);
                end
                if (rvfi_rd_addr != 5'd0 && live_rs2 == rvfi_rd_addr) begin
                    assert (comb_rs2_rdata == rvfi_rd_wdata);
                end

                // If previous instruction did NOT write to live_rs1, and live_rs1 was also read last cycle,
                // its value in the register file is strictly preserved (No Register Clobbering!)
                if (live_rs1 == $past(live_rs1) && rvfi_rd_addr != live_rs1) begin
                    assert (comb_rs1_rdata == $past(comb_rs1_rdata));
                end
                if (live_rs2 == $past(live_rs2) && rvfi_rd_addr != live_rs2) begin
                    assert (comb_rs2_rdata == $past(comb_rs2_rdata));
                end

                //--------------------------------------------------------------
                // 4. End-to-End RVFI Contract for All 37 RV32I Instructions
                //--------------------------------------------------------------

                // --- 4.1 Upper Immediate Instructions (LUI, AUIPC) ---
                if (ret_opcode == `OPCODE_LUI) begin
                    assert (rvfi_rd_addr   == ret_rd);
                    assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : ret_imm_u));
                    assert (rvfi_pc_wdata  == (rvfi_pc_rdata + 32'd4));
                    assert (rvfi_mem_rmask == 4'b0000 && rvfi_mem_wmask == 4'b0000);
                end

                if (ret_opcode == `OPCODE_AUIPC) begin
                    assert (rvfi_rd_addr   == ret_rd);
                    assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_pc_rdata + ret_imm_u)));
                    assert (rvfi_pc_wdata  == (rvfi_pc_rdata + 32'd4));
                    assert (rvfi_mem_rmask == 4'b0000 && rvfi_mem_wmask == 4'b0000);
                end

                // --- 4.2 Jump Instructions (JAL, JALR) ---
                if (ret_opcode == `OPCODE_JAL) begin
                    assert (rvfi_rd_addr   == ret_rd);
                    assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_pc_rdata + 32'd4)));
                    assert (rvfi_pc_wdata  == (rvfi_pc_rdata + ret_imm_j));
                    assert (rvfi_mem_rmask == 4'b0000 && rvfi_mem_wmask == 4'b0000);
                end

                if (ret_opcode == `OPCODE_JALR) begin
                    assert (rvfi_rs1_addr  == ret_rs1);
                    assert (rvfi_rd_addr   == ret_rd);
                    assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_pc_rdata + 32'd4)));
                    assert (rvfi_pc_wdata  == ((rvfi_rs1_rdata + ret_imm_i) & 32'hFFFF_FFFE));
                    assert (rvfi_pc_wdata[0] == 1'b0);
                    assert (rvfi_mem_rmask == 4'b0000 && rvfi_mem_wmask == 4'b0000);
                end

                // --- 4.3 Conditional Branch Instructions (BEQ, BNE, BLT, BGE, BLTU, BGEU) ---
                if (ret_opcode == `OPCODE_BRANCH) begin
                    assert (rvfi_rs1_addr  == ret_rs1);
                    assert (rvfi_rs2_addr  == ret_rs2);
                    assert (rvfi_rd_addr   == 5'd0 && rvfi_rd_wdata == 32'd0);
                    assert (rvfi_mem_rmask == 4'b0000 && rvfi_mem_wmask == 4'b0000);

                    if (ret_funct3 == `FUNCT3_BEQ) begin
                        assert (rvfi_pc_wdata == ((rvfi_rs1_rdata == rvfi_rs2_rdata) ?
                                (rvfi_pc_rdata + ret_imm_b) : (rvfi_pc_rdata + 32'd4)));
                    end
                    if (ret_funct3 == `FUNCT3_BNE) begin
                        assert (rvfi_pc_wdata == ((rvfi_rs1_rdata != rvfi_rs2_rdata) ?
                                (rvfi_pc_rdata + ret_imm_b) : (rvfi_pc_rdata + 32'd4)));
                    end
                    if (ret_funct3 == `FUNCT3_BLT) begin
                        assert (rvfi_pc_wdata == (($signed(rvfi_rs1_rdata) < $signed(rvfi_rs2_rdata)) ?
                                (rvfi_pc_rdata + ret_imm_b) : (rvfi_pc_rdata + 32'd4)));
                    end
                    if (ret_funct3 == `FUNCT3_BGE) begin
                        assert (rvfi_pc_wdata == (($signed(rvfi_rs1_rdata) >= $signed(rvfi_rs2_rdata)) ?
                                (rvfi_pc_rdata + ret_imm_b) : (rvfi_pc_rdata + 32'd4)));
                    end
                    if (ret_funct3 == `FUNCT3_BLTU) begin
                        assert (rvfi_pc_wdata == ((rvfi_rs1_rdata < rvfi_rs2_rdata) ?
                                (rvfi_pc_rdata + ret_imm_b) : (rvfi_pc_rdata + 32'd4)));
                    end
                    if (ret_funct3 == `FUNCT3_BGEU) begin
                        assert (rvfi_pc_wdata == ((rvfi_rs1_rdata >= rvfi_rs2_rdata) ?
                                (rvfi_pc_rdata + ret_imm_b) : (rvfi_pc_rdata + 32'd4)));
                    end
                end

                // --- 4.4 Load Instructions (LB, LH, LW, LBU, LHU) ---
                if (ret_opcode == `OPCODE_LOAD) begin
                    assert (rvfi_rs1_addr  == ret_rs1);
                    assert (rvfi_rd_addr   == ret_rd);
                    assert (rvfi_pc_wdata  == (rvfi_pc_rdata + 32'd4));
                    assert (rvfi_mem_wmask == 4'b0000);

                    if (ret_funct3 == `FUNCT3_LB) begin
                        assert (rvfi_mem_addr  == (rvfi_rs1_rdata + ret_imm_i));
                        assert (rvfi_mem_rmask == (4'b0001 << rvfi_mem_addr[1:0]));
                        assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : {{24{ret_load_byte[7]}}, ret_load_byte}));
                    end
                    if (ret_funct3 == `FUNCT3_LBU) begin
                        assert (rvfi_mem_addr  == (rvfi_rs1_rdata + ret_imm_i));
                        assert (rvfi_mem_rmask == (4'b0001 << rvfi_mem_addr[1:0]));
                        assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : {24'b0, ret_load_byte}));
                    end
                    if (ret_funct3 == `FUNCT3_LH) begin
                        assert (rvfi_mem_addr  == (rvfi_rs1_rdata + ret_imm_i));
                        assert (rvfi_mem_rmask == (rvfi_mem_addr[1] ? 4'b1100 : 4'b0011));
                        assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : {{16{ret_load_half[15]}}, ret_load_half}));
                    end
                    if (ret_funct3 == `FUNCT3_LHU) begin
                        assert (rvfi_mem_addr  == (rvfi_rs1_rdata + ret_imm_i));
                        assert (rvfi_mem_rmask == (rvfi_mem_addr[1] ? 4'b1100 : 4'b0011));
                        assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : {16'b0, ret_load_half}));
                    end
                    if (ret_funct3 == `FUNCT3_LW) begin
                        assert (rvfi_mem_addr  == (rvfi_rs1_rdata + ret_imm_i));
                        assert (rvfi_mem_rmask == 4'b1111);
                        assert (rvfi_rd_wdata  == ((ret_rd == 5'd0) ? 32'd0 : rvfi_mem_rdata));
                    end
                end

                // --- 4.5 Store Instructions (SB, SH, SW) ---
                if (ret_opcode == `OPCODE_STORE) begin
                    assert (rvfi_rs1_addr  == ret_rs1);
                    assert (rvfi_rs2_addr  == ret_rs2);
                    assert (rvfi_rd_addr   == 5'd0 && rvfi_rd_wdata == 32'd0);
                    assert (rvfi_pc_wdata  == (rvfi_pc_rdata + 32'd4));
                    assert (rvfi_mem_rmask == 4'b0000);

                    if (ret_funct3 == `FUNCT3_SB) begin
                        assert (rvfi_mem_addr  == (rvfi_rs1_rdata + ret_imm_s));
                        assert (rvfi_mem_wmask == (4'b0001 << rvfi_mem_addr[1:0]));
                        assert (rvfi_mem_wdata == {4{rvfi_rs2_rdata[7:0]}});
                    end
                    if (ret_funct3 == `FUNCT3_SH) begin
                        assert (rvfi_mem_addr  == (rvfi_rs1_rdata + ret_imm_s));
                        assert (rvfi_mem_wmask == (rvfi_mem_addr[1] ? 4'b1100 : 4'b0011));
                        assert (rvfi_mem_wdata == {2{rvfi_rs2_rdata[15:0]}});
                    end
                    if (ret_funct3 == `FUNCT3_SW) begin
                        assert (rvfi_mem_addr  == (rvfi_rs1_rdata + ret_imm_s));
                        assert (rvfi_mem_wmask == 4'b1111);
                        assert (rvfi_mem_wdata == rvfi_rs2_rdata);
                    end
                end

                // --- 4.6 I-Type Register-Immediate ALU Instructions (9) ---
                if (ret_opcode == `OPCODE_OP_IMM) begin
                    assert (rvfi_rs1_addr  == ret_rs1);
                    assert (rvfi_rd_addr   == ret_rd);
                    assert (rvfi_pc_wdata  == (rvfi_pc_rdata + 32'd4));
                    assert (rvfi_mem_rmask == 4'b0000 && rvfi_mem_wmask == 4'b0000);

                    if (ret_funct3 == `FUNCT3_ADD_SUB) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata + ret_imm_i)));
                    end
                    if (ret_funct3 == `FUNCT3_SLT) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 :
                                (($signed(rvfi_rs1_rdata) < $signed(ret_imm_i)) ? 32'd1 : 32'd0)));
                    end
                    if (ret_funct3 == `FUNCT3_SLTU) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 :
                                ((rvfi_rs1_rdata < ret_imm_i) ? 32'd1 : 32'd0)));
                    end
                    if (ret_funct3 == `FUNCT3_XOR) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata ^ ret_imm_i)));
                    end
                    if (ret_funct3 == `FUNCT3_OR) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata | ret_imm_i)));
                    end
                    if (ret_funct3 == `FUNCT3_AND) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata & ret_imm_i)));
                    end
                    if (ret_funct3 == `FUNCT3_SLL) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata << ret_imm_i[4:0])));
                    end
                    if (ret_funct3 == `FUNCT3_SRL_SRA && ret_funct7 == `FUNCT7_BASE) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata >> ret_imm_i[4:0])));
                    end
                    if (ret_funct3 == `FUNCT3_SRL_SRA && ret_funct7 == `FUNCT7_ALT) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : ret_sra_i));
                    end
                end

                // --- 4.7 R-Type Register-Register ALU Instructions (10) ---
                if (ret_opcode == `OPCODE_R_TYPE) begin
                    assert (rvfi_rs1_addr  == ret_rs1);
                    assert (rvfi_rs2_addr  == ret_rs2);
                    assert (rvfi_rd_addr   == ret_rd);
                    assert (rvfi_pc_wdata  == (rvfi_pc_rdata + 32'd4));
                    assert (rvfi_mem_rmask == 4'b0000 && rvfi_mem_wmask == 4'b0000);

                    if (ret_funct7 == `FUNCT7_BASE && ret_funct3 == `FUNCT3_ADD_SUB) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata + rvfi_rs2_rdata)));
                    end
                    if (ret_funct7 == `FUNCT7_ALT && ret_funct3 == `FUNCT3_ADD_SUB) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata - rvfi_rs2_rdata)));
                    end
                    if (ret_funct7 == `FUNCT7_BASE && ret_funct3 == `FUNCT3_SLL) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata << rvfi_rs2_rdata[4:0])));
                    end
                    if (ret_funct7 == `FUNCT7_BASE && ret_funct3 == `FUNCT3_SLT) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 :
                                (($signed(rvfi_rs1_rdata) < $signed(rvfi_rs2_rdata)) ? 32'd1 : 32'd0)));
                    end
                    if (ret_funct7 == `FUNCT7_BASE && ret_funct3 == `FUNCT3_SLTU) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 :
                                ((rvfi_rs1_rdata < rvfi_rs2_rdata) ? 32'd1 : 32'd0)));
                    end
                    if (ret_funct7 == `FUNCT7_BASE && ret_funct3 == `FUNCT3_XOR) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata ^ rvfi_rs2_rdata)));
                    end
                    if (ret_funct7 == `FUNCT7_BASE && ret_funct3 == `FUNCT3_SRL_SRA) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata >> rvfi_rs2_rdata[4:0])));
                    end
                    if (ret_funct7 == `FUNCT7_ALT && ret_funct3 == `FUNCT3_SRL_SRA) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : ret_sra_r));
                    end
                    if (ret_funct7 == `FUNCT7_BASE && ret_funct3 == `FUNCT3_OR) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata | rvfi_rs2_rdata)));
                    end
                    if (ret_funct7 == `FUNCT7_BASE && ret_funct3 == `FUNCT3_AND) begin
                        assert (rvfi_rd_wdata == ((ret_rd == 5'd0) ? 32'd0 : (rvfi_rs1_rdata & rvfi_rs2_rdata)));
                    end
                end
            end

            //------------------------------------------------------------------
            // 5. Multi-Cycle Reachability / Witness Cover Properties
            //------------------------------------------------------------------
            // Cover back-to-back write then read (RAW dependency) with non-zero result
            cover (rvfi_valid && rvfi_rd_addr == 5'd5 && rvfi_rd_wdata == 32'hCAFE_BABE &&
                   live_rs1 == 5'd5 && comb_rs1_rdata == 32'hCAFE_BABE);

            // Cover taken backward branch
            cover (rvfi_valid && ret_opcode == `OPCODE_BRANCH && ret_funct3 == `FUNCT3_BLT &&
                   ret_imm_b[31] == 1'b1 && rvfi_pc_wdata == (rvfi_pc_rdata + ret_imm_b));

            // Cover JALR indirect jump with odd target address cleared to even
            cover (rvfi_valid && ret_opcode == `OPCODE_JALR &&
                   ((rvfi_rs1_rdata + ret_imm_i) & 32'd1) == 32'd1 && rvfi_pc_wdata[0] == 1'b0);

            // Cover byte store followed by signed byte load
            cover (rvfi_valid && ret_opcode == `OPCODE_STORE && ret_funct3 == `FUNCT3_SB &&
                   rvfi_mem_wmask == 4'b1000 && data_re);

            // Cover retiring 3 consecutive instructions after reset
            cover (rvfi_valid && rvfi_order == 64'd3);
        end
    end
`endif

endmodule
