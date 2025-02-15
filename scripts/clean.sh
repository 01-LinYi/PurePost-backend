#!/bin/bash

# Remove all .pyc files and __pycache__ directories
# Remove all files in media/uploads directory
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
rm -rf media/uploads/*