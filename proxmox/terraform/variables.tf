# Proxmox Provider Variables
variable "proxmox_api_url" {
  description = "Proxmox API URL"
  type        = string
  default     = "https://192.168.1.100:8006/api2/json"
}

variable "proxmox_api_token_id" {
  description = "Proxmox API token ID"
  type        = string
  sensitive   = true
}

variable "proxmox_api_token_secret" {
  description = "Proxmox API token secret"
  type        = string
  sensitive   = true
}

variable "proxmox_tls_insecure" {
  description = "Skip TLS verification for Proxmox API"
  type        = bool
  default     = true
}

variable "proxmox_debug" {
  description = "Enable debug mode for Proxmox provider"
  type        = bool
  default     = false
}

variable "proxmox_node" {
  description = "Proxmox node to deploy VMs on"
  type        = string
  default     = "pve"
}

# Cluster Configuration
variable "cluster_name" {
  description = "Name of the Suna cluster"
  type        = string
  default     = "suna"
}

variable "template_name" {
  description = "Name of the VM template to clone from"
  type        = string
  default     = "ubuntu-22.04-template"
}

variable "lxc_template" {
  description = "Name of the LXC template to use"
  type        = string
  default     = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.gz"
}

variable "storage_pool" {
  description = "Storage pool for VM disks"
  type        = string
  default     = "local-lvm"
}

variable "network_bridge" {
  description = "Network bridge for VMs"
  type        = string
  default     = "vmbr0"
}

variable "network_cidr" {
  description = "Network CIDR for VM IPs"
  type        = string
  default     = "24"
}

variable "network_gateway" {
  description = "Network gateway"
  type        = string
  default     = "192.168.1.1"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
  sensitive   = true
}

variable "lxc_password" {
  description = "Password for LXC containers"
  type        = string
  sensitive   = true
}

# Network IP Ranges (XX91 port scheme compatible)
variable "management_network_start_ip" {
  description = "Starting IP for management nodes"
  type        = string
  default     = "192.168.1.10"
}

variable "application_network_start_ip" {
  description = "Starting IP for application nodes"
  type        = string
  default     = "192.168.1.20"
}

variable "database_network_start_ip" {
  description = "Starting IP for database nodes"
  type        = string
  default     = "192.168.1.30"
}

variable "storage_network_start_ip" {
  description = "Starting IP for storage nodes"
  type        = string
  default     = "192.168.1.40"
}

variable "load_balancer_network_start_ip" {
  description = "Starting IP for load balancer nodes"
  type        = string
  default     = "192.168.1.50"
}

variable "redis_network_start_ip" {
  description = "Starting IP for Redis containers"
  type        = string
  default     = "192.168.1.60"
}

variable "monitoring_network_start_ip" {
  description = "Starting IP for monitoring containers"
  type        = string
  default     = "192.168.1.70"
}

# Node Counts
variable "management_node_count" {
  description = "Number of management nodes"
  type        = number
  default     = 1
}

variable "application_node_count" {
  description = "Number of application nodes"
  type        = number
  default     = 2
}

variable "database_node_count" {
  description = "Number of database nodes"
  type        = number
  default     = 1
}

variable "storage_node_count" {
  description = "Number of storage nodes"
  type        = number
  default     = 1
}

variable "load_balancer_count" {
  description = "Number of load balancer nodes"
  type        = number
  default     = 1
}

variable "redis_container_count" {
  description = "Number of Redis containers"
  type        = number
  default     = 1
}

variable "monitoring_container_count" {
  description = "Number of monitoring containers"
  type        = number
  default     = 1
}

# Management Node Configuration
variable "management_vm_cores" {
  description = "Number of CPU cores for management VMs"
  type        = number
  default     = 2
}

variable "management_vm_memory" {
  description = "Memory allocation for management VMs (MB)"
  type        = number
  default     = 4096
}

variable "management_vm_disk_size" {
  description = "Disk size for management VMs"
  type        = string
  default     = "50G"
}

