#!/usr/bin/env python
"""
This script uses Essentia in order to extract a set of features to be used
as input for the segmentation algorithms.

Features to be computed:

- MFCC: Mel Frequency Cepstral Coefficients
- HPCP: Harmonic Pithc Class Profile
- Beats
"""

__author__ = "Oriol Nieto"
__copyright__ = "Copyright 2014, Music and Audio Research Lab (MARL)"
__license__ = "GPL"
__version__ = "1.0"
__email__ = "oriol@nyu.edu"

import argparse
import essentia
import essentia.standard as ES
from essentia.standard import YamlOutput
import pylab as plt
import logging
import time

class STFTFeature:
    """Class to easily compute the features that require a frame based 
        spectrum process (or STFT)."""
    def __init__(self, frame_size, hop_size, window_type, feature):
        """STFTFeature constructor."""
        self.frame_size = frame_size
        self.hop_size = hop_size
        self.window_type = window_type
        self.w = ES.Windowing(type=window_type)
        self.spectrum = ES.Spectrum()
        self.feature = feature # Essentia feature object

    def compute_features(self, audio):
        """Computes the specified Essentia features from the audio array."""
        features = []

        for frame in ES.FrameGenerator(audio, 
                frameSize=self.frame_size, hopSize=self.hop_size):
            if self.feature.name() == "MFCC":
                bands, coeffs = self.feature(self.spectrum(self.w(frame)))
            elif self.feature.name() == "HPCP":
                spectral_peaks = ES.SpectralPeaks()
                freqs, mags = spectral_peaks(self.spectrum(self.w(frame)))
                coeffs = self.feature(freqs, mags)
            features.append(coeffs)

        # Convert to Numpy array
        features = essentia.array(features)

        return features

def process(audio_file, out_file, save_beats=False):
    """Main process."""

    # Setup main params
    sample_rate = 11025
    frame_size = 2048
    hop_size = 512
    window_type = "blackmanharris74"

    # Load Audio
    logging.info("Loading Audio")
    audio = ES.MonoLoader(filename=audio_file, sampleRate=sample_rate)()

    # Compute Features
    MFCC = STFTFeature(frame_size, hop_size, window_type, ES.MFCC())
    HPCP = STFTFeature(frame_size, hop_size, window_type, ES.HPCP())
    logging.info("Computing MFCCs...")
    mfcc = MFCC.compute_features(audio)
    logging.info("Computing HPCPs...")
    hpcp = HPCP.compute_features(audio)
    plt.imshow(hpcp.T, interpolation="nearest", aspect="auto"); plt.show()
    logging.info("Obtaining Beats...")
    ticks, conf = ES.BeatTrackerMultiFeature()(audio)

    # Save output as audio file
    if save_beats:
        logging.info("Saving Beats as an audio file")
        marker = ES.AudioOnsetsMarker(onsets=ticks, type='beep')
        marked_audio = marker(audio)
        ES.MonoWriter(filename='beats.wav')(marked_audio)

    # Save output as json file
    logging.info("Saving the JSON file")
    yaml = YamlOutput(filename=out_file, format='json')
    pool = essentia.Pool()
    pool.add("beats.ticks", ticks)
    pool.add("beats.confidence", conf)
    yaml(pool)


def main():
    """Main function to parse the arguments and call the main process."""
    parser = argparse.ArgumentParser(description=
        "Extracts a set of features from an audio file and saves them " \
            "into a JSON file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("audio_file",action="store",
        help="Input audio file")
    parser.add_argument("-o", action="store", dest="out_file", 
        default="output.json", help="Output JSON file")
    args = parser.parse_args()
    start_time = time.time()
   
    # Setup the logger
    logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)

    # Run the algorithm
    process(args.audio_file, args.out_file)

    # Done!
    logging.info("Done! Took %.2f seconds." % (time.time() - start_time))

if __name__ == '__main__':
    main()