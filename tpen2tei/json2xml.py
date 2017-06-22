#!/usr/bin/env python3

import traceback
import os
import fnmatch
import sys
import json
import logging
import argparse

from tpen2tei.parse import from_sc


def json2xml (**kwa):
    """ json2xml assumes all files in indir to be T-PEN output
        and tries to convert them to TEI-XML in outdir

        see moe-data/ci/resources/json2xml.py for an example usage
    """

    indir          = kwa.get ('indir')
    outdir         = kwa.get ('outdir')
    metadata       = kwa.get ('metadata')
    special_chars  = kwa.get ('special_chars')
    numeric_parser = kwa.get ('numeric_parser')
    write_stdout_stderr = kwa.get ('write_stdout_stderr')

    for infile in fnmatch.filter (os.listdir (indir), '*json'):
        outfile = infile + '.tei.xml'

        if write_stdout_stderr:
            sys.stdout = open (outdir + '/' + infile + '.stdout', 'w')
            sys.stderr = open (outdir + '/' + infile + '.stderr', 'w')

        with open (indir + '/' + infile, 'r') as fh:
            data = json.load (fh)

            try:
                tei = from_sc (
                    data,
                    metadata       = metadata,
                    special_chars  = special_chars,
                    numeric_parser = numeric_parser,
                )

                # just ignore tei==None
                if tei:
                    tei.write (
                        outdir + '/' + outfile,
                        encoding = 'utf8',
                        pretty_print = True,
                    )

                    logging.error ('file <%s> looks good' % infile)
                else:
                    logging.error ('error with file <%s>: tpen2tei.parse.from_sc did not return anything' % infile)

            except Exception as e:
                logging.error ('error with file <%s>: %s\n' % (infile, traceback.format_exc()))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument (
         "indir",
         help = "input directory t-pen output files",
    )
    parser.add_argument (
        "outdir",
        help = "output directory",
    )
    parser.add_argument (
        "-w",
        "--write_stdout_stderr",
        action = "store_true",
        help = "write stdout and stderr to separate files in outdir",
    )

    args = parser.parse_args()

    #  logging.basicConfig (
    #      format = '%(asctime)s %(message)s',
    #      filename = '%s.log' % os.path.basename (sys.argv[0]),
    #  )

    json2xml (
        indir               = args.indir,
        outdir              = args.outdir,
        write_stdout_stderr = args.write_stdout_stderr,
        metadata            = None,
        special_chars       = None,
        numeric_parser      = None,
    )
