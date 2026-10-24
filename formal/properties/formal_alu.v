`include "../include/rv32i_defs.vh"
`timescale 1ns/1ps

//==============================================================================
// Formal Verification Harness: 32-bit Arithmetic Logic Unit (ALU) (Verilog-2005)
// Mathematically proves bit-vector arithmetic/logic operations, signed/unsigned
// comparisons, shift invariants, and flag equivalences across all 2^68 inputs.
//==============================================================================
module formal_alu (
    input wire        clk,
    input wire [31:0] a,
    input wire [31:0] b,
    input wire [3:0]  alu_op
);

    wire [31:0] alu_result;
    wire        zero;
    wire        carry_out;
    wire        overflow;

    // Instantiate DUT: ALU
    alu u_alu (
        .a          (a),
        .b          (b),
        .alu_op     (alu_op),
        .alu_result (alu_result),
        .zero       (zero),
        .carry_out  (carry_out),
        .overflow   (overflow)
    );

    wire [32:0] add_ext = {1'b0, a} + {1'b0, b};
    wire [32:0] sub_ext = {1'b0, a} - {1'b0, b};
    wire signed [31:0] sra_expected = $signed(a) >>> b[4:0];

    wire is_known_op = (alu_op == `ALU_ADD)  || (alu_op == `ALU_SUB) ||
                       (alu_op == `ALU_AND)  || (alu_op == `ALU_OR)  ||
                       (alu_op == `ALU_XOR)  || (alu_op == `ALU_SLL) ||
                       (alu_op == `ALU_SRL)  || (alu_op == `ALU_SRA) ||
                       (alu_op == `ALU_SLT)  || (alu_op == `ALU_SLTU);

`ifdef FORMAL
    always @(*) begin
        //----------------------------------------------------------------------
        // 1. Universal Zero Flag Bi-Implication
        //----------------------------------------------------------------------
        assert (zero == (alu_result == 32'b0));

`ifdef FORMAL_BUG_INJECT
        // Intentional false assertion for fault injection demonstration
        assert (!(alu_op == `ALU_ADD && overflow));
`endif

        //----------------------------------------------------------------------
        // 2. Exhaustive Operation Proofs
        //----------------------------------------------------------------------
        if (alu_op == `ALU_ADD) begin
            assert (alu_result == (a + b));
            assert (carry_out == add_ext[32]);
            // Classic two's complement signed overflow theorem:
            // Overflow occurs iff operands share the same sign and result has opposite sign
            assert (overflow == ((a[31] == b[31]) && (alu_result[31] != a[31])));
            if (b == 32'b0) assert (alu_result == a);
        end

        if (alu_op == `ALU_SUB) begin
            assert (alu_result == (a - b));
            assert (carry_out == sub_ext[32]);
            // Signed subtraction overflow occurs iff operands have different signs and result sign != a[31]
            assert (overflow == ((a[31] != b[31]) && (alu_result[31] != a[31])));
            if (a == b)     assert (alu_result == 32'b0 && zero == 1'b1);
        end

        if (alu_op == `ALU_AND) begin
            assert (alu_result == (a & b));
            assert (!carry_out && !overflow);
            if (b == 32'b0)         assert (alu_result == 32'b0 && zero);
            if (b == 32'hFFFF_FFFF) assert (alu_result == a);
        end

        if (alu_op == `ALU_OR) begin
            assert (alu_result == (a | b));
            assert (!carry_out && !overflow);
            if (b == 32'b0)         assert (alu_result == a);
            if (b == 32'hFFFF_FFFF) assert (alu_result == 32'hFFFF_FFFF && !zero);
        end

        if (alu_op == `ALU_XOR) begin
            assert (alu_result == (a ^ b));
            assert (!carry_out && !overflow);
            if (a == b)     assert (alu_result == 32'b0 && zero);
            if (b == 32'b0) assert (alu_result == a);
        end

        if (alu_op == `ALU_SLL) begin
            assert (alu_result == (a << b[4:0]));
            assert (!carry_out && !overflow);
            if (b[4:0] == 5'd0) assert (alu_result == a);
        end

        if (alu_op == `ALU_SRL) begin
            assert (alu_result == (a >> b[4:0]));
            assert (!carry_out && !overflow);
            if (b[4:0] == 5'd0) assert (alu_result == a);
            if (b[4:0] != 5'd0) assert (alu_result[31] == 1'b0);
        end

        if (alu_op == `ALU_SRA) begin
            assert (alu_result == sra_expected);
            assert (!carry_out && !overflow);
            assert (alu_result[31] == a[31]);
            if (b[4:0] == 5'd0)     assert (alu_result == a);
            if (a == 32'hFFFF_FFFF) assert (alu_result == 32'hFFFF_FFFF);
        end

        if (alu_op == `ALU_SLT) begin
            assert (alu_result == (($signed(a) < $signed(b)) ? 32'd1 : 32'd0));
            assert (alu_result[31:1] == 31'b0);
            assert ((a != b) || (alu_result == 32'd0));
        end

        if (alu_op == `ALU_SLTU) begin
            assert (alu_result == ((a < b) ? 32'd1 : 32'd0));
            assert (alu_result[31:1] == 31'b0);
            assert ((a != b) || (alu_result == 32'd0));
        end

        if (!is_known_op) begin
            assert (alu_result == 32'b0 && zero && !carry_out && !overflow);
        end
    end

    //--------------------------------------------------------------------------
    // 3. Reachability / Witness Cover Properties
    //--------------------------------------------------------------------------
    always @(posedge clk) begin
        cover (alu_op == `ALU_ADD && !a[31] && !b[31] && alu_result[31] && overflow);
        cover (alu_op == `ALU_SUB && a == 32'h8000_0000 && b == 32'd1 && overflow);
        cover (alu_op == `ALU_SRA && a == 32'h8000_0000 && b[4:0] == 5'd31 && alu_result == 32'hFFFF_FFFF);
        cover (alu_op == `ALU_SLT && a == 32'h8000_0000 && b == 32'd0 && alu_result == 32'd1);
        cover (alu_op == `ALU_SLTU && a == 32'd0 && b == 32'hFFFF_FFFF && alu_result == 32'd1);
    end
`endif

endmodule
