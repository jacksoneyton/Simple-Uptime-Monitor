"""
Database models and initialization using SQLAlchemy.
"""

from datetime import datetime, date
from typing import Optional
import json
import logging
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Date, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session, scoped_session
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

Base = declarative_base()


class MonitorModel(Base):
    """Monitor configuration cache"""
    __tablename__ = 'monitors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    type = Column(String(50), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    group_name = Column(String(255), index=True)
    interval = Column(Integer)  # seconds
    timeout = Column(Integer)
    retry_count = Column(Integer)
    config = Column(JSON)  # Full monitor configuration as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    check_results = relationship("CheckResult", back_populates="monitor", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="monitor", cascade="all, delete-orphan")
    push_monitor = relationship("PushMonitor", back_populates="monitor", uselist=False, cascade="all, delete-orphan")
    ssl_certificates = relationship("SSLCertificate", back_populates="monitor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MonitorModel(id={self.id}, name='{self.name}', type='{self.type}', enabled={self.enabled})>"


class CheckResult(Base):
    """Individual check results (ping history)"""
    __tablename__ = 'check_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # up, down, degraded
    response_time = Column(Float)  # milliseconds
    status_code = Column(Integer)
    error_message = Column(Text)
    check_metadata = Column(JSON)  # Renamed from 'metadata' to avoid SQLAlchemy conflict

    # Relationship
    monitor = relationship("MonitorModel", back_populates="check_results")

    __table_args__ = (
        Index('idx_check_results_monitor_timestamp', 'monitor_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<CheckResult(id={self.id}, monitor_id={self.monitor_id}, status='{self.status}', timestamp={self.timestamp})>"


class Incident(Base):
    """Downtime incident tracking"""
    __tablename__ = 'incidents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, index=True)
    duration = Column(Integer)  # seconds (calculated when ended)
    trigger_check_id = Column(Integer, ForeignKey('check_results.id'))
    resolution_check_id = Column(Integer, ForeignKey('check_results.id'))
    notified = Column(Boolean, default=False)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(255))
    acknowledged_at = Column(DateTime)
    notes = Column(Text)

    # Relationships
    monitor = relationship("MonitorModel", back_populates="incidents")
    notifications_log = relationship("NotificationLog", back_populates="incident", cascade="all, delete-orphan")

    @property
    def is_ongoing(self) -> bool:
        """Check if incident is still ongoing"""
        return self.ended_at is None

    @property
    def duration_seconds(self) -> Optional[int]:
        """Get incident duration in seconds"""
        if self.duration:
            return self.duration
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        if self.started_at:
            return int((datetime.utcnow() - self.started_at).total_seconds())
        return None

    def __repr__(self):
        status = "ongoing" if self.is_ongoing else "resolved"
        return f"<Incident(id={self.id}, monitor_id={self.monitor_id}, status='{status}')>"


class NotificationLog(Base):
    """Notification audit trail"""
    __tablename__ = 'notifications_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey('incidents.id', ondelete='CASCADE'), index=True)
    monitor_id = Column(Integer, ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)  # email, discord, slack
    notification_name = Column(String(255), nullable=False)
    event_type = Column(String(50), nullable=False)  # down, up, ssl_expire
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Relationship
    incident = relationship("Incident", back_populates="notifications_log")

    def __repr__(self):
        status = "success" if self.success else "failed"
        return f"<NotificationLog(id={self.id}, type='{self.notification_type}', status='{status}')>"


class PushMonitor(Base):
    """Push-based monitor tracking"""
    __tablename__ = 'push_monitors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False, unique=True)
    secret_key = Column(String(255), nullable=False, unique=True)
    last_push_at = Column(DateTime)
    expected_interval = Column(Integer, nullable=False)  # seconds
    grace_period = Column(Integer, default=0)
    next_expected_at = Column(DateTime, index=True)

    # Relationship
    monitor = relationship("MonitorModel", back_populates="push_monitor")

    @property
    def is_overdue(self) -> bool:
        """Check if push is overdue"""
        if not self.next_expected_at:
            return False
        return datetime.utcnow() > self.next_expected_at

    def __repr__(self):
        return f"<PushMonitor(id={self.id}, monitor_id={self.monitor_id}, overdue={self.is_overdue})>"


class UptimeStats(Base):
    """Aggregated uptime statistics"""
    __tablename__ = 'uptime_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    total_checks = Column(Integer, default=0)
    successful_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    uptime_percentage = Column(Float)  # 0-100
    avg_response_time = Column(Float)  # milliseconds
    max_response_time = Column(Float)
    min_response_time = Column(Float)

    __table_args__ = (
        Index('idx_uptime_stats_monitor_date', 'monitor_id', 'date', unique=True),
    )

    def __repr__(self):
        return f"<UptimeStats(monitor_id={self.monitor_id}, date={self.date}, uptime={self.uptime_percentage}%)>"


class SSLCertificate(Base):
    """SSL certificate tracking"""
    __tablename__ = 'ssl_certificates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False)
    hostname = Column(String(255), nullable=False)
    issued_to = Column(String(255))
    issued_by = Column(String(255))
    valid_from = Column(DateTime)
    valid_until = Column(DateTime, index=True)
    days_remaining = Column(Integer)
    last_checked = Column(DateTime, default=datetime.utcnow)

    # Relationship
    monitor = relationship("MonitorModel", back_populates="ssl_certificates")

    @property
    def is_expiring_soon(self, days: int = 30) -> bool:
        """Check if certificate is expiring within specified days"""
        return self.days_remaining is not None and self.days_remaining <= days

    def __repr__(self):
        return f"<SSLCertificate(hostname='{self.hostname}', days_remaining={self.days_remaining})>"


class Database:
    """Database manager"""

    def __init__(self, database_url: str = "sqlite:///data/uptime.db"):
        """
        Initialize database.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url

        # Configure engine
        if database_url.startswith('sqlite'):
            # SQLite-specific configuration for thread safety
            self.engine = create_engine(
                database_url,
                connect_args={
                    'check_same_thread': False,
                    'timeout': 30  # 30 second timeout for locks
                },
                poolclass=NullPool,  # No connection pooling for SQLite
                echo=False
            )
        else:
            self.engine = create_engine(database_url)

        # Use scoped_session for thread-safe session management
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.SessionLocal = scoped_session(session_factory)

    def init_db(self) -> None:
        """Initialize database tables"""
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    def get_session(self) -> Session:
        """Get a thread-local database session"""
        return self.SessionLocal()

    def remove_session(self) -> None:
        """Remove the current thread's session"""
        self.SessionLocal.remove()

    def drop_all(self) -> None:
        """Drop all tables (use with caution!)"""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All tables dropped")


# Global database instance
_db: Optional[Database] = None


def init_database(database_url: str = "sqlite:///data/uptime.db") -> Database:
    """
    Initialize the global database instance.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        Database instance
    """
    global _db
    _db = Database(database_url)
    _db.init_db()
    return _db


def get_database() -> Database:
    """
    Get the global database instance.

    Returns:
        Database instance

    Raises:
        RuntimeError: If database has not been initialized
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


def get_session() -> Session:
    """
    Get a new database session.

    Returns:
        SQLAlchemy Session

    Raises:
        RuntimeError: If database has not been initialized
    """
    return get_database().get_session()


# CLI for database management
if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == '--init':
        # Initialize database
        db_path = sys.argv[2] if len(sys.argv) > 2 else "data/uptime.db"
        db_url = f"sqlite:///{db_path}"
        logger.info(f"Initializing database at {db_url}")
        init_database(db_url)
        logger.info("Database initialized successfully")
    else:
        print("Usage: python -m uptime_monitor.database --init [database_path]")
        print("Example: python -m uptime_monitor.database --init data/uptime.db")
