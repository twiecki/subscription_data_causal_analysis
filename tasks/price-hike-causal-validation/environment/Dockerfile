FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Pinned analysis stack
RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    numpy==1.26.4 \
    scikit-learn==1.5.2 \
    scipy==1.14.1 \
    statsmodels==0.14.4

RUN mkdir -p /app   # BenchFlow injects skills into /app/skills at runtime
WORKDIR /root

COPY daily_aggregates_intervention.csv /root/
COPY metric-contract.yml /root/
