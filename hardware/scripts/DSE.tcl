# =========================================================
# VIVADO 10-RUN DEEP DSE SCRIPT (A2-PUF EDITION)
# =========================================================
set dse_dir "INSERT_DESTINATION_HERE"
file mkdir $dse_dir

set directives [list "Explore" "Default" "AggressiveExplore" "AlternateCLBRouting" "NoTimingRelaxation" "MoreGlobalIterations" "HigherDelayCost" "AdvancedSkewModeling" "RuntimeOptimized" "Quick"]
for {set i 0} {$i < 10} {incr i} {
    set dir_name [lindex $directives $i]
    set run_name "impl_A2_Sweep_$i"
    
    puts "========================================================="
    puts "STARTING A2-PUF RUN [expr {$i + 1}] OF 10: $dir_name"
    puts "========================================================="

    if {[llength [get_runs $run_name]] > 0} {
        puts "Overwriting old run: $run_name..."
        delete_run $run_name
    }
    create_run $run_name -parent_run synth_1 -flow {Vivado Implementation 2025}
    set_property STEPS.ROUTE_DESIGN.ARGS.DIRECTIVE $dir_name [get_runs $run_name]
    launch_runs $run_name -jobs 8 -to_step write_bitstream
    
    wait_on_run $run_name
    
    set run_dir [get_property DIRECTORY [get_runs $run_name]]
    set bit_files [glob -nocomplain "$run_dir/*.bit"]
    
    if {[llength $bit_files] > 0} {
        set source_bit [lindex $bit_files 0]
        file copy -force $source_bit "$dse_dir/A2_${run_name}_${dir_name}.bit"
        puts "SUCCESS: Saved bitstream to $dse_dir/A2_${run_name}_${dir_name}.bit"
    } else {
        puts "WARNING: Bitstream generation failed for $run_name. Check Vivado logs."
    }
}
puts "========================================================="
puts "A2-PUF SWEEP COMPLETE. ALL BITSTREAMS SAVED."
puts "========================================================="
