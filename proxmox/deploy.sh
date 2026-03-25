#!/bin/bash

# Suna Proxmox Deployment Script
# This script orchestrates the complete deployment of Suna on Proxmox infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="${SCRIPT_DIR}/terraform"
ANSIBLE_DIR="${SCRIPT_DIR}/ansible"
LOG_FILE="${SCRIPT_DIR}/deployment.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Default values
DEPLOYMENT_TYPE="full"
SKIP_TERRAFORM=false
SKIP_ANSIBLE=false
DRY_RUN=false
VERBOSE=false

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        DEBUG)
            if [ "$VERBOSE" = true ]; then
                echo -e "${BLUE}[DEBUG]${NC} $message"
            fi
            ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Help function
show_help() {
    cat << EOF
Suna Proxmox Deployment Script

Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE          Deployment type (full, infrastructure, application) [default: full]
    -s, --skip-terraform     Skip Terraform infrastructure provisioning
    -a, --skip-ansible       Skip Ansible configuration
    -d, --dry-run            Perform dry run without making changes
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

Examples:
    $0                          # Full deployment
    $0 -t infrastructure       # Only provision infrastructure
    $0 -s                      # Skip Terraform, run Ansible only
    $0 -d                      # Dry run
    $0 -v                      # Verbose output

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        -s|--skip-terraform)
            SKIP_TERRAFORM=true
            shift
            ;;
        -a|--skip-ansible)
            SKIP_ANSIBLE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log ERROR "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validation
validate_environment() {
    log INFO "Validating deployment environment..."
    
    # Check required tools
    local required_tools=("terraform" "ansible-playbook" "ssh-keygen")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log ERROR "Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check Terraform configuration
    if [ ! -f "${TERRAFORM_DIR}/terraform.tfvars" ]; then
        log ERROR "Terraform configuration file not found: ${TERRAFORM_DIR}/terraform.tfvars"
        log INFO "Please copy terraform.tfvars.example and configure it for your environment"
        exit 1
    fi
    
    # Check SSH key
    if [ ! -f ~/.ssh/id_rsa ]; then
        log WARN "SSH private key not found. Generating new key pair..."
        ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
    fi
    
    log INFO "Environment validation completed"
}

# Terraform deployment
deploy_infrastructure() {
    if [ "$SKIP_TERRAFORM" = true ]; then
        log INFO "Skipping Terraform infrastructure provisioning"
        return 0
    fi
    
    log INFO "Starting Terraform infrastructure provisioning..."
    cd "$TERRAFORM_DIR"
    
    if [ "$DRY_RUN" = true ]; then
        log INFO "Performing Terraform dry run..."
        terraform plan -out=plan.tfplan
        log INFO "Terraform dry run completed"
        return 0
    fi
    
    # Initialize Terraform
    log INFO "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    log INFO "Planning Terraform deployment..."
    terraform plan -out=plan.tfplan
    
    # Apply deployment
    log INFO "Applying Terraform deployment..."
    terraform apply plan.tfplan
    
    # Get outputs for Ansible
    log INFO "Extracting Terraform outputs..."
    terraform output -json > outputs.json
    
    log INFO "Terraform infrastructure provisioning completed"
}

# Ansible deployment
deploy_application() {
    if [ "$SKIP_ANSIBLE" = true ]; then
        log INFO "Skipping Ansible configuration"
        return 0
    fi
    
    log INFO "Starting Ansible application deployment..."
    cd "$ANSIBLE_DIR"
    
    # Generate dynamic inventory from Terraform outputs
    log INFO "Generating dynamic inventory..."
    python3 -c "
import json
import yaml

# Load Terraform outputs
with open('${TERRAFORM_DIR}/outputs.json', 'r') as f:
    outputs = json.load(f)

# Generate inventory
inventory = {
    'all': {
        'children': {
            'management': {'hosts': {}},
            'application': {'hosts': {}},
            'database': {'hosts': {}},
            'storage': {'hosts': {}},
            'load_balancer': {'hosts': {}},
            'redis': {'hosts': {}},
            'monitoring': {'hosts': {}}
        }
    }
}

# Add hosts to inventory
for vm_name, vm_data in outputs['all_vms']['value'].items():
    if 'management' in vm_name:
        inventory['all']['children']['management']['hosts'][vm_data['ip_address']] = {}
    elif 'app' in vm_name:
        inventory['all']['children']['application']['hosts'][vm_data['ip_address']] = {}
    elif 'db' in vm_name:
        inventory['all']['children']['database']['hosts'][vm_data['ip_address']] = {}
    elif 'storage' in vm_name:
        inventory['all']['children']['storage']['hosts'][vm_data['ip_address']] = {}
    elif 'lb' in vm_name:
        inventory['all']['children']['load_balancer']['hosts'][vm_data['ip_address']] = {}

for container_name, container_data in outputs['all_containers']['value'].items():
    if 'redis' in container_name:
        inventory['all']['children']['redis']['hosts'][container_data['ip_address']] = {}
    elif 'monitoring' in container_name:
        inventory['all']['children']['monitoring']['hosts'][container_data['ip_address']] = {}

# Write inventory file
with open('inventory-generated.yml', 'w') as f:
    yaml.dump(inventory, f, default_flow_style=False)
"
    
    if [ "$DRY_RUN" = true ]; then
        log INFO "Performing Ansible dry run..."
        ansible-playbook -i inventory-generated.yml deploy.yml --check
        log INFO "Ansible dry run completed"
        return 0
    fi
    
    # Wait for hosts to be ready
    log INFO "Waiting for hosts to be ready..."
    ansible all -i inventory-generated.yml -m wait_for -a "host={{ inventory_hostname }} port=22 delay=10 timeout=300"
    
    # Run deployment
    log INFO "Running Ansible deployment..."
    ansible-playbook -i inventory-generated.yml deploy.yml
    
    log INFO "Ansible application deployment completed"
}

