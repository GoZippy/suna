# Requirements Document

## Introduction

This document outlines the requirements for migrating Suna from a third-party service dependent architecture to a fully self-hosted, open-source solution. The goal is to eliminate all external paid dependencies while maintaining full functionality, enabling deployment on local infrastructure including Proxmox VMs/LXCs for both development and production use.

## Requirements

### Requirement 1: Database Migration from Supabase

**User Story:** As a self-hosting administrator, I want to replace Supabase with local database solutions, so that I can eliminate external dependencies and maintain full control over data storage.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL connect to a locally hosted PostgreSQL database instead of Supabase
2. WHEN authentication is required THEN the system SHALL use a local authentication service instead of Supabase Auth
3. WHEN real-time features are needed THEN the system SHALL implement WebSocket-based real-time functionality locally
4. WHEN file storage is required THEN the system SHALL use local file storage instead of Supabase Storage
5. WHEN database migrations run THEN they SHALL work with the local PostgreSQL instance
6. WHEN the basejump schema is needed THEN it SHALL be implemented locally or replaced with equivalent functionality

### Requirement 2: Vector Database Integration

**User Story:** As a developer, I want to implement local vector database capabilities, so that I can support AI-powered search and knowledge base features without external dependencies.

#### Acceptance Criteria

1. WHEN vector embeddings need to be stored THEN the system SHALL use a local vector database solution
2. WHEN similarity searches are performed THEN the system SHALL query the local vector database
3. WHEN knowledge base features are used THEN they SHALL work with the local vector storage
4. WHEN embedding generation is needed THEN the system SHALL use local or self-hosted embedding models
5. WHEN vector database scaling is required THEN the solution SHALL support horizontal scaling on Proxmox infrastructure

### Requirement 3: Replace Daytona Sandbox Service

**User Story:** As a system administrator, I want to replace Daytona with local container orchestration, so that I can run agent sandboxes without external service dependencies.

#### Acceptance Criteria

1. WHEN agent execution is required THEN the system SHALL use local Docker containers instead of Daytona
2. WHEN sandbox isolation is needed THEN the system SHALL provide equivalent security isolation locally
3. WHEN file system access is required THEN the system SHALL provide secure file operations within local containers
4. WHEN VNC access is needed THEN the system SHALL provide local VNC server capabilities
5. WHEN multiple sandboxes run concurrently THEN the system SHALL manage resources efficiently on Proxmox infrastructure

### Requirement 4: Local Search and Web Scraping Services

**User Story:** As a user, I want search and web scraping functionality to work without external API dependencies, so that I can use these features in a fully offline environment.

#### Acceptance Criteria

1. WHEN web search is required THEN the system SHALL use local search engines or web crawling capabilities
2. WHEN web scraping is needed THEN the system SHALL use local scraping tools instead of Firecrawl
3. WHEN search results are processed THEN the system SHALL provide equivalent functionality to Tavily locally
4. WHEN rate limiting is needed THEN the system SHALL implement local rate limiting mechanisms
5. WHEN search indexing is required THEN the system SHALL maintain local search indexes

### Requirement 5: Replace Stripe Billing System

**User Story:** As a self-hosting administrator, I want to remove billing functionality or replace it with local user management, so that I can operate without payment processing dependencies.

#### Acceptance Criteria

1. WHEN user access control is needed THEN the system SHALL use local role-based access control
2. WHEN usage tracking is required THEN the system SHALL implement local usage monitoring
3. WHEN subscription management is needed THEN the system SHALL provide local user tier management
4. WHEN billing-related features are accessed THEN the system SHALL either disable them or provide local alternatives
5. WHEN credit systems are used THEN the system SHALL implement local credit tracking without payment processing

### Requirement 6: Local Authentication and User Management

**User Story:** As a system administrator, I want complete local user management capabilities, so that I can control access without relying on external authentication services.

#### Acceptance Criteria

