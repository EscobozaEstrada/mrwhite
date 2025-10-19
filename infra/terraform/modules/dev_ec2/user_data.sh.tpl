#!/bin/bash
# User data script to bootstrap developer EC2 instance
# This script runs on first boot and configures the environment

set -e

# Update system
echo "=== Updating system packages ==="
apt-get update
apt-get upgrade -y

# Install essential development tools
echo "=== Installing development tools ==="
apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    jq \
    unzip \
    python3-pip \
    python3-venv \
    postgresql-client \
    awscli

# Install Docker
echo "=== Installing Docker ==="
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu
rm get-docker.sh

# Install Docker Compose
echo "=== Installing Docker Compose ==="
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Configure AWS CLI region
echo "=== Configuring AWS CLI ==="
mkdir -p /home/ubuntu/.aws
cat > /home/ubuntu/.aws/config <<EOF
[default]
region = ${aws_region}
output = json
EOF
chown -R ubuntu:ubuntu /home/ubuntu/.aws

# Fetch and export SSM parameters to .bashrc
echo "=== Fetching application secrets from SSM Parameter Store ==="
echo "" >> /home/ubuntu/.bashrc
echo "# Application secrets from SSM Parameter Store (loaded at login)" >> /home/ubuntu/.bashrc
echo "# Path: ${ssm_parameter_path}" >> /home/ubuntu/.bashrc

# Get all parameters from SSM and export them
aws ssm get-parameters-by-path \
    --path "${ssm_parameter_path}" \
    --with-decryption \
    --recursive \
    --region ${aws_region} \
    --output json | jq -r '.Parameters[] | "export " + (.Name | split("/") | last | ascii_upcase) + "=\"" + .Value + "\""' >> /home/ubuntu/.bashrc

echo "" >> /home/ubuntu/.bashrc
echo "# Project environment variables" >> /home/ubuntu/.bashrc
echo "export PROJECT_NAME=${project_name}" >> /home/ubuntu/.bashrc
echo "export ORGANIZATION=${organization}" >> /home/ubuntu/.bashrc
echo "export ENVIRONMENT=${environment}" >> /home/ubuntu/.bashrc
echo "export AWS_REGION=${aws_region}" >> /home/ubuntu/.bashrc
echo "export USE_SSM_CONFIG=True" >> /home/ubuntu/.bashrc

# Set ownership
chown ubuntu:ubuntu /home/ubuntu/.bashrc

# Create welcome message
cat > /etc/motd <<'EOF'
╔═══════════════════════════════════════════════════════════╗
║         Mr. White Development Environment                 ║
║         Project: Pet Health Management Application        ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  🎯 Application secrets are pre-loaded in your shell     ║
║  📦 Development tools: Docker, Python, AWS CLI, Git      ║
║  💡 Instance auto-stops after 30 min of low CPU usage    ║
║  🔒 All secrets loaded from SSM Parameter Store          ║
║                                                           ║
║  Quick Commands:                                          ║
║    - Check secrets: env | grep -E 'OPENAI|FIREBASE'      ║
║    - Clone repo: git clone <repo-url>                    ║
║    - Run backend: cd backend && python run.py            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF

# Create a helper script for refreshing secrets
cat > /usr/local/bin/refresh-secrets <<'SCRIPT'
#!/bin/bash
# Refresh secrets from SSM Parameter Store
echo "Refreshing application secrets from SSM..."
# Remove old secret exports from .bashrc
sed -i '/# Application secrets from SSM Parameter Store/,/# Project environment variables/d' /home/ubuntu/.bashrc
# Re-add secrets
echo "" >> /home/ubuntu/.bashrc
echo "# Application secrets from SSM Parameter Store (loaded at login)" >> /home/ubuntu/.bashrc
echo "# Path: ${ssm_parameter_path}" >> /home/ubuntu/.bashrc
aws ssm get-parameters-by-path \
    --path "${ssm_parameter_path}" \
    --with-decryption \
    --recursive \
    --region ${aws_region} \
    --output json | jq -r '.Parameters[] | "export " + (.Name | split("/") | last | ascii_upcase) + "=\"" + .Value + "\""' >> /home/ubuntu/.bashrc
echo "" >> /home/ubuntu/.bashrc
echo "# Project environment variables" >> /home/ubuntu/.bashrc
echo "Secrets refreshed! Run 'source ~/.bashrc' to reload."
SCRIPT
chmod +x /usr/local/bin/refresh-secrets

echo "=== Bootstrap complete! Developer workstation is ready. ==="
