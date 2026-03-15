from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app import crud
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_old_links():
    """Фоновая задача для удаления старых ссылок"""
    db = SessionLocal()
    try:
        deleted = crud.delete_old_unused_links(db, days=30)
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old unused links")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    finally:
        db.close()

def start_scheduler():
    """Запускает планировщик фоновых задач"""
    scheduler = BackgroundScheduler()
    # Запускаем каждый день в 3:00 утра
    scheduler.add_job(cleanup_old_links, 'cron', hour=3, minute=0)
    scheduler.start()
    logger.info("Scheduler started - will cleanup old links daily at 3:00 AM")
    return scheduler
