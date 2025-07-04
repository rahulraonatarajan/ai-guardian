FROM python:3.11-slim

COPY guard_fix.py /guard_fix.py

ENTRYPOINT ["python3", "/guard_fix.py"]
