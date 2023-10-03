#!/bin/bash
set -euo pipefail

docalign trg.gz ref.gz > out.txt
./diff.py 0.01 out.txt ref.txt
