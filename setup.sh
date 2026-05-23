#!/usr/bin/env bash
set -e

mkdir -p models tools agents nodes tests

touch models/__init__.py
touch tools/__init__.py
touch agents/__init__.py
touch nodes/__init__.py
touch tests/__init__.py

echo "Directory structure created."
