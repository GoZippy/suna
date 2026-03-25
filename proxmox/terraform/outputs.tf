# Management Node Outputs
output "management_nodes" {
  description = "Management node details"
  value = {
    for idx, vm in proxmox_vm_qemu.management_node : vm.name => {
      id          = vm.vmid
      ip_address  = vm.default_ipv4_address
      name        = vm.name
      cores       = vm.cores
      memory      = vm.memory
      status      = vm.status
      tags        = vm.tags
    }
  }
}

output "management_node_ips" {
  description = "IP addresses of management nodes"
  value = [
    for vm in proxmox_vm_qemu.management_node : vm.default_ipv4_address
  ]
}

# Application Node Outputs
output "application_nodes" {
  description = "Application node details"
  value = {
    for idx, vm in proxmox_vm_qemu.application_nodes : vm.name => {
      id          = vm.vmid
      ip_address  = vm.default_ipv4_address
      name        = vm.name
      cores       = vm.cores
      memory      = vm.memory
      status      = vm.status
      tags        = vm.tags
    }
  }
}

output "application_node_ips" {
  description = "IP addresses of application nodes"
  value = [
    for vm in proxmox_vm_qemu.application_nodes : vm.default_ipv4_address
  ]
}

# Database Node Outputs
output "database_nodes" {
  description = "Database node details"
  value = {
    for idx, vm in proxmox_vm_qemu.database_node : vm.name => {
      id          = vm.vmid
      ip_address  = vm.default_ipv4_address
      name        = vm.name
      cores       = vm.cores
      memory      = vm.memory
      status      = vm.status
      tags        = vm.tags
    }
  }
}

output "database_node_ips" {
  description = "IP addresses of database nodes"
  value = [
    for vm in proxmox_vm_qemu.database_node : vm.default_ipv4_address
  ]
}

# Storage Node Outputs
output "storage_nodes" {
  description = "Storage node details"
  value = {
    for idx, vm in proxmox_vm_qemu.storage_node : vm.name => {
      id          = vm.vmid
      ip_address  = vm.default_ipv4_address
      name        = vm.name
      cores       = vm.cores
      memory      = vm.memory
      status      = vm.status
      tags        = vm.tags
    }
  }
}

output "storage_node_ips" {
  description = "IP addresses of storage nodes"
  value = [
    for vm in proxmox_vm_qemu.storage_node : vm.default_ipv4_address
  ]
}

# Load Balancer Outputs
output "load_balancers" {
  description = "Load balancer details"
  value = {
    for idx, vm in proxmox_vm_qemu.load_balancer : vm.name => {
      id          = vm.vmid
      ip_address  = vm.default_ipv4_address
      name        = vm.name
      cores       = vm.cores
      memory      = vm.memory
      status      = vm.status
      tags        = vm.tags
    }
  }
}

output "load_balancer_ips" {
  description = "IP addresses of load balancer nodes"
  value = [
    for vm in proxmox_vm_qemu.load_balancer : vm.default_ipv4_address
  ]
}

# Redis Container Outputs
output "redis_containers" {
  description = "Redis container details"
  value = {
    for idx, container in proxmox_lxc.redis : container.hostname => {
      id          = container.vmid
      ip_address  = container.network[0].ip
      hostname    = container.hostname
      cores       = container.cores
      memory      = container.memory
      status      = container.status
      tags        = container.tags
    }
  }
}

output "redis_container_ips" {
  description = "IP addresses of Redis containers"
  value = [
    for container in proxmox_lxc.redis : container.network[0].ip
  ]
}

# Monitoring Container Outputs
output "monitoring_containers" {
  description = "Monitoring container details"
  value = {
    for idx, container in proxmox_lxc.monitoring : container.hostname => {
      id          = container.vmid
      ip_address  = container.network[0].ip
      hostname    = container.hostname
      cores       = container.cores
      memory      = container.memory
      status      = container.status
      tags        = container.tags
    }
  }
}

output "monitoring_container_ips" {
  description = "IP addresses of monitoring containers"
  value = [
    for container in proxmox_lxc.monitoring : container.network[0].ip
  ]
}

# All VMs Output
output "all_vms" {
  description = "All VM details"
  value = merge(
    output.management_nodes.value,
    output.application_nodes.value,
    output.database_nodes.value,
    output.storage_nodes.value,
    output.load_balancers.value
  )
}

output "all_vm_ips" {
  description = "All VM IP addresses"
  value = concat(
    output.management_node_ips.value,
    output.application_node_ips.value,
    output.database_node_ips.value,
    output.storage_node_ips.value,
    output.load_balancer_ips.value
  )
}

# All Containers Output
output "all_containers" {
  description = "All container details"
  value = merge(
    output.redis_containers.value,
    output.monitoring_containers.value
  )
}

output "all_container_ips" {
  description = "All container IP addresses"
  value = concat(
    output.redis_container_ips.value,
    output.monitoring_container_ips.value
  )
}

