#!/bin/bash
# pip install coverage
coverage run --source resttest3 -m pytest tests/test_*.py
coverage html
coverage report
