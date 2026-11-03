# Sử dụng base image Python 3.11 bản slim để tối ưu kích thước
FROM python:3.11-slim

# Ngăn Python tạo file .pyc và bật unbuffered log
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    OMP_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    MKL_NUM_THREADS=2

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt các gói phụ thuộc hệ thống cần thiết cho dlib, OpenCV và C++ build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements trước để tận dụng Docker layer caching
COPY requirements.txt .

# Nâng cấp pip và cài đặt dependencies Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn ứng dụng vào container
COPY . .

# Tạo sẵn thư mục lưu trữ dữ liệu nếu chưa tồn tại
RUN mkdir -p data/faces models db

# Mở cổng mặc định của Streamlit
EXPOSE 8501

# Thiết lập Healthcheck kiểm tra trạng thái hoạt động của Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Lệnh khởi chạy ứng dụng Streamlit (tắt browser tự mở và lắng nghe trên 0.0.0.0)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]