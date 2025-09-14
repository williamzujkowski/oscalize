FROM python:3.11-slim

# Multi-arch build support
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    default-jre \
    ca-certificates \
    curl \
    unzip \
    gpg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install NIST oscal-cli (from official sources)
# Pin exact version for reproducibility
ENV OSCAL_CLI_VERSION=1.0.1
RUN mkdir -p /opt/oscal-cli && cd /opt/oscal-cli && \
    curl -sSLO "https://repo1.maven.org/maven2/gov/nist/secauto/oscal/tools/oscal-cli/cli-core/${OSCAL_CLI_VERSION}/cli-core-${OSCAL_CLI_VERSION}-oscal-cli.zip" && \
    unzip "cli-core-${OSCAL_CLI_VERSION}-oscal-cli.zip" && \
    rm "cli-core-${OSCAL_CLI_VERSION}-oscal-cli.zip"

ENV PATH="/opt/oscal-cli/bin:${PATH}"

# Python dependencies (deterministic)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Install Task runner
RUN curl -sL "https://taskfile.dev/install.sh" | sh -s -- -b /usr/local/bin

# Create working directory
WORKDIR /app

# Copy application code
COPY tools/oscalize /app/tools/oscalize
COPY mappings /app/mappings
COPY schemas /app/schemas
COPY Taskfile.yml /app/

# Create directories for inputs and outputs
RUN mkdir -p inputs dist/oscal/validation tests/corpus refs

# Set up PATH for non-login shells
ENV PATH="/opt/oscal-cli/bin:/usr/local/bin:${PATH}"

# Set up entry point 
ENTRYPOINT ["bash", "-c"]
CMD ["task --list"]

# Labels for metadata
LABEL maintainer="oscalize"
LABEL description="LLM-free local OSCAL converter for FedRAMP compliance documents"
LABEL version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/your-org/oscalize"
LABEL org.opencontainers.image.documentation="https://github.com/your-org/oscalize/blob/main/README.md"
LABEL org.opencontainers.image.licenses="Apache-2.0"