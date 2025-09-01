#!/bin/bash
# Validación rápida de red de seguridad
cd "$(dirname "$0")/.."
source venv/bin/activate
export PYTHONPATH="$(pwd)"
python tests/validate_safety_net.py
