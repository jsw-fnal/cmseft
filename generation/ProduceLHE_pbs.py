import os
import sys
from argparse import ArgumentParser
from array import array
import random
import math

"""
example:
python ProduceLHE_pbs.py --tag=test --gridpack=/cms/data/jsamudio/cmseft/generation/genproductions/bin/MadGraph5_aMCatNLO/TT_madjax_5_el8_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz  --outdir=./ --neventstotal=1000 --neventsperjob=500
"""

parser = ArgumentParser()
parser.add_argument('--tag', default="LHE_production_pbs",help='A specific tag name to create log files etc.')
parser.add_argument('--gridpack', default=os.getcwd()+"/test_tarball.tar.xz",help='input tarball from the gridpack production')
parser.add_argument('--neventstotal', type=int, default=1000,help='total number of simulated LHE events')
parser.add_argument('--neventsperjob', type=int, default=100,help='number of events per pbs job')
parser.add_argument('--outdir', default=os.getcwd(),help='output directory with enough space for the LHE files and with write priviledges (example: EOS)')
args = parser.parse_args()

# check if jobflavour is valid
"""
https://batchdocs.web.cern.ch/local/submit.html
espresso     = 20 minutes
microcentury = 1 hour
longlunch    = 2 hours
workday      = 8 hours
tomorrow     = 1 day
testmatch    = 3 days
nextweek     = 1 week
"""
#if not(args.jobflavour in ["espresso","microcentury","longlunch","workday","tomorrow","testmatch","nextweek"]):
#	print("ERROR: unknown jobflavour! should be one of the following: 'espresso','microcentury','longlunch','workday','tomorrow','testmatch','nextweek'")
#	print("Exiting...")
#	sys.exit(1)


# Create directory to store the log files
if not os.path.isdir(os.getcwd()+"/pbs_log_"+(args.tag).replace(" ","_")): os.mkdir(os.getcwd()+"/pbs_log_"+(args.tag).replace(" ","_"))

# check existence of the output directory
if not os.path.isdir(os.path.abspath(args.outdir)):
	need_answer = True
	while need_answer:
		answer = raw_input("The output directory (%s) is not found, should I try to create it now (y/n)?"%os.path.abspath(args.outdir))
		if answer == "n":
			print("Exiting...")
			sys.exit(1)
		elif answer == "y":
			os.mkdir(os.path.abspath(args.outdir))
			if not os.path.isdir(os.path.abspath(args.outdir)):
				print("creating directory failed (do you have proper acces rights?)")
				print("Exiting...")
				sys.exit(1)
			need_answer = False
		else:
			print("please type either 'y' or 'n'")


# create a text file with the production paramters
njobs = int(math.ceil(float(args.neventstotal)/float(args.neventsperjob)))
print("preparing %i jobs"%njobs)
initial_seed = int(random.uniform(1,1000))
remaining_events = args.neventstotal
f_tmp_ = open(os.getcwd()+"/params_pbs.txt", 'w')
for i in  range(njobs):
	seed = initial_seed + 2*i*args.neventsperjob + int(random.uniform(1,args.neventsperjob))
	nevents = args.neventsperjob
	if remaining_events < args.neventsperjob:nevents = remaining_events
	f_tmp_.write("%i, %i, %i \n"%(i+1, seed, nevents))
	remaining_events -= args.neventsperjob
f_tmp_.close()


# create a submission batch script that untars the tarball
f_tmp_btach_ = open(os.getcwd()+"/LHEproduction_%s.pbs"%((args.tag).replace(" ","_")), 'w')
f_tmp_btach_.write("#!/bin/bash \n")
f_tmp_btach_.write("#PBS -l nodes=1:ppn=2 \n")
#f_tmp_btach_.write("#PBS -m ea \n")
#f_tmp_btach_.write("#PBS -M jonathan_samudio1@baylor.edu \n")
f_tmp_btach_.write("#PBS -e pbs_log_%s/job.err \n"%((args.tag).replace(" ","_")))
f_tmp_btach_.write("#PBS -o pbs_log_%s/job.out \n"%((args.tag).replace(" ","_")))
#f_tmp_btach_.write("JOB_NUM=$1\n")
#f_tmp_btach_.write("NEVENTS=$2\n")
#f_tmp_btach_.write("RND=$3\n")
f_tmp_btach_.write('JOB_DIR_NAME="job_${JOB_NUM}"\n')
f_tmp_btach_.write("cd $PBS_O_WORKDIR \n")
f_tmp_btach_.write("pwd \n")
f_tmp_btach_.write(". setup.sh \n")
f_tmp_btach_.write("mkdir -p ${JOB_DIR_NAME}_%s \n"%((args.tag).replace(" ","_")))
f_tmp_btach_.write("cd ${JOB_DIR_NAME}_%s \n"%((args.tag).replace(" ","_")))
f_tmp_btach_.write("pwd \n")
f_tmp_btach_.write('echo "running:cmsRun ../nanogen_matching.py %s ${NEVENTS} ${RND}" \n'%(args.gridpack))
f_tmp_btach_.write("cmsRun ../nanogen_matching.py %s ${NEVENTS} ${RND} &> log.log\n"%(args.gridpack))
f_tmp_btach_.close()

# create pbs submission file
f_tmp_pbs_ = open(os.getcwd()+"/ProduceLHE_pbs_%s.sh"%((args.tag).replace(" ","_")), 'w')
f_tmp_pbs_.write("#!/bin/bash \n")
f_tmp_pbs_.write('PBS_SCRIPT="LHEproduction_%s.pbs" \n'%((args.tag).replace(" ","_")))
f_tmp_pbs_.write('PARAM_FILE="params_pbs.txt"\n')
f_tmp_pbs_.write("while IFS=',' read -r job_num rnd nevents; do\n")
f_tmp_pbs_.write('  job_num=$(echo "$job_num" | xargs)\n')
f_tmp_pbs_.write('  nevents=$(echo "$nevents" | xargs)\n')
f_tmp_pbs_.write('  rnd=$(echo "$rnd" | xargs)\n')
f_tmp_pbs_.write('  if [[ -n "$job_num" ]]; then\n')
f_tmp_pbs_.write('      echo "Submitting job ${job_num} with nevents=${nevents} and rnd=${rnd}"\n')
f_tmp_pbs_.write('      echo "qsub -v JOB_NUM=${job_num},NEVENTS=${nevents},RND=${rnd} ${PBS_SCRIPT}"\n')
f_tmp_pbs_.write('      qsub -v JOB_NUM=${job_num},NEVENTS=${nevents},RND=${rnd} ${PBS_SCRIPT}\n')
f_tmp_pbs_.write("  fi\n")
f_tmp_pbs_.write('done < "${PARAM_FILE}"\n')
f_tmp_pbs_.write('echo "All jobs submitted."\n')

print("The jobs can now be submitted via pbs with 'bash ProduceLHE_pbs_%s.sh'"%((args.tag).replace(" ","_")))
print("The status can then be checked using 'qstat -u $USER'")
