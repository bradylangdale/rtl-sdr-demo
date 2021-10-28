#!/bin/bash
echo "Compile C files"
(cd _receiver && make)

echo "[ INFO ] Set file executation rights"
chmod a+x _receiver/rtl_daq
chmod a+x _receiver/sync
chmod a+x _receiver/gate

sudo chmod +x run.sh

BUFF_SIZE=256 #Must be a power of 2. Normal values are 128, 256. 512 is possible on a fast PC.

# set to /dev/null for no logging, set to some file for logfile. You can also set it to the same file. 
#RTLDAQLOG="rtl_daq.log"
#SYNCLOG="sync.log"
#GATELOG="gate.log"
#PYTHONLOG="python.log"

RTLDAQLOG="/dev/null"
SYNCLOG="/dev/null"
GATELOG="/dev/null"
PYTHONLOG="/dev/null"

# If you want to kill all matching processes on startup without prompt. Otherwise, set it to anything else. 
FORCE_KILL="yes"

NPROC=`expr $(nproc) - 1`

### Uncomment the following section to automatically get the IP address from interface wlan0 ###
### Don't forget to comment out "IPADDR="0.0.0.0" ###

# IPADDR=$(ip addr show wlan0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
# while [ "$IPADDR" == "" ] || [ "$IPADDR" == "169.254.*" ]
# do
# sleep 1
# echo "waiting for network"
# IPADDR=$(ip addr show wlan0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
# echo $IPADDR
# done

### End of Section ###

# Useful to set this on low power ARM devices
#sudo cpufreq-set -g performance

# Set for RPI3 with heatsink/fan
#sudo cpufreq-set -d 1.4GHz
# Set for Tinkerboard with heatsink/fan
#sudo cpufreq-set -d 1.8GHz


# Trap SIGINT (2) (ctrl-C) as well as SIGTERM (6), run cleanup if either is caught
trap cleanup 2 6

cleanup() {
	# Kill all processes that have been spawned by this program.
	# we know that these processes have "_receiver", "_GUI" and "_webDisplay" in their names. 
	exec 2> /dev/null           # Suppress "Terminated" message. 
	sudo pkill -f "_receiver" 
	
	# also delete all pipes: 
	rm -f _receiver/gate_control_fifo
        rm -f _receiver/sync_control_fifo
        rm -f _receiver/rec_control_fifo
}


# Clear memory
sudo sh -c "echo 0 > /sys/module/usbcore/parameters/usbfs_memory_mb"
echo '3' | sudo dd of=/proc/sys/vm/drop_caches status=none
		
#sudo kill $(ps aux | grep 'rtl' | awk '{print $2}') 2>$OUTPUT_FD || true


# Enable on the Pi 3 to prevent the internet from hogging the USB bandwidth
#sudo wondershaper wlan0 3000 3000
#sudo wondershaper eth0 3000 3000

sleep 1

# Remake Controller FIFOs. Deleting them should not be neccessary after 
# a clean exit, but why not do it anyway... 
rm -f _receiver/gate_control_fifo
mkfifo _receiver/gate_control_fifo

rm -f _receiver/sync_control_fifo
mkfifo _receiver/sync_control_fifo

rm -f _receiver/rec_control_fifo
mkfifo _receiver/rec_control_fifo

# Start programs at realtime priority levels
curr_user=$(whoami)

sudo chrt -r 50 taskset -c $NPROC ionice -c 1 -n 0 ./_receiver/rtl_daq $BUFF_SIZE 2>$RTLDAQLOG 1| \
	sudo chrt -r 50 taskset -c $NPROC ./_receiver/sync $BUFF_SIZE 2>$SYNCLOG 1| \
	sudo chrt -r 50 taskset -c $NPROC ./_receiver/gate $BUFF_SIZE 2>$GATELOG 1| \
	sudo python3 ./run_sdrs.py

