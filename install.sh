#!/usr/bin/env bash

set -euo pipefail

readonly REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pip3 install -r "${REPO}/requirements.txt"
