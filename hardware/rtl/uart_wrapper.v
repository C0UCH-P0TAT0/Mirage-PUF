`timescale 1ns / 1ps

module uart_wrapper (
    input wire clk,           // 100MHz Physical Pin E3
    input wire rx,            // UART RX Pin C4
    output reg tx = 1         // UART TX Pin D4
);

    // ~~~~~~~~~~~~~~~ INTERNAL MODE SELECTION ~~~~~~~~~~~~~~~
    localparam [1:0] latched_mode = 2'b10; // 00:Hybrid, 01:Mirage, 10:RO

    // ~~~~~~~~~~~~~~~ CLOCK BUFFERING ~~~~~~~~~~~~~~~
    wire sys_clk;
    BUFG bufg_inst (.I(clk), .O(sys_clk));

    // ~~~~~~~~~~~~~~~ FSM STATES ~~~~~~~~~~~~~~~
    localparam STATE_IDLE      = 3'd0;
    localparam STATE_RX        = 3'd1;
    localparam STATE_PUF_WAIT  = 3'd2; 
    localparam STATE_PUF_RUN   = 3'd3; 
    localparam STATE_WAIT_RO   = 3'd4; 
    localparam STATE_PREPARE   = 3'd5; 
    localparam STATE_TX        = 3'd6;
    
    reg [2:0] state = STATE_IDLE;
    reg [9:0] baud_counter = 0;
    reg baud_tick = 0;
    
    always @(posedge sys_clk) begin
        if (state == STATE_IDLE && rx == 1) begin
            baud_counter <= 434;
            baud_tick <= 0;
        end else if (baud_counter >= 867) begin
            baud_counter <= 0;
            baud_tick <= 1;
        end else begin
            baud_counter <= baud_counter + 1;
            baud_tick <= 0;
        end
    end

    // ~~~~~~~~~~~~~~~ PUF INSTANTIATION ~~~~~~~~~~~~~~~
    reg [127:0] active_challenge;
    reg [63:0]  full_response;
    reg [63:0]  final_buffer;
    reg [7:0]   byte_buffer;
    
    wire puf_result;
    wire [63:0] ro_fingerprint;
    wire        ro_ready;
    reg         ro_gen_next = 0;

    // --- Sticky Latch Logic ---
    // Updated every 10ns to catch the RO completion pulse.
    // Cleared during IDLE and RX to prepare for the next transaction.
    reg ro_done_latch = 0;
    always @(posedge sys_clk) begin
        if (state == STATE_IDLE || state == STATE_RX)
            ro_done_latch <= 0;
        else if (ro_ready)
            ro_done_latch <= 1;
    end

    ro_puf ro_puf_inst (
        .clk(sys_clk),
        .reset(1'b0), 
        .gen_next(ro_gen_next),
        .ro_fingerprint(ro_fingerprint),
        .ro_ready(ro_ready)
    );

    reg puf_trigger = 0;
    always @(posedge sys_clk)
        puf_trigger <= (state == STATE_PUF_RUN) && (baud_counter > 50);

    mirage_core my_ipuf (
        .trigger(puf_trigger),
        .challenge_x(active_challenge[127:64]),
        .challenge_y(active_challenge[63:0]),
        .final_response(puf_result)
    );

    reg [3:0] bit_count = 0;   
    reg [4:0] byte_count = 0;  
    reg [7:0] run_count = 0;   
    
    // ~~~~~~~~~~~~~~~ FSM LOGIC ~~~~~~~~~~~~~~~
    always @(posedge sys_clk) begin
        if (baud_tick) begin
            case (state)                                                
                STATE_IDLE: begin
                    tx <= 1;
                    ro_gen_next <= 0;
                    if (rx == 0) begin
                        state <= STATE_RX;
                        bit_count <= 0;
                        byte_count <= 0;
                    end
                end

                STATE_RX: begin
                    if (bit_count < 8) begin
                        byte_buffer <= {rx, byte_buffer[7:1]};
                        bit_count <= bit_count + 1;
                    end else begin
                        active_challenge <= {active_challenge[119:0], byte_buffer};
                        if (byte_count == 15) begin
                            state <= STATE_PUF_WAIT;
                            ro_gen_next <= 1; // Pulse RO-PUF
                        end else begin                                 
                            byte_count <= byte_count + 1;
                            state <= STATE_IDLE;
                        end
                    end
                end

                STATE_PUF_WAIT: begin
                    ro_gen_next <= 0; 
                    full_response <= 64'b0;
                    run_count <= 0;
                    
                    if (latched_mode == 2'b10) begin 
                        if (ro_done_latch) state <= STATE_PREPARE;
                    end else begin 
                        state <= STATE_PUF_RUN;
                    end
                end

                STATE_PUF_RUN: begin
                    full_response <= {full_response[62:0], puf_result};
                    active_challenge[119:64] <= {active_challenge[118:64], active_challenge[119] ^ active_challenge[64]};
                    active_challenge[55:0]   <= {active_challenge[54:0], active_challenge[55] ^ active_challenge[0]};

                    if (run_count == 63) begin
                        if (latched_mode == 2'b00) state <= STATE_WAIT_RO;
                        else                      state <= STATE_PREPARE;
                    end else begin
                        run_count <= run_count + 1;
                    end
                end

                STATE_WAIT_RO: begin
                    if (ro_done_latch) state <= STATE_PREPARE;
                end

                STATE_PREPARE: begin
                    case (latched_mode)
                        2'b00: final_buffer <= full_response ^ ro_fingerprint;
                        2'b01: final_buffer <= full_response;
                        2'b10: final_buffer <= ro_fingerprint;
                        default: final_buffer <= 64'b0;
                    endcase
                    state <= STATE_TX;
                    byte_count <= 0;
                    bit_count <= 0;
                end

                STATE_TX: begin                                                 
                    if (bit_count == 0) tx <= 0;
                    else if (bit_count <= 8) begin
                        tx <= final_buffer[0]; 
                        final_buffer <= {1'b0, final_buffer[63:1]};
                    end else if (bit_count == 9) tx <= 1;
                    else begin
                        bit_count <= 0;
                        if (byte_count == 7) begin
                            state <= STATE_IDLE;
                            byte_count <= 0;
                        end else begin
                            byte_count <= byte_count + 1;
                        end
                    end
                    if (bit_count < 10) bit_count <= bit_count + 1;
                end
                default: state <= STATE_IDLE;
            endcase
        end
    end
endmoduleu