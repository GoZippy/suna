#!/usr/bin/env python3
"""
Suna Admin CLI Tool

A comprehensive command-line interface for Suna system administration and maintenance.
"""

import os
import sys
import argparse
import asyncio
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from admin import ADMIN_CONFIG, SERVICE_CONFIG
from admin.monitoring import SystemMonitor
from admin.auth import AdminAuthService
from database import get_db


class SunaAdminCLI:
    """Suna Admin CLI tool"""
    
    def __init__(self):
        self.db = next(get_db())
        self.monitor = SystemMonitor(self.db)
        self.auth_service = AdminAuthService(self.db)
    
    def run(self):
        """Main CLI entry point"""
        parser = argparse.ArgumentParser(
            description="Suna Admin CLI - System administration and maintenance tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  suna-admin system status                    # Check system status
  suna-admin services restart backend         # Restart backend service
  suna-admin users list                       # List admin users
  suna-admin logs show backend --lines 50     # Show backend logs
  suna-admin backup create --type full        # Create full backup
  suna-admin config get admin_port            # Get configuration value
            """
        )
        
        # Create subparsers for different command categories
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # System commands
        self._add_system_commands(subparsers)
        
        # Service commands
        self._add_service_commands(subparsers)
        
        # User management commands
        self._add_user_commands(subparsers)
        
        # Log commands
        self._add_log_commands(subparsers)
        
        # Backup commands
        self._add_backup_commands(subparsers)
        
        # Configuration commands
        self._add_config_commands(subparsers)
        
        # Parse arguments
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        # Execute command
        try:
            if hasattr(self, f'cmd_{args.command}'):
                getattr(self, f'cmd_{args.command}')(args)
            else:
                print(f"Unknown command: {args.command}")
                parser.print_help()
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    def _add_system_commands(self, subparsers):
        """Add system-related commands"""
        system_parser = subparsers.add_parser('system', help='System management')
        system_subparsers = system_parser.add_subparsers(dest='subcommand')
        
        # System status
        status_parser = system_subparsers.add_parser('status', help='Check system status')
        status_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        
        # System metrics
        metrics_parser = system_subparsers.add_parser('metrics', help='Show system metrics')
        metrics_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        
        # System health
        health_parser = system_subparsers.add_parser('health', help='Check system health')
        health_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    def _add_service_commands(self, subparsers):
        """Add service-related commands"""
        service_parser = subparsers.add_parser('services', help='Service management')
        service_subparsers = service_parser.add_subparsers(dest='subcommand')
        
        # List services
        list_parser = service_subparsers.add_parser('list', help='List all services')
        list_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        
        # Service status
        status_parser = service_subparsers.add_parser('status', help='Check service status')
        status_parser.add_argument('service', help='Service name')
        status_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        
        # Service control
        for action in ['start', 'stop', 'restart', 'reload']:
            action_parser = service_subparsers.add_parser(action, help=f'{action.capitalize()} service')
            action_parser.add_argument('service', help='Service name')
            action_parser.add_argument('--force', action='store_true', help='Force action')
    
    def _add_user_commands(self, subparsers):
        """Add user management commands"""
        user_parser = subparsers.add_parser('users', help='User management')
        user_subparsers = user_parser.add_subparsers(dest='subcommand')
        
        # List users
        list_parser = user_subparsers.add_parser('list', help='List admin users')
        list_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        
        # Create user
        create_parser = user_subparsers.add_parser('create', help='Create admin user')
        create_parser.add_argument('--username', required=True, help='Username')
        create_parser.add_argument('--email', required=True, help='Email')
        create_parser.add_argument('--password', required=True, help='Password')
        create_parser.add_argument('--role', choices=['super_admin', 'admin', 'operator'], default='operator', help='User role')
        create_parser.add_argument('--full-name', help='Full name')
        
        # Update user
        update_parser = user_subparsers.add_parser('update', help='Update admin user')
        update_parser.add_argument('--user-id', required=True, help='User ID')
        update_parser.add_argument('--email', help='Email')
        update_parser.add_argument('--role', choices=['super_admin', 'admin', 'operator'], help='User role')
        update_parser.add_argument('--full-name', help='Full name')
        update_parser.add_argument('--active', type=bool, help='Active status')
        
        # Delete user
        delete_parser = user_subparsers.add_parser('delete', help='Delete admin user')
        delete_parser.add_argument('--user-id', required=True, help='User ID')
    
    def _add_log_commands(self, subparsers):
        """Add log management commands"""
        log_parser = subparsers.add_parser('logs', help='Log management')
        log_subparsers = log_parser.add_subparsers(dest='subcommand')
        
        # Show logs
        show_parser = log_subparsers.add_parser('show', help='Show service logs')
        show_parser.add_argument('service', help='Service name')
        show_parser.add_argument('--lines', type=int, default=100, help='Number of lines to show')
        show_parser.add_argument('--follow', action='store_true', help='Follow log output')
        
        # Search logs
        search_parser = log_subparsers.add_parser('search', help='Search logs')
        search_parser.add_argument('service', help='Service name')
        search_parser.add_argument('query', help='Search query')
        search_parser.add_argument('--lines', type=int, default=100, help='Number of lines to show')
    
    def _add_backup_commands(self, subparsers):
        """Add backup management commands"""
        backup_parser = subparsers.add_parser('backup', help='Backup management')
        backup_subparsers = backup_parser.add_subparsers(dest='subcommand')
        
        # Create backup
        create_parser = backup_subparsers.add_parser('create', help='Create backup')
        create_parser.add_argument('--type', choices=['database', 'files', 'full'], default='full', help='Backup type')
        create_parser.add_argument('--output', help='Output file path')
        
        # List backups
        list_parser = backup_subparsers.add_parser('list', help='List backups')
        list_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        
        # Restore backup
        restore_parser = backup_subparsers.add_parser('restore', help='Restore backup')
        restore_parser.add_argument('backup-id', help='Backup ID')
        restore_parser.add_argument('--force', action='store_true', help='Force restore')
    
    def _add_config_commands(self, subparsers):
        """Add configuration management commands"""
        config_parser = subparsers.add_parser('config', help='Configuration management')
        config_subparsers = config_parser.add_subparsers(dest='subcommand')
        
        # Get config
        get_parser = config_subparsers.add_parser('get', help='Get configuration value')
        get_parser.add_argument('key', help='Configuration key')
        
        # Set config
        set_parser = config_subparsers.add_parser('set', help='Set configuration value')
        set_parser.add_argument('key', help='Configuration key')
        set_parser.add_argument('value', help='Configuration value')
        
        # List config
        list_parser = config_subparsers.add_parser('list', help='List all configuration')
        list_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    async def cmd_system(self, args):
        """Handle system commands"""
        if args.subcommand == 'status':
            await self._system_status(args)
        elif args.subcommand == 'metrics':
            await self._system_metrics(args)
        elif args.subcommand == 'health':
            await self._system_health(args)
        else:
            print(f"Unknown system subcommand: {args.subcommand}")
    
    async def cmd_services(self, args):
        """Handle service commands"""
        if args.subcommand == 'list':
            await self._services_list(args)
        elif args.subcommand == 'status':
            await self._service_status(args)
        elif args.subcommand in ['start', 'stop', 'restart', 'reload']:
            await self._service_control(args)
        else:
            print(f"Unknown services subcommand: {args.subcommand}")
    
    def cmd_users(self, args):
        """Handle user commands"""
        if args.subcommand == 'list':
            self._users_list(args)
        elif args.subcommand == 'create':
            self._user_create(args)
        elif args.subcommand == 'update':
            self._user_update(args)
        elif args.subcommand == 'delete':
            self._user_delete(args)
        else:
            print(f"Unknown users subcommand: {args.subcommand}")
    
    def cmd_logs(self, args):
        """Handle log commands"""
        if args.subcommand == 'show':
            self._logs_show(args)
        elif args.subcommand == 'search':
            self._logs_search(args)
        else:
            print(f"Unknown logs subcommand: {args.subcommand}")
    
    def cmd_backup(self, args):
        """Handle backup commands"""
        if args.subcommand == 'create':
            self._backup_create(args)
        elif args.subcommand == 'list':
            self._backup_list(args)
        elif args.subcommand == 'restore':
            self._backup_restore(args)
        else:
            print(f"Unknown backup subcommand: {args.subcommand}")
    
    def cmd_config(self, args):
        """Handle config commands"""
        if args.subcommand == 'get':
            self._config_get(args)
        elif args.subcommand == 'set':
            self._config_set(args)
        elif args.subcommand == 'list':
            self._config_list(args)
        else:
            print(f"Unknown config subcommand: {args.subcommand}")
    
    async def _system_status(self, args):
        """Show system status"""
        print("🔍 Checking system status...")
        
        # Get system health
        system_health = await self.monitor.get_system_health()
        
        if args.json:
            print(json.dumps(system_health.dict(), indent=2, default=str))
        else:
            print(f"Overall Status: {system_health.overall_status.value.upper()}")
            print(f"Healthy Services: {system_health.healthy_services}/{system_health.total_services}")
            print(f"Degraded Services: {system_health.degraded_services}")
            print(f"Down Services: {system_health.down_services}")
            print(f"Last Updated: {system_health.last_updated}")
    
    async def _system_metrics(self, args):
        """Show system metrics"""
        print("📊 Getting system metrics...")
        
        metrics = await self.monitor.get_system_metrics()
        
        if args.json:
            print(json.dumps(metrics.dict(), indent=2, default=str))
        else:
            print(f"CPU Usage: {metrics.cpu_usage_percent:.1f}%")
            print(f"Memory Usage: {metrics.memory_usage_percent:.1f}%")
            print(f"Disk Usage: {metrics.disk_usage_percent:.1f}%")
            print(f"Load Average: {metrics.load_average_1m:.2f} (1m), {metrics.load_average_5m:.2f} (5m), {metrics.load_average_15m:.2f} (15m)")
            print(f"Uptime: {timedelta(seconds=metrics.uptime_seconds)}")
    
    async def _system_health(self, args):
        """Show system health"""
        print("🏥 Checking system health...")
        
        health = await self.monitor.get_system_health()
        
        if args.json:
            print(json.dumps(health.dict(), indent=2, default=str))
        else:
            status_emoji = {
                'healthy': '✅',
                'degraded': '⚠️',
                'down': '❌',
                'unknown': '❓'
            }
            
            print(f"Overall Status: {status_emoji.get(health.overall_status.value, '❓')} {health.overall_status.value.upper()}")
            print(f"Services: {health.healthy_services} healthy, {health.degraded_services} degraded, {health.down_services} down")
            print(f"Alerts: {health.critical_alerts} critical, {health.warning_alerts} warning, {health.info_alerts} info")
    
    async def _services_list(self, args):
        """List all services"""
        print("📋 Listing services...")
        
        services = await self.monitor.check_all_services()
        
        if args.json:
            print(json.dumps([s.dict() for s in services], indent=2, default=str))
        else:
            print(f"{'Service':<20} {'Status':<10} {'Port':<8} {'Response Time':<15}")
            print("-" * 60)
            for service in services:
                status_emoji = {
                    'healthy': '✅',
                    'degraded': '⚠️',
                    'down': '❌',
                    'unknown': '❓'
                }
                status = f"{status_emoji.get(service.status.value, '❓')} {service.status.value}"
                response_time = f"{service.response_time_ms:.1f}ms" if service.response_time_ms else "N/A"
                print(f"{service.service_name:<20} {status:<10} {service.port:<8} {response_time:<15}")
    
    async def _service_status(self, args):
        """Check specific service status"""
        print(f"🔍 Checking status of {args.service}...")
        
        service = await self.monitor.check_service_health(args.service)
        
        if args.json:
            print(json.dumps(service.dict(), indent=2, default=str))
        else:
            status_emoji = {
                'healthy': '✅',
                'degraded': '⚠️',
                'down': '❌',
                'unknown': '❓'
            }
            
            print(f"Service: {service.service_name}")
            print(f"Status: {status_emoji.get(service.status.value, '❓')} {service.status.value.upper()}")
            print(f"Port: {service.port}")
            if service.response_time_ms:
                print(f"Response Time: {service.response_time_ms:.1f}ms")
            if service.version:
                print(f"Version: {service.version}")
            if service.error_message:
                print(f"Error: {service.error_message}")
    
    async def _service_control(self, args):
        """Control service"""
        action = args.subcommand
        service_id = args.service
        
        print(f"🔄 {action.capitalize()}ing {service_id}...")
        
        # Check if service exists
        service_config = SERVICE_CONFIG['services'].get(service_id)
        if not service_config:
            print(f"❌ Service '{service_id}' not found")
            return
        
        try:
            # Execute service control command
            command = service_config['restart_command']
            if action == "stop":
                command = command.replace("restart", "stop")
            elif action == "start":
                command = command.replace("restart", "start")
            elif action == "reload":
                command = command.replace("restart", "reload")
            
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"✅ {action.capitalize()}ed {service_id} successfully")
                if result.stdout:
                    print(f"Output: {result.stdout}")
            else:
                print(f"❌ Failed to {action} {service_id}")
                print(f"Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"❌ {action.capitalize()} timed out")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def _users_list(self, args):
        """List admin users"""
        print("👥 Listing admin users...")
        
        users = self.auth_service.list_admin_users()
        
        if args.json:
            print(json.dumps([u.dict() for u in users], indent=2, default=str))
        else:
            print(f"{'ID':<36} {'Username':<20} {'Email':<30} {'Role':<15} {'Status':<10}")
            print("-" * 120)
            for user in users:
                status = "Active" if user.is_active else "Inactive"
                print(f"{user.id:<36} {user.username:<20} {user.email:<30} {user.role.value:<15} {status:<10}")
    
    def _user_create(self, args):
        """Create admin user"""
        print(f"👤 Creating admin user '{args.username}'...")
        
        from admin.models import AdminUserCreate, AdminRole
        
        user_data = AdminUserCreate(
            username=args.username,
            email=args.email,
            password=args.password,
            role=AdminRole(args.role),
            full_name=args.full_name
        )
        
        try:
            user = self.auth_service.create_admin_user(user_data)
            print(f"✅ User '{user.username}' created successfully")
            print(f"ID: {user.id}")
            print(f"Role: {user.role.value}")
        except Exception as e:
            print(f"❌ Failed to create user: {e}")
    
    def _user_update(self, args):
        """Update admin user"""
        print(f"✏️  Updating admin user '{args.user_id}'...")
        
        from admin.models import AdminUserUpdate, AdminRole
        
        update_data = AdminUserUpdate()
        if args.email:
            update_data.email = args.email
        if args.role:
            update_data.role = AdminRole(args.role)
        if args.full_name:
            update_data.full_name = args.full_name
        if args.active is not None:
            update_data.is_active = args.active
        
        try:
            user = self.auth_service.update_admin_user(args.user_id, update_data)
            print(f"✅ User '{user.username}' updated successfully")
        except Exception as e:
            print(f"❌ Failed to update user: {e}")
    
    def _user_delete(self, args):
        """Delete admin user"""
        print(f"🗑️  Deleting admin user '{args.user_id}'...")
        
        try:
            success = self.auth_service.delete_admin_user(args.user_id)
            if success:
                print(f"✅ User deleted successfully")
            else:
                print(f"❌ User not found")
        except Exception as e:
            print(f"❌ Failed to delete user: {e}")
    
    def _logs_show(self, args):
        """Show service logs"""
        service_id = args.service
        
        print(f"📄 Showing logs for {service_id}...")
        
        # Check if service exists
        service_config = SERVICE_CONFIG['services'].get(service_id)
        if not service_config:
            print(f"❌ Service '{service_id}' not found")
            return
        
        try:
            # Get logs using tail command
            cmd = ["tail", "-n", str(args.lines)]
            if args.follow:
                cmd.append("-f")
            cmd.append(service_config['log_file'])
            
            subprocess.run(cmd)
            
        except FileNotFoundError:
            print(f"❌ Log file not found: {service_config['log_file']}")
        except Exception as e:
            print(f"❌ Error reading logs: {e}")
    
    def _logs_search(self, args):
        """Search service logs"""
        service_id = args.service
        query = args.query
        
        print(f"🔍 Searching logs for '{query}' in {service_id}...")
        
        # Check if service exists
        service_config = SERVICE_CONFIG['services'].get(service_id)
        if not service_config:
            print(f"❌ Service '{service_id}' not found")
            return
        
        try:
            # Search logs using grep
            cmd = ["grep", "-n", query, service_config['log_file']]
            if args.lines:
                cmd.extend(["-A", str(args.lines)])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("No matches found")
                
        except FileNotFoundError:
            print(f"❌ Log file not found: {service_config['log_file']}")
        except Exception as e:
            print(f"❌ Error searching logs: {e}")
    
    def _backup_create(self, args):
        """Create backup"""
        backup_type = args.type
        output_path = args.output
        
        print(f"💾 Creating {backup_type} backup...")
        
        # This would implement actual backup logic
        # For now, just show what would be done
        
        if backup_type == "database":
            print("Would create database backup using pg_dump")
        elif backup_type == "files":
            print("Would create file system backup")
        elif backup_type == "full":
            print("Would create full system backup")
        
        if output_path:
            print(f"Output path: {output_path}")
    
    def _backup_list(self, args):
        """List backups"""
        print("📋 Listing backups...")
        
        # This would query actual backup storage
        # For now, show mock data
        
        if args.json:
            print(json.dumps([], indent=2))
        else:
            print("No backups found")
    
    def _backup_restore(self, args):
        """Restore backup"""
        backup_id = args.backup_id
        
        print(f"🔄 Restoring backup '{backup_id}'...")
        
        if args.force:
            print("Force restore enabled")
        
        # This would implement actual restore logic
        print("Would restore backup from storage")
    
    def _config_get(self, args):
        """Get configuration value"""
        key = args.key
        
        print(f"🔧 Getting configuration '{key}'...")
        
        # Check if key exists in admin config
        if key in ADMIN_CONFIG:
            value = ADMIN_CONFIG[key]
            print(f"{key}: {value}")
        else:
            print(f"❌ Configuration key '{key}' not found")
    
    def _config_set(self, args):
        """Set configuration value"""
        key = args.key
        value = args.value
        
        print(f"🔧 Setting configuration '{key}' to '{value}'...")
        
        # This would update actual configuration storage
        print(f"Would update {key} = {value}")
    
    def _config_list(self, args):
        """List all configuration"""
        print("🔧 Listing configuration...")
        
        if args.json:
            print(json.dumps(ADMIN_CONFIG, indent=2))
        else:
            for key, value in ADMIN_CONFIG.items():
                print(f"{key}: {value}")


def main():
    """Main entry point"""
    cli = SunaAdminCLI()
    
    # Run async commands
    if len(sys.argv) > 1 and sys.argv[1] in ['system', 'services']:
        asyncio.run(cli.run())
    else:
        cli.run()


if __name__ == "__main__":
    main()







