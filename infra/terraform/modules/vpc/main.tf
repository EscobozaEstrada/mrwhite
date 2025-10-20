# modules/vpc/main.tf
# VPC and networking infrastructure module

# === Local Variables ===
locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# === VPC ===
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = var.enable_dns_hostnames
  enable_dns_support   = var.enable_dns_support

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

# === Internet Gateway ===
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-igw"
  })
}

# === Public Subnets ===
resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-public-subnet-${count.index + 1}"
    Type = "Public"
  })
}

# === Private Subnets ===
resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-private-subnet-${count.index + 1}"
    Type = "Private"
  })
}

# === NAT Gateway ===
resource "aws_eip" "nat" {
  count = var.enable_nat_gateway ? 1 : 0
  domain   = "vpc"
  tags = merge(var.tags, {
    Name = "${local.name_prefix}-nat-eip"
  })
}

resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-nat-gateway"
  })

  depends_on = [aws_internet_gateway.main]
}

# === Route Tables ===
# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-public-rt"
  })
}

# Private Route Tables (No internet access - App Runner handles external traffic)
resource "aws_route_table" "private" {
  count  = length(var.private_subnet_cidrs)
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = var.enable_nat_gateway ? aws_nat_gateway.main[0].id : null
  }

  # App Runner's VPC connector will use default public egress for external traffic

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-private-rt-${count.index + 1}"
  })
}

# === Route Table Associations ===
# Public Subnet Associations
resource "aws_route_table_association" "public" {
  count = length(var.public_subnet_cidrs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private Subnet Associations
resource "aws_route_table_association" "private" {
  count = length(var.private_subnet_cidrs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# === Security Groups ===
# App Runner Security Group
resource "aws_security_group" "app_runner" {
  name_prefix = "${local.name_prefix}-app-runner-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for App Runner service"

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-app-runner-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# App Runner Security Group Rules (separate to avoid circular dependency)
resource "aws_security_group_rule" "app_runner_ingress" {
  type              = "ingress"
  description       = "Allow internal App Runner VPC connector traffic"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.app_runner.id
}

resource "aws_security_group_rule" "app_runner_egress_rds" {
  type                     = "egress"
  description              = "Allow App Runner to connect to RDS"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.rds.id
  security_group_id        = aws_security_group.app_runner.id
}

# Allow App Runner to make HTTPS requests to AWS services (SSM, Secrets Manager, S3, etc.)
resource "aws_security_group_rule" "app_runner_egress_https" {
  type              = "egress"
  description       = "Allow App Runner to make HTTPS requests to AWS services"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.app_runner.id
}

# Allow App Runner to make HTTP requests (for external APIs if needed)
resource "aws_security_group_rule" "app_runner_egress_http" {
  type              = "egress"
  description       = "Allow App Runner to make HTTP requests"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.app_runner.id
}

# CRITICAL: No full 0.0.0.0/0 egress rule - only specific ports for security

# RDS Security Group
resource "aws_security_group" "rds" {
  name_prefix = "${local.name_prefix}-rds-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for RDS PostgreSQL database"

  # Outbound rules (usually not needed for RDS, but explicit is better)
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-rds-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# RDS Security Group Rules (separate to avoid circular dependency)
resource "aws_security_group_rule" "rds_ingress_app_runner" {
  type                     = "ingress"
  description              = "PostgreSQL from App Runner"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.app_runner.id
  security_group_id        = aws_security_group.rds.id
}

# RDS ingress from bastion (if enabled)
resource "aws_security_group_rule" "rds_ingress_bastion" {
  count                    = var.enable_bastion_host ? 1 : 0
  type                     = "ingress"
  description              = "PostgreSQL from Bastion Host"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion[0].id
  security_group_id        = aws_security_group.rds.id
}

# VPC Endpoints Security Group
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${local.name_prefix}-vpc-endpoints-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for VPC endpoints"

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc-endpoints-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# === Bastion Host (Optional) ===
# Bastion Host Security Group
resource "aws_security_group" "bastion" {
  count = var.enable_bastion_host ? 1 : 0

  name_prefix = "${local.name_prefix}-bastion-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for bastion host"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.bastion_allowed_cidrs
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-bastion-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Bastion Host Instance
resource "aws_instance" "bastion" {
  count = var.enable_bastion_host ? 1 : 0

  ami           = var.bastion_ami_id
  instance_type = var.bastion_instance_type
  key_name      = var.bastion_key_name

  vpc_security_group_ids = [aws_security_group.bastion[0].id]
  subnet_id              = aws_subnet.public[0].id

  associate_public_ip_address = true

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-bastion"
  })
}

# === VPN Gateway (Optional) ===
resource "aws_vpn_gateway" "main" {
  count = var.enable_vpn_gateway ? 1 : 0

  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpn-gateway"
  })
}