terraform {
  required_version = ">= 1.5.0"
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "~> 2.9"
    }
  }
}

# Configure the Proxmox Provider
provider "proxmox" {
  pm_api_url          = var.proxmox_api_url
  pm_api_token_id     = var.proxmox_api_token_id
  pm_api_token_secret = var.proxmox_api_token_secret
  pm_tls_insecure     = var.proxmox_tls_insecure
  pm_debug            = var.proxmox_debug
  pm_log_enable       = true
  pm_log_file         = "terraform.log"
}

# Create VM for Management Node
resource "proxmox_vm_qemu" "management_node" {
  count       = var.management_node_count
  name        = "${var.cluster_name}-management-${count.index + 1}"
  target_node = var.proxmox_node
  clone       = var.template_name
  full_clone  = true
  agent       = 1
  os_type     = "cloud-init"
  cores       = var.management_vm_cores
  sockets     = 1
  cpu         = "host"
  memory      = var.management_vm_memory
  scsihw      = "virtio-scsi-pci"
  bootdisk    = "scsi0"
  disk {
    slot     = 0
    size     = var.management_vm_disk_size
    type     = "scsi"
    storage  = var.storage_pool
    ssd      = 1
  }
  network {
    model  = "virtio"
    bridge = var.network_bridge
  }
  ipconfig0 = "ip=${var.management_network_start_ip}${count.index + 1}/${var.network_cidr},gw=${var.network_gateway}"
  sshkeys   = var.ssh_public_key
  tags      = ["suna", "management", "terraform-managed"]
  
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}

# Create VMs for Application Nodes
resource "proxmox_vm_qemu" "application_nodes" {
  count       = var.application_node_count
  name        = "${var.cluster_name}-app-${count.index + 1}"
  target_node = var.proxmox_node
  clone       = var.template_name
  full_clone  = true
  agent       = 1
  os_type     = "cloud-init"
  cores       = var.application_vm_cores
  sockets     = 1
  cpu         = "host"
  memory      = var.application_vm_memory
  scsihw      = "virtio-scsi-pci"
  bootdisk    = "scsi0"
  disk {
    slot     = 0
    size     = var.application_vm_disk_size
    type     = "scsi"
    storage  = var.storage_pool
    ssd      = 1
  }
  network {
    model  = "virtio"
    bridge = var.network_bridge
  }
  ipconfig0 = "ip=${var.application_network_start_ip}${count.index + 1}/${var.network_cidr},gw=${var.network_gateway}"
  sshkeys   = var.ssh_public_key
  tags      = ["suna", "application", "terraform-managed"]
  
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}

# Create VM for Database Node
resource "proxmox_vm_qemu" "database_node" {
  count       = var.database_node_count
  name        = "${var.cluster_name}-db-${count.index + 1}"
  target_node = var.proxmox_node
  clone       = var.template_name
  full_clone  = true
  agent       = 1
  os_type     = "cloud-init"
  cores       = var.database_vm_cores
  sockets     = 1
  cpu         = "host"
  memory      = var.database_vm_memory
  scsihw      = "virtio-scsi-pci"
  bootdisk    = "scsi0"
  disk {
    slot     = 0
    size     = var.database_vm_disk_size
    type     = "scsi"
    storage  = var.storage_pool
    ssd      = 1
  }
  # Additional disk for database storage
  disk {
    slot     = 1
    size     = var.database_storage_disk_size
    type     = "scsi"
    storage  = var.storage_pool
    ssd      = 1
  }
  network {
    model  = "virtio"
    bridge = var.network_bridge
  }
  ipconfig0 = "ip=${var.database_network_start_ip}${count.index + 1}/${var.network_cidr},gw=${var.network_gateway}"
  sshkeys   = var.ssh_public_key
  tags      = ["suna", "database", "terraform-managed"]
  
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}

