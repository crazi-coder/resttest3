#!/bin/bash
# pip install coverage
coverage run --source py3resttest -m pytest tests/test_*.py
coverage html
coverage report
