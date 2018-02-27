#!/usr/bin/env python2.7
"""
vg_config.py: Default configuration values all here (and only here), as well as logic
for reading and generating config files.

"""
from __future__ import print_function
import argparse, sys, os, os.path, errno, random, subprocess, shutil, itertools, glob, tarfile
import doctest, re, json, collections, time, timeit
import logging, logging.handlers, SocketServer, struct, socket, threading
import string
import urlparse
import getpass
import pdb
import textwrap
import yaml
from toil_vg.vg_common import require, test_docker

default_config = textwrap.dedent("""
# Toil VG Pipeline configuration file (created by toil-vg generate-config)
# This configuration file is formatted in YAML. Simply write the value (at least one space) after the colon.
# Edit the values in the configuration file and then rerun the pipeline: "toil-vg run"
# 
# URLs can take the form: "/", "s3://"
# Local inputs follow the URL convention: "/full/path/to/input.txt"
# S3 URLs follow the convention: "s3://bucket/directory/file.txt"
#
# Comments (beginning with #) do not need to be removed. 
# Command-line options take priority over parameters in this file.  
######################################################################################################################

###########################################
### Toil resource tuning                ###

# These parameters must be adjusted based on data and cluster size
# when running on anything other than single-machine mode

# TODO: Reduce number of parameters here.  Seems fine grained, especially for disk/mem
# option to spin off config files for small/medium/large datasets?   

# The following parameters assign resources to small helper jobs that typically don't do 
    # do any computing outside of toil overhead.  Generally do not need to be changed. 
misc-cores: 1
misc-mem: '1G'
misc-disk: '1G'

# Resources allotted for vg construction.
construct-cores: 1
construct-mem: '4G'
construct-disk: '2G'

# Resources allotted for xg indexing.
# this stage generally cannot take advantage of more than one thread except GBWT
xg-index-cores: 1
xg-index-mem: '4G'
xg-index-disk: '2G'

# Resources allotted for gcsa pruning.  Note that the vg mod commands used in
# this stage generally cannot take advantage of more than one thread
prune-cores: 1
prune-mem: '4G'
prune-disk: '2G'

# Resources allotted for gcsa kmers.  
kmers-cores: 1
kmers-mem: '4G'
kmers-disk: '2G'

# Resources allotted gcsa indexing
gcsa-index-cores: 1
gcsa-index-mem: '4G'
gcsa-index-disk: '2G'

# Resources for fastq splitting and gam merging
# Important to assign as many cores as possible here for large fastq inputs
fq-split-cores: 1
fq-split-mem: '4G'
fq-split-disk: '2G'

# Number of threads to use for Rocksdb GAM indexing
# Generally, this should be kept low as speedup drops off radically 
# after a few threads.
gam-index-cores: 1

# Resources for *each* vg map job
# the number of vg map jobs is controlled by reads-per-chunk (below)
alignment-cores: 1
alignment-mem: '4G'
alignment-disk: '2G'

# Resources for chunking up a graph/gam for calling (and merging)
# typically take xg for whoe grpah, and gam for a chromosome,
# and split up into chunks of call-chunk-size (below)
call-chunk-cores: 1
call-chunk-mem: '4G'
call-chunk-disk: '2G'

# Resources for calling each chunk (currently includes augment/call/genotype)
calling-cores: 1
calling-mem: '4G'
calling-disk: '2G'

# Resources for vcfeval
vcfeval-cores: 1
vcfeval-mem: '4G'
vcfeval-disk: '2G'

# Resources for vg sim
sim-cores: 2
sim-mem: '4G'
sim-disk: '2G'

###########################################
### Arguments Shared Between Components ###
# Use output store instead of toil for all intermediate files (use only for debugging)
force-outstore: False

# Toggle container support.  Valid values are Docker / Singularity / None
# (commenting out or Null values equivalent to None)
container: """ + ("Docker" if test_docker() else "None") + """

#############################
### Docker Tool Arguments ###

## Docker Tool List ##
##   Locations of docker images. 
##   If empty or commented, then the tool will be run directly from the command line instead
##   of through docker. 

# Docker image to use for vg
vg-docker: 'quay.io/vgteam/vg:v1.6.0-442-gd3a69a42-t134-run'

# Docker image to use for bcftools
bcftools-docker: 'vandhanak/bcftools:1.3.1'

# Docker image to use for tabix
tabix-docker: 'vandhanak/bcftools:1.3.1'

# Docker image to use for samtools
samtools-docker: 'quay.io/ucsc_cgl/samtools:latest'

# Docker image to use for bwa
bwa-docker: 'quay.io/ucsc_cgl/bwa:latest'

# Docker image to use for jq
jq-docker: 'devorbitus/ubuntu-bash-jq-curl'

# Docker image to use for rtg
rtg-docker: 'realtimegenomics/rtg-tools:3.8.4'

# Docker image to use for pigz
pigz-docker: 'quay.io/glennhickey/pigz:latest'

# Docker image to use to run R scripts
r-docker: 'rocker/tidyverse:latest'

# Docker image to use for vcflib
vcflib-docker: 'quay.io/biocontainers/vcflib:1.0.0_rc1--0'

# Docker image to use for Freebayes
freebayes-docker: 'maxulysse/freebayes:1.2.5'

##########################
### vg_index Arguments ###

# Name of index output files.  ex <name>.xg, <name>.gcsa etc. 
index-name: 'genome'

# Options to pass to vg mod for pruning phase.
# The primary path(s) will always be added back onto the pruned grpah
# Phase skipped if empty.  If list of lists, mod commands will be chained together
prune-opts: [['-D'], ['-p', '-l', '16', '-S', '-e', '5'], ['-S', '-l', '32']]

# Options to pass to vg kmers.
kmers-opts: ['-g', '-B', '-k', '16']

# Options to pass to vg gcsa indexing
gcsa-opts: ['-X', '3', '-Z', '3000']

########################
### vg_map Arguments ###

# Toggle whether reads are split into chunks
single-reads-chunk: False

# Number of reads per chunk to use when splitting up fastq.
# (only applies if single-reads-chunk is False)
# Each chunk will correspond to a vg map job
reads-per-chunk: 10000000

# Core arguments for vg mapping (do not include file names or -t/--threads)
# Note -i/--interleaved will be ignored. use the --interleaved option 
# on the toil-vg command line instead
map-opts: []

# Core arguments for vg multipath mapping (do not include file names or -t/--threads)
mpmap-opts: ['-S']

#########################
### vg_call Arguments ###
# Overlap option that is passed into make_chunks and call_chunk
overlap: 2000

# Chunk size
call-chunk-size: 2000000

# Context expansion used for graph chunking
chunk_context: 50

# Options to pass to vg filter when running vg call. (do not include file names or -t/--threads)
filter-opts: ['-r', '0.9', '-fu', '-s', '1000', '-m', '1', '-q', '15', '-D', '999']

# Options to pass to vg augment. (do not include any file names or -t/--threads or -a/--augmentation-mode)
augment-opts: ['-q', '10']

# Options to pass to vg call. (do not include file/contig/sample names or -t/--threads)
call-opts: []

# Options to pass to vg genotype. (do not include file/contig/sample names or -t/--threads)
genotype-opts: []

# Use vg genotype instead of vg call
genotype: False

#########################
### vcfeval Arguments ###
# Options to pass to rgt vcfeval. (do not include filenaems or threads or BED)
vcfeval-opts: ['--ref-overlap', '--vcf-score-field', 'QUAL']

#########################
### sim and mapeval Arguments ###
# Options to pass to vg sim (should not include -x, -n, -s or -a)
sim-opts: ['-l', '150', '-p', '570', '-v', '165', '-e', '0.01', '-i', '0.002']

# Options to pass to bwa
bwa-opts: []

""")