# Health check
health_check() {
    log INFO "Performing post-deployment health check..."
    
    # Check service endpoints
    local endpoints=(
        "http://localhost:3091"  # Frontend
        "http://localhost:8091"  # API
        "http://localhost:9091"  # Prometheus
        "http://localhost:3191"  # Grafana
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$endpoint" > /dev/null; then
            log INFO "Health check passed: $endpoint"
        else
            log WARN "Health check failed: $endpoint"
        fi
    done
    
    log INFO "Health check completed"
}

# Cleanup function
cleanup() {
    log INFO "Cleaning up deployment artifacts..."
    
    # Remove Terraform plan file
    if [ -f "${TERRAFORM_DIR}/plan.tfplan" ]; then
        rm "${TERRAFORM_DIR}/plan.tfplan"
    fi
    
    # Remove generated inventory
    if [ -f "${ANSIBLE_DIR}/inventory-generated.yml" ]; then
        rm "${ANSIBLE_DIR}/inventory-generated.yml"
    fi
    
    log INFO "Cleanup completed"
}

# Main deployment function
main() {
    log INFO "Starting Suna Proxmox deployment..."
    log INFO "Deployment type: $DEPLOYMENT_TYPE"
    log INFO "Dry run: $DRY_RUN"
    log INFO "Verbose: $VERBOSE"
    
    # Create backup of current state
    if [ -f "${TERRAFORM_DIR}/terraform.tfstate" ]; then
        cp "${TERRAFORM_DIR}/terraform.tfstate" "${TERRAFORM_DIR}/terraform.tfstate.backup.${TIMESTAMP}"
    fi
    
    # Validate environment
    validate_environment
    
    # Deploy based on type
    case $DEPLOYMENT_TYPE in
        "full")
            deploy_infrastructure
            deploy_application
            ;;
        "infrastructure")
            deploy_infrastructure
            ;;
        "application")
            deploy_application
            ;;
        *)
            log ERROR "Unknown deployment type: $DEPLOYMENT_TYPE"
            exit 1
            ;;
    esac
    
    # Health check
    if [ "$DEPLOYMENT_TYPE" = "full" ] || [ "$DEPLOYMENT_TYPE" = "application" ]; then
        health_check
    fi
    
    # Cleanup
    cleanup
    
    log INFO "Suna Proxmox deployment completed successfully!"
    
    # Display summary
    echo
    echo -e "${GREEN}=== Deployment Summary ===${NC}"
    echo "Type: $DEPLOYMENT_TYPE"
    echo "Timestamp: $TIMESTAMP"
    echo "Log file: $LOG_FILE"
    echo
    echo -e "${BLUE}Service Endpoints:${NC}"
    echo "Frontend: http://localhost:3091"
    echo "API: http://localhost:8091"
    echo "Prometheus: http://localhost:9091"
    echo "Grafana: http://localhost:3191"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Configure SSL certificates"
    echo "2. Set up monitoring alerts"
    echo "3. Test all functionality"
    echo "4. Review deployment logs: $LOG_FILE"
}

# Error handling
trap 'log ERROR "Deployment failed. Check logs: $LOG_FILE"; exit 1' ERR

# Run main function
main "$@"







