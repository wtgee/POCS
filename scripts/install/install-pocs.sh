#!/bin/bash -e

KEY_FILE=${1}
PANDIR=${2:-/var/panoptes}

echo "Starting fresh install at `date`" > install.log

echo "Using ${KEY_FILE}"

echo "Creating ${PANDIR}"
sudo mkdir -p ${PANDIR}/.key

sudo chown -R panoptes:panoptes ${PANDIR}
# Make sure time is correct or gcloud won't authenticate
sudo timedatectl set-ntp on

echo "Moving ${KEY_FILE} to hidden directory ${PANDIR}/.key"
mv ${KEY_FILE} ${PANDIR}/.key

echo "Updating computer..."

# Create environment variable for correct distribution
export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)"

# Add the Cloud SDK distribution URI as a package source
echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Import the Google Cloud Platform public key
wget -q -O- https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add - &>> install.log

sudo apt update &>> install.log
sudo apt install -y docker.io &>> install.log
sudo adduser panoptes docker &>> install.log

# Install miniconda and docker-compose
wget -q https://repo.continuum.io/miniconda/Miniconda3-3.7.0-Linux-x86_64.sh -O ~/miniconda.sh &>> install.log
bash ~/miniconda.sh -b -p ${PANDIR}/miniconda &>> install.log
rm ~/miniconda.sh

# Add path to user's shell
echo "export PATH="/var/panoptes/miniconda/bin:$PATH"" >> ~/.bashrc
echo "export PANDIR=/var/panoptes" >> ~/.bashrc
echo "export POCS=/var/panoptes/POCS" >> ~/.bashrc

cd $HOME
wget -q https://raw.githubusercontent.com/panoptes/POCS/40300ca08d5f12971d03c1ca58a4615f191f9471/resources/docker_files/docker-compose.yml
wget -q https://raw.githubusercontent.com/panoptes/POCS/40300ca08d5f12971d03c1ca58a4615f191f9471/resources/docker_files/env_file
wget -q https://raw.githubusercontent.com/panoptes/POCS/40300ca08d5f12971d03c1ca58a4615f191f9471/scripts/start_pocs_docker.sh
chmod +x start_pocs_docker.sh

cat <<EOT >> $HOME/Desktop/POCS.desktop
[Desktop Entry]
Exec=bash -c "cd $HOME && source activate panoptes && ./start_pocs_docker.sh"
Name=pocs
Terminal=true
Type=Application
EOT

# Add for this session
export PATH="/var/panoptes/miniconda/bin:$PATH"
#source ${PANDIR}/miniconda/bin/activate

echo "Creating new python environment for panoptes"
conda create -n panoptes --yes python=3 &>> install.log

source activate panoptes &>> install.log
conda install --yes --quiet -c conda-forge pip google-cloud-sdk &>> install.log
pip install --quiet docker-compose &>> install.log

echo "Authenticating with google"
gcloud auth activate-service-account --key-file ${PANDIR}/.key/${KEY_FILE}
gcloud auth configure-docker --quiet &>> install.log

echo "Pulling POCS files from cloud"
echo "WARNING: This is a large file that can take a long time!"
sudo docker pull gcr.io/panoptes-survey/pocs-base
sudo docker pull gcr.io/panoptes-survey/paws

echo "All done! Please reboot your system."