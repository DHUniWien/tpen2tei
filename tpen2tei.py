#!/usr/bin/env python3

""" tpen2tei.py assumes all files in indir to be T-PEN output
    and tries to convert them to TEI-XML in outdir
"""

import traceback
import os
import fnmatch
import sys
import json
import logging
import argparse

from parse import from_sc

parser = argparse.ArgumentParser()
parser.add_argument ("indir", help = "input directory, T-PEN output files")
parser.add_argument ("outdir", help = "output directory")
parser.add_argument ("-w", "--write_stdout_stderr", action = "store_true", help = "write stdout and stderr to separate files in outdir")
args = parser.parse_args()

logging.basicConfig (
    format = '%(asctime)s %(message)s',
    filename = '%s.log' % sys.argv[0],
)


for infile in fnmatch.filter (os.listdir (args.indir), '*json'):
    outfile = infile + '.tei.xml'

    if args.write_stdout_stderr:
        sys.stdout = open (args.outdir + '/' + infile + '.stdout', 'w')
        sys.stderr = open (args.outdir + '/' + infile + '.stderr', 'w')

    with open (args.indir + '/' + infile, 'r') as fh:
        data = json.load (fh)

        try:
            tei = from_sc (data)

            # just ignore tei==None
            tei and tei.write (
                args.outdir + '/' + outfile,
                encoding = 'utf8',
                pretty_print = True,
            )

        except Exception as e:
            logging.error ('error with file <%s>: %s\n' % (infile, traceback.format_exc()))
        else:
            logging.error ('file <%s> looks good' % infile)
