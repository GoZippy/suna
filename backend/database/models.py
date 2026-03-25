"""
SQLAlchemy models for Suna database
Replaces Supabase table definitions with local models
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, 
    ForeignKey, DECIMAL, ARRAY, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .connection import Base

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class User(Base, TimestampMixin):
    """User model replacing Supabase auth.users"""
    __tablename__ = 'users'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default='user')
    tier: Mapped[str] = mapped_column(String(50), default='free')
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255))
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255))
    password_reset_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    credit_balance: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.00)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    threads = relationship("Thread", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
        Index('idx_users_tier', 'tier'),
    )

class UserSession(Base, TimestampMixin):
    """User session model for JWT token management"""
    __tablename__ = 'user_sessions'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_user_sessions_user_id', 'user_id'),
        Index('idx_user_sessions_token_hash', 'token_hash'),
        Index('idx_user_sessions_expires_at', 'expires_at'),
    )

class UserTier(Base, TimestampMixin):
    """User tier configuration model"""
    __tablename__ = 'user_tiers'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_monthly_usage: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2))
    max_concurrent_agents: Mapped[int] = mapped_column(Integer, default=1)
    max_projects: Mapped[int] = mapped_column(Integer, default=10)
    max_storage_gb: Mapped[int] = mapped_column(Integer, default=5)
    features: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

class Project(Base, TimestampMixin):
    """Project model replacing Supabase projects"""
    __tablename__ = 'projects'
    
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default='active')
    sandbox_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    repository_url: Mapped[Optional[str]] = mapped_column(String(500))
    branch: Mapped[str] = mapped_column(String(100), default='main')
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="projects")
    threads = relationship("Thread", back_populates="project", cascade="all, delete-orphan")
    collaborators = relationship("ProjectCollaborator", back_populates="project", cascade="all, delete-orphan")
    sandbox_instances = relationship("SandboxInstance", back_populates="project", cascade="all, delete-orphan")
    knowledge_entries = relationship("KnowledgeBase", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_projects_user_id', 'user_id'),
        Index('idx_projects_status', 'status'),
        Index('idx_projects_created_at', 'created_at'),
        Index('idx_projects_last_accessed_at', 'last_accessed_at'),
    )

class Thread(Base, TimestampMixin):
    """Thread model for conversations"""
    __tablename__ = 'threads'
    
    thread_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('projects.project_id', ondelete='CASCADE'))
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    project = relationship("Project", back_populates="threads")
    user = relationship("User", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_threads_project_id', 'project_id'),
        Index('idx_threads_user_id', 'user_id'),
        Index('idx_threads_created_at', 'created_at'),
        Index('idx_threads_last_message_at', 'last_message_at'),
    )

class Message(Base):
    """Message model for thread conversations"""
    __tablename__ = 'messages'
    
    message_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('threads.thread_id', ondelete='CASCADE'))
    parent_message_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('messages.message_id'))
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(50))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(DECIMAL(10, 6), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
    parent_message = relationship("Message", remote_side="Message.message_id")
    
    __table_args__ = (
        Index('idx_messages_thread_id', 'thread_id'),
        Index('idx_messages_parent_message_id', 'parent_message_id'),
        Index('idx_messages_type', 'type'),
        Index('idx_messages_created_at', 'created_at'),
    )

class KnowledgeBase(Base, TimestampMixin):
    """Knowledge base model with vector embeddings"""
    __tablename__ = 'knowledge_base'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    project_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('projects.project_id', ondelete='CASCADE'))
    title: Mapped[Optional[str]] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default='text')
    source_url: Mapped[Optional[str]] = mapped_column(String(1000))
    source_type: Mapped[Optional[str]] = mapped_column(String(50))
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536))
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=1)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User")
    project = relationship("Project", back_populates="knowledge_entries")
    
    __table_args__ = (
        Index('idx_knowledge_base_user_id', 'user_id'),
        Index('idx_knowledge_base_project_id', 'project_id'),
        Index('idx_knowledge_base_content_type', 'content_type'),
        Index('idx_knowledge_base_source_type', 'source_type'),
        Index('idx_knowledge_base_created_at', 'created_at'),
        Index('idx_knowledge_base_file_hash', 'file_hash'),
    )

class UsageLog(Base):
    """Usage tracking model replacing Stripe billing"""
    __tablename__ = 'usage_logs'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    project_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('projects.project_id', ondelete='CASCADE'))
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_subtype: Mapped[Optional[str]] = mapped_column(String(50))
    amount: Mapped[float] = mapped_column(DECIMAL(15, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    cost: Mapped[float] = mapped_column(DECIMAL(10, 6), default=0)
    provider: Mapped[Optional[str]] = mapped_column(String(50))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")
    project = relationship("Project")
    
    __table_args__ = (
        Index('idx_usage_logs_user_id', 'user_id'),
        Index('idx_usage_logs_project_id', 'project_id'),
        Index('idx_usage_logs_resource_type', 'resource_type'),
        Index('idx_usage_logs_created_at', 'created_at'),
        Index('idx_usage_logs_user_created', 'user_id', 'created_at'),
    )

class CreditTransaction(Base):
    """Credit transaction model for tracking credit purchases and usage"""
    __tablename__ = 'credit_transactions'

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'purchase', 'usage', 'grant', 'refund'
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    balance_before: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    balance_after: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(255))  # Could reference usage_log or purchase ID
    description: Mapped[Optional[str]] = mapped_column(Text)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index('idx_credit_transactions_user_id', 'user_id'),
        Index('idx_credit_transactions_type', 'transaction_type'),
        Index('idx_credit_transactions_created_at', 'created_at'),
        Index('idx_credit_transactions_user_type', 'user_id', 'transaction_type'),
    )

class ProjectCollaborator(Base):
    """Project collaborator model for shared access"""
    __tablename__ = 'project_collaborators'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('projects.project_id', ondelete='CASCADE'))
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    role: Mapped[str] = mapped_column(String(50), default='viewer')
    invited_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    project = relationship("Project", back_populates="collaborators")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])
    
    __table_args__ = (
        UniqueConstraint('project_id', 'user_id'),
        Index('idx_project_collaborators_project_id', 'project_id'),
        Index('idx_project_collaborators_user_id', 'user_id'),
    )

class SandboxInstance(Base, TimestampMixin):
    """Sandbox instance model for container management"""
    __tablename__ = 'sandbox_instances'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('projects.project_id', ondelete='CASCADE'))
    container_id: Mapped[Optional[str]] = mapped_column(String(255))
    container_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default='creating')
    port_mappings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    resource_limits: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    project = relationship("Project", back_populates="sandbox_instances")
    
    __table_args__ = (
        Index('idx_sandbox_instances_project_id', 'project_id'),
        Index('idx_sandbox_instances_status', 'status'),
        Index('idx_sandbox_instances_container_id', 'container_id'),
    )

class WorkerNode(Base, TimestampMixin):
    """Worker node model for tracking worker instances"""
    __tablename__ = 'worker_nodes'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    worker_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    status: Mapped[str] = mapped_column(String(50), default='active')  # active, inactive, offline
    process_count: Mapped[int] = mapped_column(Integer, default=0)
    thread_count: Mapped[int] = mapped_column(Integer, default=0)
    current_load: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00)  # percentage
    memory_usage: Mapped[Optional[int]] = mapped_column(Integer)  # bytes
    cpu_usage: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 2))  # percentage
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index('idx_worker_nodes_worker_id', 'worker_id'),
        Index('idx_worker_nodes_status', 'status'),
        Index('idx_worker_nodes_last_heartbeat', 'last_heartbeat'),
        Index('idx_worker_nodes_status_heartbeat', 'status', 'last_heartbeat'),
    )

class WebSocketConnection(Base, TimestampMixin):
    """WebSocket connection model for tracking persistent connections"""
    __tablename__ = 'websocket_connections'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    session_id: Mapped[Optional[str]] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default='connected')  # connected, disconnected, expired
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    disconnected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    subscriptions: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)  # Store thread/project/agent subscriptions
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User", backref="websocket_connections")
    
    __table_args__ = (
        Index('idx_websocket_connections_connection_id', 'connection_id'),
        Index('idx_websocket_connections_user_id', 'user_id'),
        Index('idx_websocket_connections_status', 'status'),
        Index('idx_websocket_connections_last_activity', 'last_activity'),
        Index('idx_websocket_connections_connected_at', 'connected_at'),
    )

class FileStorage(Base, TimestampMixin):
    """File storage model for managing uploaded files"""
    __tablename__ = 'file_storage'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    file_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    project_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('projects.project_id', ondelete='CASCADE'))
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 hash
    status: Mapped[str] = mapped_column(String(50), default='active')  # active, deleted, archived
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    last_downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User", backref="files")
    project = relationship("Project", backref="files")
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")
    shares = relationship("FileShare", back_populates="file", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_file_storage_file_id', 'file_id'),
        Index('idx_file_storage_user_id', 'user_id'),
        Index('idx_file_storage_project_id', 'project_id'),
        Index('idx_file_storage_file_hash', 'file_hash'),
        Index('idx_file_storage_status', 'status'),
        Index('idx_file_storage_content_type', 'content_type'),
    )

class FileVersion(Base, TimestampMixin):
    """File version model for versioning support"""
    __tablename__ = 'file_versions'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    file_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('file_storage.id', ondelete='CASCADE'))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    change_description: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    
    # Relationships
    file = relationship("FileStorage", back_populates="versions")
    creator = relationship("User")
    
    __table_args__ = (
        Index('idx_file_versions_file_id', 'file_id'),
        Index('idx_file_versions_version_number', 'version_number'),
        UniqueConstraint('file_id', 'version_number', name='uq_file_version'),
    )

class FileShare(Base, TimestampMixin):
    """File sharing model for permission management"""
    __tablename__ = 'file_shares'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    file_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('file_storage.id', ondelete='CASCADE'))
    shared_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    shared_with: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    share_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    permissions: Mapped[str] = mapped_column(String(50), default='read')  # read, write, admin
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    file = relationship("FileStorage", back_populates="shares")
    sharer = relationship("User", foreign_keys=[shared_by])
    recipient = relationship("User", foreign_keys=[shared_with])
    
    __table_args__ = (
        Index('idx_file_shares_file_id', 'file_id'),
        Index('idx_file_shares_shared_by', 'shared_by'),
        Index('idx_file_shares_shared_with', 'shared_with'),
        Index('idx_file_shares_share_token', 'share_token'),
        Index('idx_file_shares_expires_at', 'expires_at'),
    )

class FileBackup(Base, TimestampMixin):
    """File backup model for backup management"""
    __tablename__ = 'file_backups'
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    file_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('file_storage.id', ondelete='CASCADE'))
    backup_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    backup_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    backup_size: Mapped[int] = mapped_column(Integer, nullable=False)
    backup_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    backup_type: Mapped[str] = mapped_column(String(50), default='manual')  # manual, scheduled, version
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    
    # Relationships
    file = relationship("FileStorage")
    creator = relationship("User")
    
    __table_args__ = (
        Index('idx_file_backups_file_id', 'file_id'),
        Index('idx_file_backups_backup_type', 'backup_type'),
        Index('idx_file_backups_created_at', 'created_at'),
    )