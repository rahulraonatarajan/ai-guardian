FROM python:3.12-alpine
COPY src/guard_fix.py /guard_fix.py
ENTRYPOINT ["python", "/guard_fix.py"]
