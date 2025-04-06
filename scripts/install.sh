#!/bin/bash
# This script installs Moonraker telegram bot
set -eu

SYSTEMDDIR="/etc/systemd/system"
MENUCONFIG_SERVICE="klipper-menuconfig-builder.service"
MENUCONFIG_ENV="${HOME}/klipper-menuconfig-builder-env"
MENUCONFIG_DIR="$( cd -- "$(dirname "$0")/.." >/dev/null 2>&1 ; pwd -P )"
MENUCONFIG_LOG="${HOME}/printer_data/logs/menuconfig.log"
KLIPPER_DIR="${HOME}/klipper"
KLIPPER_LOGS_DIR="${HOME}/printer_data/logs"
CURRENT_USER=${USER}


### set color variables
green=$(echo -en "\e[92m")
yellow=$(echo -en "\e[93m")
red=$(echo -en "\e[91m")
cyan=$(echo -en "\e[96m")
default=$(echo -en "\e[39m")

# Helper functions
report_status() {
  echo -e "\n\n###### $1"
}
warn_msg(){
  echo -e "${red}<!!!!> $1${default}"
}
status_msg(){
  echo; echo -e "${yellow}###### $1${default}"
}
ok_msg(){
  echo -e "${green}>>>>>> $1${default}"
}

install_packages() {
  PKGLIST="python3-virtualenv python3-dev"

  report_status "Running apt-get update..."
  sudo apt-get update --allow-releaseinfo-change
  report_status "Installing packages..."
  for pkg in $PKGLIST; do
    echo "${cyan}$pkg${default}"
  done
  sudo apt-get install --yes ${PKGLIST}
}

create_virtualenv() {
  report_status "Installing python virtual environment..."

  if [ -d "$MENUCONFIG_ENV" ]; then
	  rm -rf "$MENUCONFIG_ENV"
  fi

  mkdir -p "${HOME}"/space
  virtualenv -p /usr/bin/python3 --system-site-packages "${MENUCONFIG_ENV}"
  export TMPDIR=${HOME}/space
  "${MENUCONFIG_ENV}"/bin/pip install --no-cache-dir -r "${MENUCONFIG_DIR}"/scripts/requirements.txt
}

create_service() {
  ### create systemd service file
  sudo /bin/sh -c "cat > ${SYSTEMDDIR}/${MENUCONFIG_SERVICE}" <<EOF
#Systemd service file for Klipper Menuconfig Builder
[Unit]
Description=Starts Klipper Menuconfig Builder on startup
After=network-online.target

[Install]
WantedBy=multi-user.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${MENUCONFIG_DIR}
ExecStart=${MENUCONFIG_ENV}/bin/python ${MENUCONFIG_DIR}/server.py -k ${KLIPPER_DIR} -l ${MENUCONFIG_LOG}
Restart=always
RestartSec=5
EOF

  ### enable instance
  sudo systemctl enable ${MENUCONFIG_SERVICE}
  report_status "${MENUCONFIG_SERVICE} instance created!"

  ### launching instance
  report_status "Launching klipper-menuconfig-builder instance ..."
  sudo systemctl restart ${MENUCONFIG_SERVICE}
}


install(){
  sudo systemctl stop klipper-menuconfig-builder || true
  status_msg "Installing dependencies"
  install_packages
  create_virtualenv
  create_service
}

install

