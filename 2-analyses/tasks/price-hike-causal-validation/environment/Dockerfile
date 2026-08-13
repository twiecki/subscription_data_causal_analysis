FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    git \
    vim \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Pinned analysis stack (g++ above: pytensor needs a C++ compiler for pymc)
RUN pip install --no-cache-dir \
    pandas==3.0.2 \
    numpy==2.3.5 \
    scikit-learn==1.8.0 \
    scipy==1.17.1 \
    statsmodels==0.14.6 \
    pymc==5.28.5 \
    causalpy==0.8.1

RUN mkdir -p /app   # BenchFlow injects skills into /app/skills at runtime
WORKDIR /root

COPY daily_aggregates_intervention.csv /root/
COPY metric-contract.yml /root/
