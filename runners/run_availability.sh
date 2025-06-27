#!/bin/bash
cd /home/opc/availability
source venv/bin/activate
export FROM_INTERACTIONS=false
python3 runners/all.py 