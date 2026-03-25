# Implementation Plan

- [x] 1. Set up local PostgreSQL database with pgvector extension

  - Create Docker Compose configuration for PostgreSQL 16 with pgvector extension
  - Configure database connection pooling and performance settings
  - Create initial database schema migration scripts from Supabase structure
  - Implement database backup and restore procedures
  - Write database connection abstraction layer to replace Supabase client
  - _Requirements: 1.1, 1.2, 1.5, 1.6_

- [x] 2. Implement local authentication system

  - Create user registration and login API endpoints with JWT token generation
  - Implement password hashing using bcrypt and secure password policies
  - Build JWT token validation middleware for FastAPI routes
  - Create user session management with token refresh capabilities
  - Implement role-based access control (RBAC) system
  - Write user management admin interface for local user administration
  - _Requirements: 6.1, 6.2, 6.3, 6.5, 12.1_

- [x] 3. Replace Supabase database integration

  - Migrate all existing Supabase table schemas to PostgreSQL
  - Update all database queries to use direct PostgreSQL connections
  - Replace Supabase real-time subscriptions with WebSocket implementation
  - Migrate file storage from Supabase Storage to local file system
  - Update all authentication flows to use local JWT system
  - Create data migration scripts for existing Supabase data export/import
  - _Requirements: 1.1, 1.3, 1.4, 11.1, 11.4_

- [x] 4. Implement vector database functionality

  - Install and configure pgvector extension for PostgreSQL
  - Create vector storage tables for knowledge base and embeddings
  - Implement similarity search functions using pgvector
  - Build embedding generation service using local sentence-transformers
  - Create vector indexing and optimization for large datasets
  - Implement hybrid search combining text and vector similarity
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 5. Build local container orchestration system

  - Create Docker-based sandbox manager to replace Daytona functionality
  - Implement container lifecycle management (create, start, stop, delete)
  - Build secure container isolation with resource limits and network segmentation
  - Create VNC server integration for GUI access to sandbox containers
  - Implement file system operations within sandbox containers
  - Build container health monitoring and automatic restart capabilities
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 6. Create agent sandbox container images

  - Build base Ubuntu 22.04 container image with development tools
  - Install Python 3.11+, Node.js 20+, and common development packages
  - Configure VNC server (TigerVNC) with web-based access
  - Install browser automation tools (Playwright, Selenium)

  - Set up Supervisor for process management within containers
  - Create container security hardening and non-root user configuration
  - _Requirements: 3.1, 3.2, 3.4_

- [x] 7. Implement local search and web scraping services


  - Deploy SearXNG as local metasearch engine for web search functionality
  - Create web scraping service using Playwright and BeautifulSoup
  - Implement rate limiting and proxy rotation for scraping operations
  - Build search result caching and deduplication system
  - Create API endpoints that match Tavily and Firecrawl interfaces
  - Implement search indexing for local content and cached results
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8. Replace Stripe billing with local user management

  - Remove all Stripe-related code and dependencies
  - Implement local user tier system (free, pro, enterprise)
  - Create usage tracking and monitoring without payment processing
  - Build local credit system for resource allocation
  - Implement admin interface for user tier management
  - Create usage reporting and analytics dashboard
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 9. Set up local AI/ML services

  - Deploy Ollama server for local LLM inference
  - Configure automatic model downloading and management
  - Implement model switching between local and external APIs
  - Set up local embedding service using sentence-transformers
  - Create GPU acceleration configuration for model inference
  - Build model performance monitoring and resource usage tracking
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 10. Implement local email and notification system ✅

  - Configure local SMTP server (Postfix) or use external SMTP
  - Create email template system for notifications and alerts
  - Implement email queue management with retry logic
  - Build notification service for system events and user alerts
  - Create email delivery status tracking and bounce handling
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 11. Build local background job processing ✅

  - Replace external queue services with Redis-based job queue
  - Implement Dramatiq worker configuration for local deployment
  - Create job scheduling system using APScheduler
  - Build job monitoring and status tracking interface
  - Implement job persistence and failure recovery mechanisms
  - Create worker scaling and load balancing for multiple processes
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 12. Create WebSocket real-time communication ✅

  - Implement FastAPI WebSocket endpoints for real-time features
  - Build connection management for multiple concurrent users
  - Create real-time agent status updates and progress notifications
  - Implement live chat functionality between users and agents
  - Build file system change notifications for collaborative editing
  - Create WebSocket authentication and authorization
  - _Requirements: 1.3, 6.4_

- [x] 13. Implement local file storage system ✅

  - Create organized directory structure for project and user files
  - Implement file upload, download, and management APIs
  - Build file versioning and backup capabilities
  - Create file sharing and permission management
  - Implement file search and indexing functionality
  - Build file storage quota management and cleanup procedures
  - _Requirements: 1.4, 11.2, 11.3_

- [x] 14. Set up monitoring and logging infrastructure ✅

  - Deploy Prometheus for metrics collection from all services
  - Configure Grafana dashboards for system monitoring and alerting
  - Implement structured logging with centralized log aggregation
  - Create health check endpoints for all services
  - Build automated alerting for service failures and performance issues
  - Implement audit logging for security and compliance
  - _Requirements: 12.3, 12.5_

- [x] 15. Create Docker Compose deployment configuration ✅

  - Build comprehensive Docker Compose file for all services
  - Configure service dependencies and startup ordering
  - Implement environment variable management and secrets handling
  - Create volume management for persistent data storage
  - Build network configuration for service isolation and communication
  - Create development and production deployment variants
  - _Requirements: 10.1, 10.2_

