#!/usr/bin/env bash
# Compatibility shim for older commands. The project default is Isaac Lab 3
# Newton; this file intentionally no longer installs Isaac Sim 5.1 or Isaac
# Lab 2.x.
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
exec "${SCRIPT_DIR}/setup_isaaclab3_newton.sh" "$@"
