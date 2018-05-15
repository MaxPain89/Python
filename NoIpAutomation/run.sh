#!/usr/bin/env bash


set -e
set -o xtrace

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

python3 ${BASEDIR}/noip_automation.py --config config.yaml
