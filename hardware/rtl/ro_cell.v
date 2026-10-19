// ro_cell.v - 7-stage Ring Oscillator
(* DONT_TOUCH = "yes" *)
module ro_cell (
    input  wire en,
    output wire out
);
    (* DONT_TOUCH = "yes" *) wire [6:0] w;

    (* DONT_TOUCH = "yes" *)
    LUT2 #(.INIT(4'h7)) lut_nand (.I0(en), .I1(w[6]), .O(w[0]));

    genvar i;
    generate
        for (i = 1; i < 7; i = i + 1) begin : inv_stages
            (* DONT_TOUCH = "yes" *)
            LUT1 #(.INIT(2'h1)) lut_inv (.I0(w[i-1]), .O(w[i]));
        end
    endgenerate

    assign out = w[6];
endmodule