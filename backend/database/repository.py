"""
Repository pattern implementation for database operations
Provides high-level database operations replacing Supabase client methods
"""

from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
import bcrypt
import jwt
import secrets
from .models import (
    User, UserSession, UserTier, Project, Thread, Message,
    KnowledgeBase, UsageLog, ProjectCollaborator, SandboxInstance
)
from .connection import db_manager

class BaseRepository:
    """Base repository with common operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, model_class, id_value: UUID):
        """Get entity by ID"""
        result = await self.session.execute(
            select(model_class).where(model_class.id == id_value)
        )
        return result.scalar_one_or_none()
    
    async def create(self, entity):
        """Create new entity"""
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    async def update(self, entity):
        """Update existing entity"""
        await self.session.merge(entity)
        return entity
    
    async def delete(self, entity):
        """Delete entity"""
        await self.session.delete(entity)

class UserRepository(BaseRepository):
    """User management repository replacing Supabase auth operations"""
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, email: str, password: str, **kwargs) -> User:
        """Create new user with hashed password"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = User(
            email=email,
            password_hash=password_hash,
            **kwargs
        )
        
        return await self.create(user)
    
    async def verify_password(self, user: User, password: str) -> bool:
        """Verify user password"""
        return bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
    
    async def update_password(self, user: User, new_password: str):
        """Update user password"""
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password_hash = password_hash
        return await self.update(user)
    
    async def create_session(self, user: User, ip_address: str = None, user_agent: str = None) -> UserSession:
        """Create user session with JWT token"""
        # Generate tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        
        # Hash tokens for storage
        token_hash = bcrypt.hashpw(access_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        refresh_token_hash = bcrypt.hashpw(refresh_token.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create session
        session = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            refresh_expires_at=datetime.utcnow() + timedelta(days=30),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        await self.create(session)
        
        # Return tokens (not stored in plain text)
        session.access_token = access_token
        session.refresh_token = refresh_token
        
        return session
    
    async def get_session_by_token(self, token: str) -> Optional[UserSession]:
        """Get session by access token"""
        # Get all active sessions and verify token
        result = await self.session.execute(
            select(UserSession)
            .where(UserSession.expires_at > datetime.utcnow())
            .options(joinedload(UserSession.user))
        )
        
        sessions = result.scalars().all()
        
        for session in sessions:
            if bcrypt.checkpw(token.encode('utf-8'), session.token_hash.encode('utf-8')):
                # Update last used
                session.last_used_at = datetime.utcnow()
                await self.update(session)
                return session
        
        return None
    
    async def invalidate_session(self, session: UserSession):
        """Invalidate user session"""
        await self.delete(session)
    
    async def get_user_tier(self, tier_name: str) -> Optional[UserTier]:
        """Get user tier configuration"""
        result = await self.session.execute(
            select(UserTier).where(UserTier.name == tier_name)
        )
        return result.scalar_one_or_none()

class ProjectRepository(BaseRepository):
    """Project management repository"""
    
    async def get_user_projects(self, user_id: UUID, include_archived: bool = False) -> List[Project]:
        """Get all projects for a user"""
        query = select(Project).where(Project.user_id == user_id)
        
        if not include_archived:
            query = query.where(Project.status != 'archived')
        
        query = query.order_by(Project.last_accessed_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create_project(self, user_id: UUID, name: str, **kwargs) -> Project:
        """Create new project"""
        project = Project(
            user_id=user_id,
            name=name,
            **kwargs
        )
        
        return await self.create(project)
    
    async def get_project_with_threads(self, project_id: UUID) -> Optional[Project]:
        """Get project with threads loaded"""
        result = await self.session.execute(
            select(Project)
            .where(Project.project_id == project_id)
            .options(selectinload(Project.threads))
        )
        return result.scalar_one_or_none()
    
    async def update_last_accessed(self, project_id: UUID):
        """Update project last accessed timestamp"""
        await self.session.execute(
            update(Project)
            .where(Project.project_id == project_id)
            .values(last_accessed_at=datetime.utcnow())
        )

class ThreadRepository(BaseRepository):
    """Thread and message management repository"""
    
    async def create_thread(self, project_id: UUID, user_id: UUID, title: str = None) -> Thread:
        """Create new thread"""
        thread = Thread(
            project_id=project_id,
            user_id=user_id,
            title=title
        )
        
        return await self.create(thread)
    
    async def get_thread_with_messages(self, thread_id: UUID) -> Optional[Thread]:
        """Get thread with messages loaded"""
        result = await self.session.execute(
            select(Thread)
            .where(Thread.thread_id == thread_id)
            .options(selectinload(Thread.messages))
        )
        return result.scalar_one_or_none()
    
    async def add_message(self, thread_id: UUID, message_type: str, content: Dict[str, Any], **kwargs) -> Message:
        """Add message to thread"""
        message = Message(
            thread_id=thread_id,
            type=message_type,
            content=content,
            **kwargs
        )
        
        # Update thread last message timestamp
        await self.session.execute(
            update(Thread)
            .where(Thread.thread_id == thread_id)
            .values(last_message_at=datetime.utcnow())
        )
        
        return await self.create(message)
    
    async def get_recent_threads(self, user_id: UUID, limit: int = 10) -> List[Thread]:
        """Get recent threads for user"""
        result = await self.session.execute(
            select(Thread)
            .where(Thread.user_id == user_id)
            .where(Thread.is_archived == False)
            .order_by(Thread.last_message_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

class KnowledgeRepository(BaseRepository):
    """Knowledge base repository with vector search"""
    
    async def add_knowledge(self, content: str, embedding: List[float] = None, **kwargs) -> KnowledgeBase:
        """Add knowledge base entry"""
        knowledge = KnowledgeBase(
            content=content,
            embedding=embedding,
            **kwargs
        )
        
        return await self.create(knowledge)
    
    async def vector_search(self, query_embedding: List[float], user_id: UUID = None, 
                          project_id: UUID = None, limit: int = 10, 
                          similarity_threshold: float = 0.7) -> List[KnowledgeBase]:
        """Perform vector similarity search"""
        # Use the hybrid_search function from the database
        query = """
        SELECT * FROM hybrid_search($1, $2, $3, $4, $5, $6)
        """
        
        async with db_manager.get_connection() as conn:
            results = await conn.fetch(
                query, 
                "", # query_text (empty for pure vector search)
                query_embedding,
                user_id,
                project_id,
                limit,
                similarity_threshold
            )
        
        # Convert results to KnowledgeBase objects
        knowledge_entries = []
        for row in results:
            # Get full KnowledgeBase object
            result = await self.session.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == row['id'])
            )
            kb_entry = result.scalar_one_or_none()
            if kb_entry:
                # Add similarity score as attribute
                kb_entry.similarity_score = row['similarity_score']
                knowledge_entries.append(kb_entry)
        
        return knowledge_entries
    
    async def text_search(self, query: str, user_id: UUID = None, 
                         project_id: UUID = None, limit: int = 10) -> List[KnowledgeBase]:
        """Perform full-text search"""
        query_filter = select(KnowledgeBase).where(
            func.to_tsvector('english', KnowledgeBase.content).match(query)
        )
        
        if user_id:
            query_filter = query_filter.where(KnowledgeBase.user_id == user_id)
        if project_id:
            query_filter = query_filter.where(KnowledgeBase.project_id == project_id)
        
        query_filter = query_filter.limit(limit)
        
        result = await self.session.execute(query_filter)
        return result.scalars().all()

class UsageRepository(BaseRepository):
    """Usage tracking repository replacing Stripe billing"""
    
    async def log_usage(self, user_id: UUID, resource_type: str, amount: float, 
                       unit: str, cost: float = 0, **kwargs) -> UsageLog:
        """Log resource usage"""
        usage_log = UsageLog(
            user_id=user_id,
            resource_type=resource_type,
            amount=amount,
            unit=unit,
            cost=cost,
            **kwargs
        )
        
        return await self.create(usage_log)
    
    async def get_monthly_usage(self, user_id: UUID, year: int = None, 
                               month: int = None) -> Dict[str, float]:
        """Get monthly usage summary"""
        if not year:
            year = datetime.utcnow().year
        if not month:
            month = datetime.utcnow().month
        
        # Get usage from monthly_usage table
        query = """
        SELECT resource_type, total_amount, total_cost
        FROM monthly_usage
        WHERE user_id = $1 AND year = $2 AND month = $3
        """
        
        async with db_manager.get_connection() as conn:
            results = await conn.fetch(query, user_id, year, month)
        
        usage_summary = {}
        for row in results:
            usage_summary[row['resource_type']] = {
                'amount': float(row['total_amount']),
                'cost': float(row['total_cost'])
            }
        
        return usage_summary
    
    async def check_usage_limits(self, user_id: UUID, resource_type: str, 
                                requested_amount: float) -> bool:
        """Check if user can use requested amount without exceeding limits"""
        query = "SELECT check_user_limits($1, $2, $3)"
        
        async with db_manager.get_connection() as conn:
            result = await conn.fetchval(query, user_id, resource_type, requested_amount)
        
        return result

# Repository factory for dependency injection
class RepositoryFactory:
    """Factory for creating repository instances"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @property
    def users(self) -> UserRepository:
        return UserRepository(self.session)
    
    @property
    def projects(self) -> ProjectRepository:
        return ProjectRepository(self.session)
    
    @property
    def threads(self) -> ThreadRepository:
        return ThreadRepository(self.session)
    
    @property
    def knowledge(self) -> KnowledgeRepository:
        return KnowledgeRepository(self.session)
    
    @property
    def usage(self) -> UsageRepository:
        return UsageRepository(self.session)

# FastAPI dependency
async def get_repositories(session: AsyncSession = None) -> RepositoryFactory:
    """Get repository factory for FastAPI dependency injection"""
    if session is None:
        async with db_manager.get_session() as session:
            yield RepositoryFactory(session)
    else:
        yield RepositoryFactory(session)