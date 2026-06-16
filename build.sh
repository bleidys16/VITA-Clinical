#!/bin/bash
set -o errexit

pip install --upgrade pip
pip install -r backend/requirements.txt

python backend/manage.py migrate --noinput
python backend/manage.py collectstatic --noinput
python backend/manage.py crear_usuarios_base