# All Infrastructure Output
output "all_infrastructure" {
  description = "All infrastructure details"
  value = {
    vms = output.all_vms.value
    containers = output.all_containers.value
    total_vms = length(output.all_vm_ips.value)
    total_containers = length(output.all_container_ips.value)
    cluster_name = var.cluster_name
    network_cidr = var.network_cidr
    network_gateway = var.network_gateway
  }
}

# Service Discovery Outputs
output "service_endpoints" {
  description = "Service endpoints for load balancer configuration"
  value = {
    frontend = {
      nodes = output.application_node_ips.value
      port = var.suna_ports["frontend_http"]
    }
    api = {
      nodes = output.application_node_ips.value
      port = var.suna_ports["api_http"]
    }
    database = {
      nodes = output.database_node_ips.value
      port = var.suna_ports["postgres"]
    }
    redis = {
      nodes = output.redis_container_ips.value
      port = var.suna_ports["redis"]
    }
    monitoring = {
      nodes = output.monitoring_container_ips.value
      ports = {
        prometheus = var.suna_ports["prometheus"]
        grafana = var.suna_ports["grafana"]
        alertmanager = var.suna_ports["alertmanager"]
      }
    }
  }
}

# Load Balancer Configuration Output
output "load_balancer_config" {
  description = "Load balancer configuration for Ansible"
  value = {
    frontend_upstream = {
      servers = [
        for ip in output.application_node_ips.value : "${ip}:${var.suna_ports["frontend_http"]}"
      ]
      health_check = "/health"
    }
    api_upstream = {
      servers = [
        for ip in output.application_node_ips.value : "${ip}:${var.suna_ports["api_http"]}"
      ]
      health_check = "/health"
    }
    websocket_upstream = {
      servers = [
        for ip in output.application_node_ips.value : "${ip}:${var.suna_ports["websocket"]}"
      ]
    }
  }
}

# Monitoring Configuration Output
output "monitoring_config" {
  description = "Monitoring configuration for Prometheus"
  value = {
    prometheus_targets = {
      application_nodes = [
        for ip in output.application_node_ips.value : "${ip}:${var.suna_ports["api_http"]}"
      ]
      database_nodes = [
        for ip in output.database_node_ips.value : "${ip}:${var.suna_ports["postgres"]}"
      ]
      redis_containers = [
        for ip in output.redis_container_ips.value : "${ip}:${var.suna_ports["redis"]}"
      ]
      load_balancers = [
        for ip in output.load_balancer_ips.value : "${ip}:${var.suna_ports["lb_http"]}"
      ]
    }
    grafana_datasources = {
      prometheus = "http://localhost:${var.suna_ports["prometheus"]}"
    }
  }
}

# Backup Configuration Output
output "backup_config" {
  description = "Backup configuration for storage nodes"
  value = {
    storage_nodes = output.storage_node_ips.value
    backup_paths = {
      database = "/mnt/backup/database"
      files = "/mnt/backup/files"
      configs = "/mnt/backup/configs"
    }
  }
}

# Network Configuration Output
output "network_config" {
  description = "Network configuration details"
  value = {
    cluster_name = var.cluster_name
    network_cidr = var.network_cidr
    network_gateway = var.network_gateway
    network_bridge = var.network_bridge
    ip_ranges = {
      management = var.management_network_start_ip
      application = var.application_network_start_ip
      database = var.database_network_start_ip
      storage = var.storage_network_start_ip
      load_balancer = var.load_balancer_network_start_ip
      redis = var.redis_network_start_ip
      monitoring = var.monitoring_network_start_ip
    }
  }
}

# Port Configuration Output
output "port_config" {
  description = "Port configuration for all services"
  value = var.suna_ports
}

# Summary Output
output "deployment_summary" {
  description = "Summary of the deployed infrastructure"
  value = {
    cluster_name = var.cluster_name
    total_resources = {
      vms = length(output.all_vm_ips.value)
      containers = length(output.all_container_ips.value)
      total_ips = length(output.all_vm_ips.value) + length(output.all_container_ips.value)
    }
    resource_distribution = {
      management_nodes = length(output.management_node_ips.value)
      application_nodes = length(output.application_node_ips.value)
      database_nodes = length(output.database_node_ips.value)
      storage_nodes = length(output.storage_node_ips.value)
      load_balancers = length(output.load_balancer_ips.value)
      redis_containers = length(output.redis_container_ips.value)
      monitoring_containers = length(output.monitoring_container_ips.value)
    }
    network_info = {
      gateway = var.network_gateway
      cidr = var.network_cidr
      bridge = var.network_bridge
    }
    next_steps = [
      "Run Ansible playbooks to configure services",
      "Configure load balancer with provided configuration",
      "Set up monitoring with Prometheus targets",
      "Configure backup procedures",
      "Test all service endpoints"
    ]
  }
}







