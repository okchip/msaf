#!/usr/bin/env python
'''Runs the SIPLCA segmenter for boundaries and labels across the 
a segmentation dataset.

'''

__author__ = "Oriol Nieto"
__copyright__ = "Copyright 2014, Music and Audio Research Lab (MARL)"
__license__ = "GPL"
__version__ = "1.0"
__email__ = "oriol@nyu.edu"

import sys
import glob
import os
import argparse
import numpy as np
import time
import logging
import jams

# SI-PLCA segmenter
import segmenter as S

import sys
sys.path.append("../../")
import msaf_io as MSAF


def process(in_path, annot_beats=False, annot_bounds=False):
    """Main process."""

    # Get relevant files
    jam_files = glob.glob(os.path.join(in_path, "annotations", "*.jams"))
    audio_files = glob.glob(os.path.join(in_path, "audio", "*.[wm][ap][v3]"))

    for jam_file, audio_file in zip(jam_files, audio_files):
        assert os.path.basename(audio_file)[:-4] == \
            os.path.basename(jam_file)[:-5]

        # Only analize files with annotated beats
        if annot_beats:
            jam = jams.load(jam_file)
            if jam.beats == []:
                continue
            if jam.beats[0].data == []:
                continue

        logging.info("Segmenting %s" % audio_file)

        # SI-PLCA Params (From MIREX)
        params = {
            "niter"             :   200,
            "rank"              :   15,
            "win"               :   60,
            "alphaZ"            :   -0.01,
            "normalize_frames"  :   True,
            "viterbi_segmenter" :   True
        }
        segments, beattimes, frame_labels = S.segment_wavfile(
            audio_file, b=annot_beats, **params)

        # Convert segments to times
        lines = segments.split("\n")[:-1]
        times = []
        labels = []
        for line in lines:
            time = float(line.strip("\n").split("\t")[0])
            times.append(time)
            label = line.strip("\n").split("\t")[2]
            labels.append(ord(label))

        if annot_bounds:
            chroma, mfcc, beats, dur = MSAF.get_features(
                audio_file, annot_beats=annot_beats)
            try:
                bound_idxs = MSAF.read_annot_bound_frames(audio_file, beats)
            except:
                logging.warning("No annotation boundaries for %s" %
                                audio_file)
                continue

            labels = []
            start = bound_idxs[0]
            for end in bound_idxs[1:]:
                segment_labels = frame_labels[start:end]
                label = np.argmax(np.bincount(segment_labels))
                labels.append(label)
                start = end

        # Add last one and reomve empty segments
        times, idxs = np.unique(times, return_index=True)
        labels = np.asarray(labels)[idxs]
        times = np.concatenate((times,
                                [float(lines[-1].strip("\n").split("\t")[1])]))
        times = np.unique(times)

        # Save segments
        out_file = os.path.join(in_path, "estimations",
            os.path.basename(jam_file).replace(".jams", ".json"))
        if not annot_bounds:
            MSAF.save_estimations(out_file, times, annot_beats, "siplca",
                version="1.0", **params)
        MSAF.save_estimations(out_file, labels, annot_beats, "siplca",
            bounds=False, version="1.0", **params)


def main():
    """Main function to parse the arguments and call the main process."""
    parser = argparse.ArgumentParser(description=
        "Runs the OLDA segmenter across a the Segmentation dataset and "
        "stores the results in the estimations folder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("in_path",
                        action="store",
                        help="Input dataset")
    parser.add_argument("-b",
                        action="store_true",
                        dest="annot_beats",
                        help="Use annotated beats",
                        default=False)
    parser.add_argument("-bo",
                        action="store_true",
                        dest="annot_bounds",
                        help="Use annotated bounds",
                        default=False)
    args = parser.parse_args()
    start_time = time.time()

    # Setup the logger
    logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
        level=logging.INFO)

    # Run the algorithm
    process(args.in_path, annot_beats=args.annot_beats, 
            annot_bounds=args.annot_bounds)

    # Done!
    logging.info("Done! Took %.2f seconds." % (time.time() - start_time))


if __name__ == '__main__':
    main()