whole_genome_config = textwrap.dedent("""
# Toil VG Pipeline configuration file (created by toil-vg generate-config)
# This configuration file is formatted in YAML. Simply write the value (at least one space) after the colon.
# Edit the values in the configuration file and then rerun the pipeline: "toil-vg run"
# 
# URLs can take the form: "/", "s3://"
# Local inputs follow the URL convention: "/full/path/to/input.txt"
# S3 URLs follow the convention: "s3://bucket/directory/file.txt"
#
# Comments (beginning with #) do not need to be removed. 
# Command-line options take priority over parameters in this file.  
######################################################################################################################

###########################################
### Toil resource tuning                ###

# These parameters must be adjusted based on data and cluster size
# when running on anything other than single-machine mode

# TODO: Reduce number of parameters here.  Seems fine grained, especially for disk/mem
# option to spin off config files for small/medium/large datasets?   

# The following parameters assign resources to small helper jobs that typically don't do 
    # do any computing outside of toil overhead.  Generally do not need to be changed. 
misc-cores: 1
misc-mem: '1G'
misc-disk: '1G'

# Resources allotted for vg construction.
construct-cores: 1
construct-mem: '32G'
construct-disk: '32G'

# Resources allotted for xg indexing.
# this stage generally cannot take advantage of more than one thread except GBWT
xg-index-cores: 32
xg-index-mem: '200G'
xg-index-disk: '200G'

# Resources allotted for gcsa pruning.  Note that the vg mod commands used in
# this stage generally cannot take advantage of more than one thread
prune-cores: 2
prune-mem: '60G'
prune-disk: '60G'

# Resources allotted for gcsa kmers.  
kmers-cores: 16
kmers-mem: '70G'
kmers-disk: '60G'

# Resources allotted gcsa indexing
# Note for a whole genome 1kg graph, need about 3000G of disk
gcsa-index-cores: 32
gcsa-index-mem: '200G'
gcsa-index-disk: '200G'

# Resources for fastq splitting and gam merging
# Important to assign as many cores as possible here for large fastq inputs
fq-split-cores: 32
fq-split-mem: '4G'
fq-split-disk: '200G'

# Number of threads to use for Rocksdb GAM indexing
# Generally, this should be kept low as speedup drops off radically 
# after a few threads.
gam-index-cores: 6

# Resources for *each* vg map job
# the number of vg map jobs is controlled by reads-per-chunk (below)
alignment-cores: 32
alignment-mem: '100G'
alignment-disk: '100G'

# Resources for chunking up a graph/gam for calling (and merging)
# typically take xg for whoe grpah, and gam for a chromosome,
# and split up into chunks of call-chunk-size (below)
call-chunk-cores: 8
call-chunk-mem: '100G'
call-chunk-disk: '100G'

# Resources for calling each chunk (currently includes augment/call/genotype)
calling-cores: 2
calling-mem: '32G'
calling-disk: '8G'

# Resources for vcfeval
vcfeval-cores: 32
vcfeval-mem: '64G'
vcfeval-disk: '64G'

# Resources for vg sim
sim-cores: 2
sim-mem: '60G'
sim-disk: '200G'

###########################################
### Arguments Shared Between Components ###
# Use output store instead of toil for all intermediate files (use only for debugging)
force-outstore: False

# Toggle container support.  Valid values are Docker / Singularity / None
# (commenting out or Null values equivalent to None)
container: """ + ("Docker" if test_docker() else "None") + """

#############################
### Docker Tool Arguments ###

## Docker Tool List ##
##   Locations of docker images. 
##   If empty or commented, then the tool will be run directly from the command line instead
##   of through docker. 

# Docker image to use for vg
vg-docker: 'quay.io/vgteam/vg:v1.6.0-442-gd3a69a42-t134-run'

# Docker image to use for bcftools
bcftools-docker: 'vandhanak/bcftools:1.3.1'

# Docker image to use for tabix
tabix-docker: 'vandhanak/bcftools:1.3.1'

# Docker image to use for samtools
samtools-docker: 'quay.io/ucsc_cgl/samtools:latest'

# Docker image to use for bwa
bwa-docker: 'quay.io/ucsc_cgl/bwa:latest'

# Docker image to use for jq
jq-docker: 'devorbitus/ubuntu-bash-jq-curl'

# Docker image to use for rtg
rtg-docker: 'realtimegenomics/rtg-tools:3.8.4'

# Docker image to use for pigz
pigz-docker: 'quay.io/glennhickey/pigz:latest'

# Docker image to use to run R scripts
r-docker: 'rocker/tidyverse:latest'

# Docker image to use for vcflib
vcflib-docker: 'quay.io/biocontainers/vcflib:1.0.0_rc1--0'

# Docker image to use for Freebayes
freebayes-docker: 'maxulysse/freebayes:1.2.5'

##########################
### vg_index Arguments ###

# Name of index output files.  ex <name>.xg, <name>.gcsa etc. 
index-name: 'genome'

# Options to pass to vg mod for pruning phase.
# The primary path(s) will always be added back onto the pruned grpah
# Phase skipped if empty.  If list of lists, mod commands will be chained together
prune-opts: [['-D'], ['-p', '-l', '16', '-S', '-e', '4'], ['-S', '-l', '32']]

# Options to pass to vg kmers.
kmers-opts: ['-g', '-B', '-k', '16']

# Options to pass to vg gcsa indexing
gcsa-opts: ['-X', '3', '-Z', '3000']

########################
### vg_map Arguments ###

# Toggle whether reads are split into chunks
single-reads-chunk: False

# Number of reads per chunk to use when splitting up fastq.
# (only applies if single-reads-chunk is False)
# Each chunk will correspond to a vg map job
reads-per-chunk: 50000000

# Core arguments for vg mapping (do not include file names or -t/--threads)
# Note -i/--interleaved will be ignored. use the --interleaved option 
# on the toil-vg command line instead
map-opts: []

# Core arguments for vg multipath mapping (do not include file names or -t/--threads)
mpmap-opts: ['-S']

#########################
### vg_call Arguments ###
# Overlap option that is passed into make_chunks and call_chunk
overlap: 5000

# Chunk size
call-chunk-size: 2000000

# Context expansion used for graph chunking
chunk_context: 50

# Options to pass to vg filter when running vg call. (do not include file names or -t/--threads)
filter-opts: ['-r', '0.9', '-fu', '-s', '1000', '-m', '1', '-q', '15', '-D', '999']

# Options to pass to vg augment. (do not include any file names or -t/--threads or -a/--augmentation-mode)
augment-opts: ['-q', '10']

# Options to pass to vg call. (do not include file/contig/sample names or -t/--threads)
call-opts: []

# Options to pass to vg genotype. (do not include file/contig/sample names or -t/--threads)
genotype-opts: []

# Use vg genotype instead of vg call
genotype: False

#########################
### vcfeval Arguments ###
# Options to pass to rgt vcfeval. (do not include filenaems or threads or BED)
vcfeval-opts: ['--ref-overlap', '--vcf-score-field', 'QUAL']

#########################
### sim and mapeval Arguments ###
# Options to pass to vg sim (should not include -x, -n, -s or -a)
sim-opts: ['-l', '150', '-p', '570', '-v', '165', '-e', '0.01', '-i', '0.002']

# Options to pass to bwa
bwa-opts: []


""")

