#!/bin/bash

python3 -m venv venv

mkdir tmp_pip
export TMPDIR=$PWD/tmp_pip
echo $TMPDIR
venv/bin/python3 -m pip install -r requirements.txt --cache-dir $TMPDIR
rm -rf $TMPDIR

