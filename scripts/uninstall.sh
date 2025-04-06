#!/bin/bash
# This script installs Moonraker telegram bot
set -eu

SYSTEMDDIR="/etc/systemd/system"
MENUCONFIG_ENV="${HOME}/klipper-menuconfig-builder-env"
MENUCONFIG_SERVICE="klipper-menuconfig-builder.service"

remove_all(){
  echo -e "Removing $MENUCONFIG_SERVICE ..."
  sudo systemctl stop $MENUCONFIG_SERVICE
  sudo systemctl disable $MENUCONFIG_SERVICE
  sudo rm -f $SYSTEMDDIR/$MENUCONFIG_SERVICE
  echo -e "Done!"

  rm -rf "${HOME}/klipper_logs/menuconfig*"


  sudo systemctl daemon-reload
  sudo systemctl reset-failed

  if [ -d $MENUCONFIG_ENV ]; then
    echo -e "Removing venv directory ..."
    rm -rf "${MENUCONFIG_ENV}" && echo -e "Directory removed!"
  fi

}

remove_all
