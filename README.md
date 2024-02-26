# Klipper Firmware Configurator (and builder)

## What is that?

This is stupid simple web frontend for `make menuconfig` allowing you to build and download firmware file using web browser. That's it.

## How to install?

```
cd ~
git clone https://github.com/CODeRUS/klipper_web_builder.git
cd ~/klipper_web_builder
scripts/install.sh
```

## How to use?

Open `host_ip:7055` in your browser, or check below how to setup nginx to access via `host_ip/menuconfig` endpoint

## How to uninstall?

```
cd ~/klipper_web_builder
scripts/uninstall.sh
```

## Can i setup nginx?

Check example: https://github.com/CODeRUS/klipper_web_builder/blob/master/scripts/nginx.example

## Demo 

![animation](https://coderus.openrepos.net/static/KFCB.gif)

## Credits

Using [Kconfiglib](https://github.com/ulfalizer/Kconfiglib) Python library by [ulfalizer](https://github.com/ulfalizer)
