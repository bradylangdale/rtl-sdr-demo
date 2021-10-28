from receiver import ReceiverRTLSDR
from signal_processor import SignalProcessor

import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

sdrs = ReceiverRTLSDR()
processing = SignalProcessor(module_receiver=sdrs)

center_freq = 430
sample_rate = 1.024
gain = np.ones(4) * 40.2 # 40.2 49.6

sdrs.reconfigure_tuner(center_freq=center_freq * 10**6, sample_rate=sample_rate * 10**6, gain=gain * 10)

def sampleSynced():
    synced = 0
    for num in processing.delay_log:
        if not num[-1] == 0:
            synced += 1
    return synced == 0

def phaseSynced():
    synced = 0
    for num in processing.phase_log:
        if not abs(num[-1]) <= 2:
            synced += 1
    return synced == 0

def sync_radios():
    sdrs.switch_noise_source(True)

    while not sampleSynced():
        processing.update_data()
        processing.sample_delay()
        processing.sample_offset_sync()
        processing.update_data()

    print('sample synced!')
    for num in processing.delay_log:
        print(num[-1])

    while not phaseSynced():
        processing.update_data()
        processing.calib_iq()
        processing.update_data()
        processing.sample_delay()

    print('phase synced')
    for phase in processing.phase_log:
        print(phase[-1])

    sdrs.switch_noise_source(False)

processing.update_data()
processing.sample_delay()
sync_radios()

# lets make us MUSIC
sdrs.decimation_ratio = 4
sdrs.set_fir_coeffs(150, 50 * 10**3)
processing.DOA_inter_elem_space = 0.05
processing.update_data()

iq_samples = [sdrs.iq_samples]
processing.estimate_DOA(iq_samples)

doa_avg = [processing.DOA_MUSIC_res]

def draw_graphs(i):
    doa.cla()
    delay.cla()
    phase.cla()

    [delay.plot(processing.delay_log[i]) for i in range(0, 2)]
    [phase.plot(processing.phase_log[i]) for i in range(0, 2)]

    processing.update_data()
    processing.sample_delay()

    doa_avg.append(processing.DOA_MUSIC_res)
    if len(doa_avg) > 2: doa_avg.pop(0)

    iq_samples.append(sdrs.iq_samples)
    if len(iq_samples) > 2: iq_samples.pop(0)

    processing.estimate_DOA(iq_samples)
    
    doa.plot([np.mean(k) for k in zip(*[np.array(x) for x in doa_avg])])
    #doa.plot(range(-90, 91), doa_avg)

# define and adjust figure
fig, (doa, delay, phase) = plt.subplots(3)

ani = FuncAnimation(fig, draw_graphs, interval=50)

plt.show()
