import pytest
from unittest.mock import MagicMock, patch
from app.tasks import cleanup_old_links, start_scheduler

def test_cleanup_old_links(mocker):
    """Тест функции очистки старых ссылок"""
    mock_db = mocker.patch('app.tasks.SessionLocal')
    mock_crud = mocker.patch('app.tasks.crud')
    mock_crud.delete_old_unused_links.return_value = 5
    
    cleanup_old_links()
    
    mock_crud.delete_old_unused_links.assert_called_once()
    mock_db.return_value.close.assert_called_once()

def test_cleanup_old_links_error(mocker):
    """Тест ошибки при очистке"""
    mock_db = mocker.patch('app.tasks.SessionLocal')
    mock_crud = mocker.patch('app.tasks.crud')
    mock_crud.delete_old_unused_links.side_effect = Exception("DB Error")
    
    # Не должна падать, должна логировать ошибку
    cleanup_old_links()
    
    mock_db.return_value.close.assert_called_once()

@patch('app.tasks.BackgroundScheduler')
def test_start_scheduler(mock_scheduler):
    """Тест запуска планировщика"""
    scheduler_instance = MagicMock()
    mock_scheduler.return_value = scheduler_instance
    
    result = start_scheduler()
    
    assert result == scheduler_instance
    scheduler_instance.add_job.assert_called_once()
    scheduler_instance.start.assert_called_once()
