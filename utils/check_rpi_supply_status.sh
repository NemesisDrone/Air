#!/bin/bash
# Author James A Chambers 6-6-17

# Output current configuration
vcgencmd get_config int | egrep "(arm|core|gpu|sdram)_freq|over_volt"

# Measure clock speeds
for src in arm core h264 isp v3d; do echo "$src:\t$(vcgencmd measure_clock $src)"; done

# Measure Volts
for id in core sdram_c sdram_i sdram_p ; do echo "$id:\t$(vcgencmd measure_volts $id)"; done

# Measure Temperature
vcgencmd measure_temp

# See if we are being throttled
throttled="$(vcgencmd get_throttled)"
echo "$throttled"
if [[ $throttled != "throttled=0x0" ]]; then
    echo "WARNING:  You are being throttled.  This is likely because you are undervoltage.  Please connect your PI to a better power supply!"
fi