#!/bin/bash
.venv/bin/python main.py update-opportunity-scores --fetch-homepage --only-missing --concurrency 3 --model "meta/llama-3.1-8b-instruct" >> scoring_final.log 2>&1
