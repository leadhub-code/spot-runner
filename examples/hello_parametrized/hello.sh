#!/bin/sh

export DEBIAN_FRONTEND=noninteractive

set -ex

sudo apt-get update
sudo apt-get install -y cowsay lolcat figlet

find $PWD

cat uploaded/sample_conf.yaml | cowsay -n | lolcat -f