- [x] 16. Implement security hardening ✅

  - Configure TLS/SSL certificates for all external communications
  - Implement API rate limiting and DDoS protection
  - Create input validation and sanitization for all endpoints
  - Build SQL injection prevention and secure query practices
  - Implement container security scanning and vulnerability management
  - Create network security policies and firewall configurations
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 17. Build data migration tools ✅

  - Create Supabase data export scripts for existing installations
  - Build PostgreSQL data import and schema migration tools
  - Implement configuration migration from external services to local
  - Create backup and restore procedures for local deployment
  - Build data validation and integrity checking tools
  - Create rollback procedures for failed migrations
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 18. Create Proxmox deployment automation ✅

  - Build Terraform or Ansible scripts for VM/LXC provisioning
  - Create automated deployment scripts for multi-VM setup
  - Implement service discovery and load balancing configuration
  - Build monitoring and alerting for distributed deployment
  - Create backup and disaster recovery procedures
  - Implement scaling procedures for increased load
  - _Requirements: 10.2, 10.3, 10.4, 10.5_

- [x] 19. Implement performance optimization ✅

  - Optimize database queries and indexing for improved performance
  - Configure connection pooling and caching strategies
  - Implement container resource optimization and efficient startup
  - Build query result caching and application-level caching
  - Create performance monitoring and bottleneck identification
  - Implement auto-scaling based on resource utilization
  - _Requirements: 2.5, 3.5_

- [x] 20. Create comprehensive testing suite ✅

  - Build unit tests for all new authentication and database components
  - Create integration tests for multi-service interactions
  - Implement end-to-end testing for complete user workflows
  - Build performance testing and load testing procedures
  - Create migration testing and rollback validation
  - Implement security testing and vulnerability scanning
  - _Requirements: All requirements validation_

- [x] 21. Build administration and management interfaces ✅

  - Create web-based admin panel for user and system management
  - Build CLI tools for system administration and maintenance
  - Implement system health monitoring and diagnostic tools
  - Create user management interface for account administration
  - Build configuration management and service control interfaces
  - Implement log viewing and analysis tools
  - _Requirements: 5.3, 6.5, 12.3_

- [x] 22. Create documentation and deployment guides ✅

  - Write comprehensive installation and setup documentation
  - Create migration guide from existing Supabase-based installations
  - Build troubleshooting guide for common deployment issues
  - Create API documentation for all new local services
  - Write security best practices and hardening guide
  - Create backup and disaster recovery procedures documentation
  - _Requirements: All requirements implementation guidance_

- [x] 23. Implement final integration and testing
  - Integrate all components into cohesive self-hosted system
  - Perform comprehensive end-to-end testing of all functionality
  - Validate performance meets or exceeds current system capabilities
  - Test migration procedures with real Supabase data
  - Verify security measures and access controls function correctly
  - Create final deployment packages and release artifacts
  - _Requirements: All requirements final validation_

---

## Zippy Suna vs Kortix “core” Suna (mission)

**Kortix upstream** optimizes for their **hosted SaaS**: Supabase, Stripe / RevenueCat-style billing, cloud sandboxes (e.g. Daytona), Composio/MCP orchestration, analytics, and ops features tied to accounts they can meter and bill.

**Zippy Suna** targets **self-sovereign deployment**: **your** Postgres (+ pgvector), **local JWT auth** (no Supabase lock-in), **local or S3-compatible storage**, **Docker-based sandboxes**, **tier/credit limits you control** (no proprietary paywall backend), and **optional** local LLM / search — so the product is not dependent on Kortix’s metered services or their revenue stack.

---

## Upstream import rubric (only what makes Zippy better)

**Prefer importing (review each commit / path):**

- Agent runtime, tool calling, thread/message handling, prompts, sandbox safety fixes **that are not tied to cloud-only APIs**
- Frontend UX fixes (chat, canvas, attachments, accessibility) **where they do not assume Stripe/RevCat/Supabase-only flows**
- Backend bugfixes (Redis, workers, WebSockets) **without** pulling in hosted billing or Composio account plumbing
- Performance, security hardening, test improvements with **clear** benefit for self-hosted

**Do not merge wholesale:**

- Stripe / RevenueCat / subscription / “buy credits” cloud flows
- Supabase-specific or hosted-only auth/billing surfaces
- Composio/GitHub integration and other **account-mapped** cloud integrations unless explicitly adapted for local credentials
- Kubernetes/EKS/CI that belongs to Kortix infra, not your Proxmox/compose stack

**Mechanical blocker:** current `main` moved much of the backend under `backend/core/`. Zippy changes still live under the older layout. The first integration step is **port Zippy modules into the new tree** (or resolve rename conflicts once), **then** cherry-pick or merge **by subsystem** (e.g. `backend/core/agentpress`, `frontend/src` chat thread) with the rubric above.

- [ ] 24. Selective import from Kortix `main` onto Zippy

  - [ ] Map Zippy backend/services to `backend/core/` layout; keep local billing and remove cloud billing at boundaries
  - [ ] Merge or cherry-pick upstream subsystems one at a time (agent/thread/sandbox first), skipping billing/Stripe/RevCat paths
  - [ ] Re-apply local compose, env, and admin routes after each merge chunk
  - [ ] Run smoke tests (API + UI auth + one agent thread) on self-hosted compose
  - _Requirements: mission alignment — no mandatory third-party metered core_
