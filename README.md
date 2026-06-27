# Mirage PUF

Mirage PUF is an FPGA-based Physical Unclonable Function (PUF) architecture designed to improve resistance against machine learning modeling attacks through dynamic challenge mutation.

The design is implemented on the Xilinx Artix-7 (Nexys A7-100T) platform using dedicated CARRY4 primitives. A secondary carry-chain generates an internal avalanche mask that mutates the primary challenge during evaluation, introducing structural non-linearity while maintaining a compact hardware footprint.

## Repository Structure

```
hardware/
    rtl/            Verilog source
    constraints/    XDC constraints
    scripts/        Vivado TCL scripts

software/
    acquisition/    UART data collection
    preprocessing/  Dataset preparation
    analysis/       Metric evaluation and ML attacks

data/
    raw/            Raw CRP datasets
    processed/      Processed datasets
    calibration/    Calibration logs

artifacts/
    bitstreams/     Generated FPGA bitstreams

docs/
    Manuscript and supplementary material

build/
    Local Vivado project (ignored by Git)
```

## Experimental Pipeline

1. Calibrate the PDL settings.
2. Acquire raw challenge-response pairs.
3. Filter unstable CRPs.
4. Compute reliability, randomness, uniqueness, and stability metrics.
5. Evaluate resistance against machine learning attacks.

## Hardware

- FPGA: Digilent Nexys A7-100T
- Device: Xilinx Artix-7 XC7A100T
- UART: 115200 baud

## Paper

The submitted manuscript is available in `docs/`.

## License

Released under the MIT License.