# Application Node Configuration
variable "application_vm_cores" {
  description = "Number of CPU cores for application VMs"
  type        = number
  default     = 4
}

variable "application_vm_memory" {
  description = "Memory allocation for application VMs (MB)"
  type        = number
  default     = 8192
}

variable "application_vm_disk_size" {
  description = "Disk size for application VMs"
  type        = string
  default     = "100G"
}

# Database Node Configuration
variable "database_vm_cores" {
  description = "Number of CPU cores for database VMs"
  type        = number
  default     = 4
}

variable "database_vm_memory" {
  description = "Memory allocation for database VMs (MB)"
  type        = number
  default     = 8192
}

variable "database_vm_disk_size" {
  description = "System disk size for database VMs"
  type        = string
  default     = "50G"
}

variable "database_storage_disk_size" {
  description = "Database storage disk size"
  type        = string
  default     = "200G"
}

# Storage Node Configuration
variable "storage_vm_cores" {
  description = "Number of CPU cores for storage VMs"
  type        = number
  default     = 2
}

variable "storage_vm_memory" {
  description = "Memory allocation for storage VMs (MB)"
  type        = number
  default     = 4096
}

variable "storage_vm_disk_size" {
  description = "System disk size for storage VMs"
  type        = string
  default     = "50G"
}

variable "file_storage_disk_size" {
  description = "File storage disk size"
  type        = string
  default     = "500G"
}

variable "backup_storage_disk_size" {
  description = "Backup storage disk size"
  type        = string
  default     = "1T"
}

# Load Balancer Configuration
variable "load_balancer_vm_cores" {
  description = "Number of CPU cores for load balancer VMs"
  type        = number
  default     = 2
}

variable "load_balancer_vm_memory" {
  description = "Memory allocation for load balancer VMs (MB)"
  type        = number
  default     = 2048
}

variable "load_balancer_vm_disk_size" {
  description = "Disk size for load balancer VMs"
  type        = string
  default     = "20G"
}

# Redis Container Configuration
variable "redis_cores" {
  description = "Number of CPU cores for Redis containers"
  type        = number
  default     = 1
}

variable "redis_memory" {
  description = "Memory allocation for Redis containers (MB)"
  type        = number
  default     = 1024
}

variable "redis_swap" {
  description = "Swap allocation for Redis containers (MB)"
  type        = number
  default     = 512
}

variable "redis_disk_size" {
  description = "Disk size for Redis containers"
  type        = string
  default     = "20G"
}

# Monitoring Container Configuration
variable "monitoring_cores" {
  description = "Number of CPU cores for monitoring containers"
  type        = number
  default     = 2
}

variable "monitoring_memory" {
  description = "Memory allocation for monitoring containers (MB)"
  type        = number
  default     = 2048
}

variable "monitoring_swap" {
  description = "Swap allocation for monitoring containers (MB)"
  type        = number
  default     = 1024
}

variable "monitoring_disk_size" {
  description = "Disk size for monitoring containers"
  type        = string
  default     = "50G"
}

# Port Configuration (XX91 scheme)
variable "suna_ports" {
  description = "Port configuration for Suna services"
  type        = map(number)
  default = {
    # Frontend
    frontend_http  = 3091
    frontend_https = 3092
    
    # Backend API
    api_http  = 8091
    api_https = 8092
    
    # Database
    postgres = 5491
    
    # Redis
    redis = 6391
    
    # Load Balancer
    lb_http  = 8091
    lb_https = 8092
    
    # Monitoring
    prometheus = 9091
    grafana    = 3191
    alertmanager = 9191
    
    # Local Services
    ollama = 11491
    mailhog = 1091
    
    # WebSocket
    websocket = 8091
  }
}

# Validation Rules
variable "validate_network_range" {
  description = "Validate network IP ranges"
  type        = bool
  default     = true
}

variable "validate_disk_sizes" {
  description = "Validate disk size formats"
  type        = bool
  default     = true
}

variable "validate_memory_allocation" {
  description = "Validate memory allocation"
  type        = bool
  default     = true
}







