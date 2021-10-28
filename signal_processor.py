# Brady Langdale FSR Demo

import sys
import os
import time

# Math support
import numpy as np

# Signal processing support
from scipy import fft,ifft
from scipy import signal
from scipy.signal import correlate

from pyargus import directionEstimation as de

from pyapril import channelPreparation as cp
from pyapril import clutterCancellation as cc
from pyapril import detector as det
from pyapril import caCfar

class SignalProcessor():

    def __init__(self, module_receiver):

        self.module_receiver = module_receiver

        # DOA processing options
        self.DOA_inter_elem_space = 0.5
        
        # Passive Radar processing parameters
        self.ref_ch_id = 0
        self.surv_ch_id = 1
        self.en_td_filtering = False
        self.td_filter_dimension = 1        
        self.max_Doppler = 500  # [Hz]
        self.windowing_mode = 0
        self.max_range = 128  # [range cell]
        self.cfar_win_params = [10,10,4,4] # [Est. win length, Est. win width, Guard win length, Guard win width]
        self.cfar_threshold = 13
        self.RD_matrix = np.ones((10,10))
        self.hit_matrix = np.ones((10,10))
        self.RD_matrix_last = np.ones((10,10))
        self.RD_matrix_last_2 = np.ones((10,10))
        self.RD_matrix_last_3 = np.ones((10,10))
        
        self.center_freq = 0  # TODO: Initialize this [Hz]
        self.fs = 1.024 * 10**6  # Decimated sampling frequncy - Update from GUI
        self.channel_number = 3
        
        # Processing parameters        
        self.test = None
        self.spectrum_sample_size = 2**14 #2**14
        self.DOA_sample_size = 2**15 # Connect to GUI value??
        self.xcorr_sample_size = 2**18 #2**18
        self.xcorr = np.ones((self.channel_number-1,self.xcorr_sample_size*2), dtype=np.complex64)        
        
        # Result vectors
        self.delay_log= np.array([[0],[0]])
        self.phase_log= np.array([[0],[0]])
        self.DOA_MUSIC_res = np.ones(181)
        self.DOA_theta = np.arange(0,181,1)

    def update_data(self):
        self.module_receiver.download_iq_samples()
        self.DOA_sample_size = self.module_receiver.iq_samples[0,:].size
        self.xcorr_sample_size = self.module_receiver.iq_samples[0,:].size
        self.xcorr = np.ones((self.channel_number-1,self.xcorr_sample_size*2), dtype=np.complex64)   
            
            
    def sample_offset_sync(self):
        self.module_receiver.set_sample_offsets(self.delay_log[:,-1])  
            
    def calib_iq(self):
        # IQ correction
        for m in range(self.channel_number):
            self.module_receiver.iq_corrections[m] *= np.size(self.module_receiver.iq_samples[0, :])/(np.dot(self.module_receiver.iq_samples[m, :], self.module_receiver.iq_samples[0, :].conj()))
            c = np.sqrt(np.sum(np.abs(self.module_receiver.iq_corrections)**2))

        self.module_receiver.iq_corrections = np.divide(self.module_receiver.iq_corrections, c)

    def sample_delay(self):
        N = self.xcorr_sample_size
        iq_samples = self.module_receiver.iq_samples[:, 0:N]
       
        delays = np.array([[0],[0]])
        phases = np.array([[0],[0]])
        
        # Channel matching
        np_zeros = np.zeros(N, dtype=np.complex64)
        x_padd = np.concatenate([iq_samples[0, :], np_zeros])
        x_fft = np.fft.fft(x_padd)
        
        for m in np.arange(1, self.channel_number):
            y_padd = np.concatenate([np_zeros, iq_samples[m, :]])
            y_fft = np.fft.fft(y_padd)
            
            self.xcorr[m-1] = np.fft.ifft(x_fft.conj() * y_fft)
            
            delay = np.argmax(np.abs(self.xcorr[m-1])) - N
            phase = np.rad2deg(np.angle(self.xcorr[m-1, N]))

            delays[m-1,0] = delay
            phases[m-1,0] = phase

        if (len(self.delay_log[0]) > 50):
            self.delay_log = np.concatenate((self.delay_log, delays),axis=1)[:,1:]
            self.phase_log = np.concatenate((self.phase_log, phases),axis=1)[:,1:]
        else:
            self.delay_log = np.concatenate((self.delay_log, delays),axis=1)
            self.phase_log = np.concatenate((self.phase_log, phases),axis=1)
    
    def delete_sync_history(self):
        self.delay_log= np.array([[0],[0]])
        self.phase_log= np.array([[0],[0]])

    def estimate_DOA(self, iq_samples_list):
        #print("[ INFO ] Python DSP: Estimating DOA")

        #iq_samples = self.module_receiver.iq_samples[:, 0:self.DOA_sample_size]
        iq_samples = iq_samples_list[0]
        #for i in range(1, len(iq_samples_list)):
        #    iq_samples = np.concatenate((iq_samples, iq_samples_list[i]),axis=1)
        
        # Calculating spatial correlation matrix
        R = de.corr_matrix_estimate(iq_samples.T, imp="fast")

        R=de.forward_backward_avg(R)

        M = np.size(iq_samples, 0)

        self.DOA_theta =  np.linspace(-90,90,181)
        x = np.zeros(M)
        y = np.arange(M) * self.DOA_inter_elem_space            
        scanning_vectors = de.gen_scanning_vectors(M, x, y, self.DOA_theta)

        self.DOA_MUSIC_res = de.DOA_MUSIC(R, scanning_vectors, signal_dimension = 1)

