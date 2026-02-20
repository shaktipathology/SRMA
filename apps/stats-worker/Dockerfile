FROM python:3.11-slim

WORKDIR /app

# Install R and required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    r-base-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install R packages
RUN Rscript -e "install.packages(c('meta', 'metafor', 'jsonlite', 'ggplot2'), repos='https://cloud.r-project.org', Ncpus=4)"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "worker.main"]
