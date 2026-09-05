module cocotb_iverilog_dump();
initial begin
    string dumpfile_path;    if ($value$plusargs("dumpfile_path=%s", dumpfile_path)) begin
        $dumpfile(dumpfile_path);
    end else begin
        $dumpfile("C:\\Projects\\rv32i_core\\sim\\main_decoder\\main_decoder.fst");
    end
    $dumpvars(0, main_decoder);
end
endmodule
