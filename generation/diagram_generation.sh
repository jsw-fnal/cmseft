#!/bin/bash -x

#First you need to set couple of settings:
name=${1}
# name of the run
carddir=${2}

if [ -z "$PRODHOME" ]; then
  PRODHOME=`pwd`
fi

CARDSDIR=${PRODHOME}/${carddir}


WORKDIR=$PRODHOME/diagrams_tmp_${name}
if [ -d $WORKDIR ]; then
    rm -rf $WORKDIR
fi

mkdir -p $WORKDIR
cd $WORKDIR

# Folder structure is different on CMSConnect
helpers_dir=${PRODHOME}/Utilities
if [ ! -d "$helpers_dir" ]; then
    helpers_dir=$(git rev-parse --show-toplevel)/Utilities
fi
source ${helpers_dir}/gridpack_helpers.sh

if [ ! -z ${CMSSW_BASE} ]; then
  echo "Error: This script must be run in a clean environment as it sets up CMSSW itself.  You already have a CMSSW environment set up for ${CMSSW_VERSION}."
  echo "Please try again from a clean shell."
  if [ "${BASH_SOURCE[0]}" != "${0}" ]; then return 1; else exit 1; fi
fi

#catch unset variables
set -u

if [ -z ${name} ]; then
  echo "Process/card name not provided"
  if [ "${BASH_SOURCE[0]}" != "${0}" ]; then return 1; else exit 1; fi
fi

MG_EXT=".tar.gz"
MG=MG5_aMC_v2.9.18$MG_EXT
MGSOURCE=https://cms-project-generators.web.cern.ch/cms-project-generators/$MG
MGBASEDIRORIG=$(echo ${MG%$MG_EXT} | tr "." "_")
wget --no-check-certificate ${MGSOURCE}
tar xzf ${MG}
rm "$MG"

cd $WORKDIR

# careful: if you change the model path here, you have to change it in submit_cmsconnect_gridpack_generation(_singlejob).sh as well (model_directory)
cp -rp ${PRODHOME}/addons/models/* ${MGBASEDIRORIG}/models/

if [ -e $CARDSDIR/${name}_restrict_custom.dat ]; then
  cp $CARDSDIR/${name}_restrict_custom.dat restrict_custom.dat
  for MDDIR in ${MGBASEDIRORIG}/models/*/
  do
      echo $CARDSDIR/${name}_restrict_custom.dat $MDDIR/restrict_custom.dat 
      cp $CARDSDIR/${name}_restrict_custom.dat $MDDIR/restrict_custom.dat
  done
fi

cp $CARDSDIR/${name}_proc_card.dat ${name}_proc_card.dat
echo "display diagrams ./" >> ${name}_proc_card.dat
echo "display diagrams_text ./" >> ${name}_proc_card.dat

pushd $MGBASEDIRORIG

cat $PRODHOME/patches/*.patch | patch -p1
cp -r $PRODHOME/PLUGIN/CMS_CLUSTER/ PLUGIN/ 

echo "set auto_update 0" > mgconfigscript
echo "set automatic_html_opening False" >> mgconfigscript
echo "set auto_convert_model True" >> mgconfigscript
echo "set run_mode 2" >> mgconfigscript
echo "save options --all" >> mgconfigscript

./bin/mg5_aMC mgconfigscript

#load extra models if needed
if [ -e $CARDSDIR/${name}_extramodels.dat ]; then
	echo "Loading extra models specified in $CARDSDIR/${name}_extramodels.dat"
	#strip comments
	sed 's:#.*$::g' $CARDSDIR/${name}_extramodels.dat | while read -r model || [ -n "$model" ]
do
	#get needed BSM model
	if [[ $model = *[!\ ]* ]]; then
		echo "Loading extra model $model"
		wget --no-check-certificate https://cms-project-generators.web.cern.ch/cms-project-generators/$model	
		pushd models
		if [[ $model == *".zip"* ]]; then
			unzip ../$model
		elif [[ $model == *".tgz"* ]]; then
			tar zxvf ../$model
		elif [[ $model == *".tar"* ]]; then
			tar xavf ../$model
		else 
			echo "A BSM model is specified but it is not in a standard archive (.zip or .tar)"
		fi
		popd
	fi
done
fi

ls
pwd

if ls $CARDSDIR/${name}*.patch; then
	echo "    WARNING: Applying custom user patch. I hope you know what you're doing!"
	cat $CARDSDIR/${name}*.patch | patch -p 1 -f
fi

popd

${MGBASEDIRORIG}/bin/mg5_aMC ${name}_proc_card.dat

# remove all the zero coefficients
#sed -e "s/NP\w*=0, //g" -e "s/, SMHLOOP=0//" -e "s/NP=1, //" -i *.eps

PDFOUT="../${name}_diagrams"
mkdir -p $PDFOUT
for epsfile in *.eps 
do
    ps2pdf $epsfile $PDFOUT/${epsfile%.*}.pdf
done

cd $PRODHOME/
#rm -rf $WORKDIR
