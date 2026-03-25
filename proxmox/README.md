# Suna Proxmox Deployment Automation

This directory contains Terraform and Ansible automation for deploying Suna on Proxmox VE infrastructure.

## Overview

The Proxmox deployment automation provides:
- **VM/LXC Provisioning**: Automated creation of virtual machines and containers
- **Multi-VM Setup**: Distributed deployment across multiple nodes
- **Service Discovery**: Automatic service registration and load balancing
- **Monitoring Integration**: Prometheus/Grafana setup for infrastructure monitoring
- **Backup & Recovery**: Automated backup procedures and disaster recovery
- **Scaling**: Horizontal and vertical scaling capabilities

## Architecture

```
Proxmox Cluster
├── Management Node (VM)
│   ├── Terraform/Ansible Control
│   ├── Monitoring (Prometheus/Grafana)
│   └── Backup Management
├── Application Node 1 (VM)
│   ├── Suna Frontend (Next.js)
│   ├── Suna Backend (FastAPI)
│   └── Database (PostgreSQL)
├── Application Node 2 (VM)
│   ├── Load Balancer (Nginx)
│   ├── Cache (Redis)
│   └── Queue Workers (Dramatiq)
└── Storage Node (VM)
    ├── File Storage
    ├── Backup Storage
    └── Monitoring Data
```

## Prerequisites

- Proxmox VE 8.0+ cluster
- Terraform 1.5+
- Ansible 8.0+
- SSH access to Proxmox nodes
- API token or user credentials for Proxmox

## Quick Start

1. **Configure Proxmox credentials**:
   ```bash
   export PROXMOX_API_TOKEN_ID="your-token-id"
   export PROXMOX_API_TOKEN_SECRET="your-token-secret"
   export PROXMOX_HOST="your-proxmox-host"
   ```

2. **Initialize Terraform**:
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

3. **Run Ansible deployment**:
   ```bash
   cd ansible
   ansible-playbook -i inventory.yml deploy.yml
   ```

## Components

### Terraform Configuration

- **`main.tf`**: Main infrastructure configuration
- **`variables.tf`**: Input variables and validation
- **`outputs.tf`**: Output values for Ansible integration
- **`providers.tf`**: Provider configuration
- **`networks.tf`**: Network and firewall configuration
- **`storage.tf`**: Storage pool and volume configuration

### Ansible Playbooks

- **`deploy.yml`**: Main deployment playbook
- **`monitoring.yml`**: Monitoring stack deployment
- **`backup.yml`**: Backup and recovery procedures
- **`scale.yml`**: Scaling operations

### Configuration Files

- **`inventory.yml`**: Dynamic inventory for Ansible
- **`group_vars/`**: Group-specific variables
- **`host_vars/`**: Host-specific variables
- **`roles/`**: Reusable Ansible roles

## Configuration

### Environment Variables

```bash
# Proxmox Configuration
PROXMOX_HOST=192.168.1.100
PROXMOX_API_TOKEN_ID=terraform-provider@pve!terraform-token
PROXMOX_API_TOKEN_SECRET=your-secret-here

# Network Configuration
PROXMOX_NETWORK_CIDR=192.168.1.0/24
PROXMOX_GATEWAY=192.168.1.1
PROXMOX_DNS=8.8.8.8,8.8.4.4

# VM Configuration
Suna_VM_COUNT=3
Suna_VM_MEMORY=4096
Suna_VM_CORES=2
Suna_VM_DISK_SIZE=50
```

### Terraform Variables

```hcl
variable "proxmox_host" {
  description = "Proxmox host address"
  type        = string
}

variable "vm_count" {
  description = "Number of VMs to create"
  type        = number
  default     = 3
}

variable "vm_memory" {
  description = "Memory allocation per VM (MB)"
  type        = number
  default     = 4096
}
```

## Usage

### Deploy New Environment

```bash
# 1. Configure environment
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your configuration

# 2. Deploy infrastructure
cd terraform
terraform init
terraform plan
terraform apply

# 3. Deploy applications
cd ../ansible
ansible-playbook -i inventory.yml deploy.yml
```

### Scale Environment

```bash
# Scale horizontally
cd terraform
terraform apply -var="vm_count=5"

# Scale vertically
terraform apply -var="vm_memory=8192"
```

### Backup and Recovery

```bash
# Create backup
cd ansible
ansible-playbook -i inventory.yml backup.yml

# Restore from backup
ansible-playbook -i inventory.yml restore.yml -e "backup_file=backup-2024-01-01.tar.gz"
```

## Monitoring

### Infrastructure Monitoring

- **Prometheus**: Metrics collection from all VMs
- **Grafana**: Dashboards for infrastructure and application metrics
- **Alertmanager**: Alert routing and notification

### Application Monitoring

- **Health Checks**: Automated health check endpoints
- **Log Aggregation**: Centralized logging with structured logs
- **Performance Metrics**: Response times, throughput, error rates

## Security

### Network Security

- **Firewall Rules**: Restrict access to necessary ports only
- **VPN Access**: Secure remote access to management interfaces
- **SSL/TLS**: Encrypted communication for all services

### Access Control

- **SSH Key Management**: Key-based authentication for all VMs
- **API Token Security**: Secure Proxmox API token management
- **User Permissions**: Principle of least privilege

## Troubleshooting

### Common Issues

1. **Terraform State Issues**:
   ```bash
   terraform refresh
   terraform plan
   ```

2. **Ansible Connection Issues**:
   ```bash
   ansible all -m ping -i inventory.yml
   ```

3. **VM Boot Issues**:
   ```bash
   # Check VM status
   qm status <vm-id>
   
   # View VM console
   qm terminal <vm-id>
   ```

### Logs and Debugging

- **Terraform Logs**: `terraform.log`
- **Ansible Logs**: `ansible.log`
- **VM Logs**: `/var/log/qemu-server/`

## Maintenance

### Regular Tasks

- **Backup Verification**: Weekly backup restore tests
- **Security Updates**: Monthly security patch application
- **Performance Monitoring**: Continuous performance tracking
- **Capacity Planning**: Resource usage analysis and planning

### Disaster Recovery

1. **Backup Restoration**: Automated backup restoration procedures
2. **Infrastructure Recovery**: Complete infrastructure rebuild from Terraform
3. **Data Recovery**: Database and file storage recovery procedures

## Support

For issues and questions:
- Check the troubleshooting section
- Review logs and error messages
- Consult the main Suna documentation
- Open an issue in the project repository







