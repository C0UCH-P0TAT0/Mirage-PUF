# ============================================================
# System clock / UART
# ============================================================

set_property -dict { PACKAGE_PIN E3 IOSTANDARD LVCMOS33 } [get_ports clk]
create_clock -add -name sys_clk_pin -period 10.00 \
    -waveform {0 5} [get_ports clk]

set_property -dict { PACKAGE_PIN C4 IOSTANDARD LVCMOS33 } [get_ports rx]
set_property -dict { PACKAGE_PIN D4 IOSTANDARD LVCMOS33 } [get_ports tx]


# ============================================================
# Intentional RO combinational loops
# ============================================================

set_property SEVERITY Warning [get_drc_checks LUTLP-1]


# ============================================================
# RO oscillator clock routing
# ============================================================

# Verify *ro_out* matches the synthesized oscillator output nets
set_property CLOCK_DEDICATED_ROUTE FALSE \
    [get_nets -hierarchical -filter {NAME =~ */w[6]}]


# ============================================================
# Preserve oscillator structure
# ============================================================
set_property ALLOW_COMBINATORIAL_LOOPS TRUE \
    [get_nets -hierarchical -filter {NAME =~ */w[1]}]

set_property DONT_TOUCH TRUE \
    [get_cells -hierarchical -filter {NAME =~ *lut_inv*}]

set_property DONT_TOUCH TRUE \
    [get_cells -hierarchical -filter {NAME =~ *lut_nand}]


# ============================================================
# RO-PUF placement
# Oscillator LUTs ONLY — counters remain unconstrained
# ============================================================

set ro_luts [get_cells -hierarchical -filter {NAME =~ *lut_inv*}]
set ro_nands [get_cells -hierarchical -filter {NAME =~ *lut_nand}]

create_pblock pblock_ro_puf

add_cells_to_pblock [get_pblocks pblock_ro_puf] $ro_luts
add_cells_to_pblock [get_pblocks pblock_ro_puf] $ro_nands

resize_pblock [get_pblocks pblock_ro_puf] \
    -add {SLICE_X65Y40:SLICE_X95Y80}


# ============================================================
# Bitstream
# ============================================================

set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]