1. WHEN users register THEN the system SHALL store credentials in the local database
2. WHEN users authenticate THEN the system SHALL validate against local user storage
3. WHEN JWT tokens are issued THEN they SHALL be signed with local keys
4. WHEN password reset is needed THEN the system SHALL handle it through local email or admin processes
5. WHEN user roles are managed THEN the system SHALL use local role-based access control

### Requirement 7: Local Email and Notification Services

**User Story:** As a system administrator, I want to handle email notifications locally, so that I can eliminate external email service dependencies.

#### Acceptance Criteria

1. WHEN email notifications are sent THEN the system SHALL use local SMTP configuration
2. WHEN email templates are needed THEN they SHALL be stored and processed locally
3. WHEN notification queuing is required THEN the system SHALL use local message queues
4. WHEN email delivery fails THEN the system SHALL handle retries locally
5. WHEN email configuration is needed THEN it SHALL support standard SMTP servers

### Requirement 8: Local Background Job Processing

**User Story:** As a developer, I want background job processing to work without external queue services, so that I can maintain full control over task execution.

#### Acceptance Criteria

1. WHEN background jobs are queued THEN the system SHALL use local job queue implementation
2. WHEN scheduled tasks are needed THEN the system SHALL use local cron-like scheduling
3. WHEN job monitoring is required THEN the system SHALL provide local job status tracking
4. WHEN job scaling is needed THEN the system SHALL support multiple worker processes
5. WHEN job persistence is required THEN jobs SHALL be stored in the local database

### Requirement 9: Local Model and AI Service Integration

**User Story:** As a user, I want to optionally use local AI models, so that I can reduce external API costs and improve privacy.

#### Acceptance Criteria

1. WHEN LLM inference is needed THEN the system SHALL support local model deployment options
2. WHEN embedding generation is required THEN the system SHALL support local embedding models
3. WHEN external API keys are not provided THEN the system SHALL fall back to local models
4. WHEN model switching is needed THEN the system SHALL support both local and external models
5. WHEN GPU resources are available THEN the system SHALL utilize them for local model inference

### Requirement 10: Container Orchestration and Deployment

**User Story:** As a DevOps engineer, I want streamlined deployment on Proxmox infrastructure, so that I can easily set up and scale the self-hosted solution.

#### Acceptance Criteria

1. WHEN deploying the system THEN it SHALL provide Docker Compose configurations for all services
2. WHEN scaling is needed THEN the system SHALL support deployment across multiple Proxmox VMs/LXCs
3. WHEN service discovery is required THEN the system SHALL use local service discovery mechanisms
4. WHEN load balancing is needed THEN the system SHALL provide local load balancing options
5. WHEN monitoring is required THEN the system SHALL include local monitoring and logging solutions

### Requirement 11: Data Migration and Backup

**User Story:** As a system administrator, I want robust data migration and backup capabilities, so that I can safely transition from external services and maintain data integrity.

#### Acceptance Criteria

1. WHEN migrating from Supabase THEN the system SHALL provide migration scripts for data export/import
2. WHEN backing up data THEN the system SHALL support local backup strategies
3. WHEN restoring data THEN the system SHALL provide reliable restoration procedures
4. WHEN data consistency is required THEN the system SHALL maintain referential integrity during migration
5. WHEN configuration is migrated THEN the system SHALL convert external service configurations to local equivalents

### Requirement 12: Security and Access Control

**User Story:** As a security administrator, I want comprehensive local security controls, so that I can maintain security standards without relying on external security services.

#### Acceptance Criteria

1. WHEN API access is controlled THEN the system SHALL implement local API key management
2. WHEN encryption is needed THEN the system SHALL use local encryption key management
3. WHEN access logging is required THEN the system SHALL maintain local audit logs
4. WHEN network security is needed THEN the system SHALL support local firewall and network policies
5. WHEN secrets management is required THEN the system SHALL provide local secrets storage and rotation
