# Dockerfile cho Hugging Face Spaces (SDK: docker).
# Space chi can 2 tep: README.md (khai bao cau hinh) + Dockerfile nay.
# Ma nguon duoc lay tu GitHub cong khai khi build; KHONG kem du lieu that.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git libopenblas-dev liblapack-dev libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Spaces chay container voi user id 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=2 \
    SMART_ATTENDANCE_DATA_ROOT=/home/user/data \
    SMART_ATTENDANCE_RESEARCH_LOG=1

WORKDIR /home/user/app
ARG REPO=https://github.com/trunggdeptrai/smart-attendance.git
ARG REF=main
RUN git clone --depth 1 --branch ${REF} ${REPO} .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /home/user/data/data/faces /home/user/data/models

EXPOSE 7860
CMD ["python", "-m", "streamlit", "run", "app.py", \
     "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true", \
     "--server.enableXsrfProtection=false", "--server.enableCORS=false", \
     "--browser.gatherUsageStats=false"]
