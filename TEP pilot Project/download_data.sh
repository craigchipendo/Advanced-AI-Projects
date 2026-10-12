#!/usr/bin/env bash
# Downloads the Braatz Tennessee Eastman dataset (d00..d21, train and test) into data/.
# The data are distributed under the University of Illinois licence included in that
# repository; keep its LICENSE and cite the original references listed there.
set -euo pipefail
tmp=$(mktemp -d)
git clone --depth 1 https://github.com/camaramm/tennessee-eastman-profBraatz.git "$tmp/tep"
mkdir -p data
cp "$tmp"/tep/d*.dat data/
cp "$tmp"/tep/LICENSE data/LICENSE_TEP_DATA
rm -rf "$tmp"
echo "Copied $(ls data/d*.dat | wc -l) files into data/"
