FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.12

# Set environment variables to fix caching issues
ENV NUMBA_CACHE_DIR=/tmp
ENV NUMBA_DISABLE_JIT=1
ENV HOME=/tmp
ENV XDG_CACHE_HOME=/tmp/.cache
ENV TRANSFORMERS_CACHE=/tmp/.cache/transformers
ENV HF_HOME=/tmp/.cache/huggingface

# Install system dependencies and create cache directories
RUN microdnf update -y && \
    microdnf install -y gcc gcc-c++ make && \
    microdnf clean all && \
    mkdir -p /tmp/.cache/transformers /tmp/.cache/huggingface

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY . ${LAMBDA_TASK_ROOT}

CMD ["process.lambda_handler"]