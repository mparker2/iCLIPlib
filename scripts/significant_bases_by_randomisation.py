################################################################################
#
#   MRC FGU Computational Genomics Group
#
#   $Id: cgat_script_template.py 2871 2010-03-03 10:20:44Z andreas $
#
#   Copyright (C) 2009 Andreas Heger
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#################################################################################
'''
signficant_bases_by_randomisation.py
=============================================

:Author: Ian Sudbery
:Release: $Id$
:Date: |today|
:Tags: Python

Purpose
-------

This script will calculate significant bases using the method described
in Wang et al, PLoS Biol. 2010:e1000530 :PMID:`21048981`.

Within each transcript/intron the number of crosslinks within a certain
number of bases is summed to be the score for that bases. The empircal
distribution of score is calculated on a per transcript basis and the FDR for
this is calcluated by using randomizations of the profile accross the interval.

Bases meeting a certain threshold are returned as a bedgraph file

Usage
-----

python significant_bases_by_randomisation.py -b BAMFILE -I GTFFILE [OPTIONS]

Example::

   zcat transcriptome.gtf.gz
 | python significant_bases_by_randomisation.py
      -b myiCLIP.bam
 > significant_bases.bedgraph

Type::

   python significant_bases_by_randomisation.py --help

for command line help.

Command line options
--------------------

'''

import sys
import os
import pysam
import numpy

import CGAT.Experiment as E
import CGAT.GTF as GTF

sys.path.insert(1, os.path.join(
    os.path.dirname(__file__), ".."))

import iCLIP


def main(argv=None):
    """script main.

    parses command line options in sys.argv, unless *argv* is given.
    """

    if not argv:
        argv = sys.argv

    # setup command line parser
    parser = E.OptionParser(version="%prog version: $Id$",
                            usage=globals()["__doc__"])

    parser.add_option("-b", "--bam-file", dest="bam", type="string",
                      help="BAM file containing iCLIP reads", default=None)
    parser.add_option("-w", "--wig", "--plus-wig", dest="plus_wig", type="string",
                      help="BigWig file containing signal for already processed sample",
                      default=None)
    parser.add_option("--minus-wig", dest="minus_wig", type="string",
                      help="BigWig file containing signal for sample on minus strand",
                      default=None)
    parser.add_option("--bed", dest="bedfile", type="string",
                      help="Bed file containing signal for sample")
    parser.add_option("-s", "--spread", dest="spread", type="int",
                      default=15,
                      help="Number of bases each site of each bases"
                           "to use when calculating height")
    parser.add_option("-r", "--randomisations", dest="rands", type="int",
                      default=100,
                      help="Number of randomisations to use when"
                           "calculating FDR")
    parser.add_option("-t", "--threshold", dest="threshold", type="float",
                      default=0.05,
                      help="FDR threshold on which to select bases")
    parser.add_option("-f", "--feature", dest="feature", type="choice",
                      choices=["transcript", "gene"],
                      default="gene",
                      help="GTF feature to use. Gene or transcript")
    parser.add_option("-p", "--processes", dest="proc", type="int",
                      default=None,
                      help="Number of processes to use for multiprocessing")
    parser.add_option("-c", "--centre", dest="centre", action="store_true",
                      default=False,
                      help="Use centre of read instead of -1 when no"
                      "mutation is present")

    # add common options (-h/--help, ...) and parse command line
    (options, args) = E.Start(parser, argv=argv)

    if options.proc is not None:
        try:
            import multiprocessing
            pool = multiprocessing.Pool(options.proc)
            E.debug("Operating in multiprocessing mode")
        except ImportError:
            E.warn("Failed to setup multiprocessing, using single processor")
            pool = None
    else:
        E.debug("Operating in single processor mode")
        pool = None

    if options.feature == "gene":
        iterator = GTF.flat_gene_iterator(GTF.iterator(options.stdin))
    elif options.feature == "transcript":
        iterator = GTF.transcript_iterator(GTF.iterator(options.stdin))
    else:
        raise ValueError("Unknown feature type %s" % options.feature)

    if options.bam:
        bam = iCLIP.make_getter(options.bam, centre=options.centre)
    elif options.plus_wig:
        bam = iCLIP.make_getter(plus_wig=options.plus_wig,
                                minus_wig=options.minus_wig)
    elif options.bedfile:
        bam = iCLIP.make_getter(bedfile=options.bedfile)
    else:
        E.error("Please specifiy one of bam file, bed file or wig file")
        sys.exit(1)

    results = iCLIP.get_crosslink_fdr_by_randomisation(
        iterator, bam, options.rands, options.spread, pool)

    results = results[results.fdr <= options.threshold]
    results = results.reset_index()
    results.columns = ["contig", "start", "FDR", "depth", "strand"]

    # Deal with case where there is more than one value on a base. Keep one with
    # lowest FDR.
    results = results.sort_values(by=["FDR", "depth"], ascending=[True, False])
    results = results.drop_duplicates(["contig", "start", "strand"])
    results = results.sort_values(["contig", "start", "strand"])
    
    results["start"] = results["start"].astype("int")
    results["end"] = results.start + 1
    results = results.loc[:, ["contig", "start", "end", "FDR", "depth", "strand"]]
    results["FDR"] = -numpy.log10(results["FDR"])
    results.to_csv(options.stdout, header=False, index=False, sep="\t")
    # write footer and output benchmark information.
    E.Stop()

if __name__ == "__main__":
    sys.exit(main(sys.argv))

