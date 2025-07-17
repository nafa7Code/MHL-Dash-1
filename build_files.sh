#!/bin/bash

# 1) تحديث pip عبر Python
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

# 2) تثبيت المتطلبات
python3 -m pip install -r requirements.txt

# 3) مايجريشنز
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput

# 4) جمع الملفات الثابتة
python3 manage.py collectstatic --noinput --clear