# Create VM for Storage Node
resource "proxmox_vm_qemu" "storage_node" {
  count       = var.storage_node_count
  name        = "${var.cluster_name}-storage-${count.index + 1}"
  target_node = var.proxmox_node
  clone       = var.template_name
  full_clone  = true
  agent       = 1
  os_type     = "cloud-init"
  cores       = var.storage_vm_cores
  sockets     = 1
  cpu         = "host"
  memory      = var.storage_vm_memory
  scsihw      = "virtio-scsi-pci"
  bootdisk    = "scsi0"
  disk {
    slot     = 0
    size     = var.storage_vm_disk_size
    type     = "scsi"
    storage  = var.storage_pool
    ssd      = 1
  }
  # Additional disks for file storage
  disk {
    slot     = 1
    size     = var.file_storage_disk_size
    type     = "scsi"
    storage  = var.storage_pool
    ssd      = 0
  }
  disk {
    slot     = 2
    size     = var.backup_storage_disk_size
    type     = "scsi"
    storage  = var.storage_pool
    ssd      = 0
  }
  network {
    model  = "virtio"
    bridge = var.network_bridge
  }
  ipconfig0 = "ip=${var.storage_network_start_ip}${count.index + 1}/${var.network_cidr},gw=${var.network_gateway}"
  sshkeys   = var.ssh_public_key
  tags      = ["suna", "storage", "terraform-managed"]
  
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}

# Create VM for Load Balancer
resource "proxmox_vm_qemu" "load_balancer" {
  count       = var.load_balancer_count
  name        = "${var.cluster_name}-lb-${count.index + 1}"
  target_node = var.proxmox_node
  clone       = var.template_name
  full_clone  = true
  agent       = 1
  os_type     = "cloud-init"
  cores       = var.load_balancer_vm_cores
  sockets     = 1
  cpu         = "host"
  memory      = var.load_balancer_vm_memory
  scsihw      = "virtio-scsi-pci"
  bootdisk    = "scsi0"
  disk {
    slot     = 0
    size     = var.load_balancer_vm_disk_size
    type     = "scsi"
    storage  = var.storage_pool
    ssd      = 1
  }
  network {
    model  = "virtio"
    bridge = var.network_bridge
  }
  ipconfig0 = "ip=${var.load_balancer_network_start_ip}${count.index + 1}/${var.network_cidr},gw=${var.network_gateway}"
  sshkeys   = var.ssh_public_key
  tags      = ["suna", "load-balancer", "terraform-managed"]
  
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}

# Create LXC Container for Redis
resource "proxmox_lxc" "redis" {
  count     = var.redis_container_count
  hostname  = "${var.cluster_name}-redis-${count.index + 1}"
  target_node = var.proxmox_node
  ostemplate = var.lxc_template
  password  = var.lxc_password
  cores     = var.redis_cores
  memory    = var.redis_memory
  swap      = var.redis_swap
  rootfs {
    storage = var.storage_pool
    size    = var.redis_disk_size
  }
  network {
    name   = "eth0"
    bridge = var.network_bridge
    ip     = "${var.redis_network_start_ip}${count.index + 1}/${var.network_cidr}"
    gw     = var.network_gateway
  }
  ssh_public_keys = var.ssh_public_key
  tags = ["suna", "redis", "terraform-managed"]
}

# Create LXC Container for Monitoring
resource "proxmox_lxc" "monitoring" {
  count     = var.monitoring_container_count
  hostname  = "${var.cluster_name}-monitoring-${count.index + 1}"
  target_node = var.proxmox_node
  ostemplate = var.lxc_template
  password  = var.lxc_password
  cores     = var.monitoring_cores
  memory    = var.monitoring_memory
  swap      = var.monitoring_swap
  rootfs {
    storage = var.storage_pool
    size    = var.monitoring_disk_size
  }
  network {
    name   = "eth0"
    bridge = var.network_bridge
    ip     = "${var.monitoring_network_start_ip}${count.index + 1}/${var.network_cidr}"
    gw     = var.network_gateway
  }
  ssh_public_keys = var.ssh_public_key
  tags = ["suna", "monitoring", "terraform-managed"]
}

# Create firewall rules for Suna services
resource "proxmox_vm_qemu" "firewall_rules" {
  # This is a placeholder for firewall configuration
  # In a real implementation, you would use Proxmox firewall API
  # or configure firewall rules through cloud-init
  
  count       = 0  # Disabled for now
  name        = "firewall-config"
  target_node = var.proxmox_node
  clone       = var.template_name
  full_clone  = true
  agent       = 1
  cores       = 1
  memory      = 512
  disk {
    slot     = 0
    size     = "10G"
    type     = "scsi"
    storage  = var.storage_pool
  }
  network {
    model  = "virtio"
    bridge = var.network_bridge
  }
  tags = ["suna", "firewall", "terraform-managed"]
}







