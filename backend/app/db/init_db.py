import logging

from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


def init_db() -> None:
    logger.info("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
