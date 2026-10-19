`timescale 1ns / 1ps

module ro_puf (
    input  wire        clk,            // 100MHz System Clock
    input  wire        reset,          // Global Reset
    input  wire        gen_next,       // Pulse high to trigger a new read
    output reg [63:0]  ro_fingerprint = 64'b0,
    output reg         ro_ready       = 1'b0
);
    localparam NUM_ROS = 128;
    localparam MEASURE_BIT = 20;

    localparam S_IDLE      = 3'd0;
    localparam S_PREP      = 3'd1;
    localparam S_MEASURE   = 3'd2;
    localparam S_STOP_WAIT = 3'd3;
    localparam S_SNAPSHOT  = 3'd4;
    localparam S_COMPARE   = 3'd5;
    localparam S_DONE      = 3'd6;

    reg [2:0]  state = S_IDLE;
    reg [20:0] timer = 0;
    reg        ro_en = 0;
    reg        cnt_rst = 0;
    wire [NUM_ROS-1:0] ro_outs;
    reg [23:0] final_counts [NUM_ROS-1:0];

    // --- Edge detection for the trigger ---
    // Initialized to 0 to ensure the first pulse is caught correctly
    reg gen_next_q = 1'b0; 
    always @(posedge clk) gen_next_q <= gen_next;
    wire trigger = gen_next && !gen_next_q;

    genvar k;
    generate
        for (k = 0; k < NUM_ROS; k = k + 1) begin : ro_gen
            ro_cell inst_ro (.en(ro_en), .out(ro_outs[k]));
            
            reg [23:0] async_cnt = 0;
            always @(posedge ro_outs[k] or posedge cnt_rst) begin
                if (cnt_rst) async_cnt <= 0;
                else         async_cnt <= async_cnt + 1;
            end
            
            always @(posedge clk) begin
                if (state == S_SNAPSHOT) final_counts[k] <= async_cnt;
            end
        end
    endgenerate

    integer i;
    always @(posedge clk) begin
        if (reset) begin
            state <= S_IDLE; ro_ready <= 0; ro_en <= 0; cnt_rst <= 1; timer <= 0;
        end else begin
            case (state)
                S_IDLE: begin 
                    ro_ready <= 0;
                    ro_en    <= 0;
                    cnt_rst  <= 0;
                    timer    <= 0;
                    if (trigger) state <= S_PREP;
                end

                S_PREP: begin
                    cnt_rst <= 1;
                    timer   <= timer + 1;
                    if (timer[4]) begin
                        cnt_rst <= 0;
                        timer   <= 0;
                        state   <= S_MEASURE;
                    end
                end

                S_MEASURE: begin 
                    ro_en <= 1; 
                    timer <= timer + 1; 
                    if (timer[MEASURE_BIT]) begin 
                        ro_en <= 0; 
                        timer <= 0; 
                        state <= S_STOP_WAIT; 
                    end 
                end

                S_STOP_WAIT: begin 
                    timer <= timer + 1; 
                    if (timer[4]) state <= S_SNAPSHOT; 
                end

                S_SNAPSHOT: state <= S_COMPARE;

                S_COMPARE: begin 
                    for (i=0; i<64; i=i+1) begin
                        ro_fingerprint[i] <= (final_counts[2*i] > final_counts[2*i+1]);
                    end 
                    state <= S_DONE; 
                end

                S_DONE: begin 
                    ro_ready <= 1; // Pulse high for one cycle
                    state    <= S_IDLE;
                end
                
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule