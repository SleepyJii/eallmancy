#!/bin/bash

npm run build --prefix frontend/ && /root/eallmancy/venv/bin/python -m uvicorn server:app --port=9855

