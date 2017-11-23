#!/bin/sh

DEBIAN_FRONTEND=noninteractive

set -ex

sudo apt-get update
sudo apt-get install -y cowsay lolcat figlet

figlet 'Hello!' | cowsay -n | lolcat -f