def generate_config(whole_genome = False):
    return whole_genome_config if whole_genome is True else default_config

def make_opts_list(x_opts):
    opts_list = filter(lambda a : len(a), x_opts.split(' '))
    # get rid of any -t or --threads while we're at it    
    for t in ['-t', '--threads']:
        if t in opts_list:
            pos = opts_list.index(t)
            del opts_list[pos:pos+2]
    return opts_list
    

def apply_config_file_args(args):
    """
    Merge args from the config file and the parser, giving priority to the parser.
    """

    # turn --*_opts from strings to lists to be consistent with config file
    for x_opts in ['map_opts', 'call_opts', 'filter_opts', 'genotype_opts', 'vcfeval_opts', 'sim_opts',
                   'bwa_opts', 'kmers_opts', 'gcsa_opts', 'mpmap_opts', 'augment_opts']:
        if x_opts in args.__dict__.keys() and type(args.__dict__[x_opts]) is str:
            args.__dict__[x_opts] = make_opts_list(args.__dict__[x_opts])

    # do the same thing for more_mpmap_opts which is a list of strings
    if 'more_mpmap_opts' in args.__dict__.keys() and args.__dict__['more_mpmap_opts']:
        for i, m_opts in enumerate(args.__dict__['more_mpmap_opts']):
            if isinstance(m_opts, basestring):
                args.__dict__['more_mpmap_opts'][i] = make_opts_list(m_opts)

    # If no config file given, we generate a default one
    wg_config = args.__dict__.has_key('whole_genome_config') and args.whole_genome_config
    if not args.__dict__.has_key('config') or args.config is None:
        config = generate_config(whole_genome = wg_config)
    else:
        if wg_config:
            raise RuntimeError('--config and --whole_genome_config cannot be used together')
        require(os.path.exists(args.config), 'Config, {}, not found. Please run '
            '"toil-vg generate-config > {}" to create.'.format(args.config, args.config))    
        with open(args.config) as conf:
            config = conf.read()
                
    # Parse config
    parsed_config = {x.replace('-', '_'): y for x, y in yaml.load(config).iteritems()}
    if 'prune_opts_2' in parsed_config:
        raise RuntimeError('prune-opts-2 from config no longer supported')
    options = argparse.Namespace(**parsed_config)

    # Add in options from the program arguments to the arguments in the config file
    #   program arguments that are also present in the config file will overwrite the
    #   arguments in the config file
    for args_key in args.__dict__:
        # Add in missing program arguments to config option list and
        # overwrite config options with corresponding options that are not None in program arguments
        if (args.__dict__[args_key]) or (args_key not in  options.__dict__.keys()):
            options.__dict__[args_key] = args.__dict__[args_key]
            
    return options

def config_subparser(parser):
    """
    Create a subparser for config.  Should pass in results of subparsers.add_parser()
    """

    parser.add_argument("--whole_genome", action="store_true",
        help="Make config tuned to process a whole genome on 32-core instances")
        
    parser.add_argument("--config", type=argparse.FileType('w'), default=sys.stdout,
        help="config file to write to")


def config_main(options):
    """ config just prints out a file """
    
    options.config.write(generate_config(options.whole_genome))
