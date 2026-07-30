"""Log Manager - Handle logging and periodic cleanup."""

import os
import time
from datetime import datetime
from typing import Optional


class LogManager:
    """Manage logs with periodic cleanup."""
    
    def __init__(self, log_dir: str = "logs", cleanup_interval_hours: float = 1.0):
        """Initialize log manager.
        
        Args:
            log_dir: Directory to store logs
            cleanup_interval_hours: Hours between cleanups (default 1 hour)
        """
        self.log_dir = log_dir
        self.cleanup_interval_seconds = cleanup_interval_hours * 3600
        self.last_cleanup_time = time.time()
        
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
    
    def get_current_log_file(self) -> str:
        """Get current log file path.
        
        Returns:
            Path to current log file
        """
        now = datetime.now()
        filename = f"passive_read_{now.strftime('%Y%m%d_%H%M%S')}.log"
        return os.path.join(self.log_dir, filename)
    
    def log_ocr_data(self, text: str, engine: str = "Unknown") -> bool:
        """Log OCR data to file.
        
        Args:
            text: OCR text to log
            engine: OCR engine used
            
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            log_file = self.get_current_log_file()
            
            with open(log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Tới mili giây
                f.write(f"[{timestamp}] Engine: {engine}\n")
                f.write(f"Text: {text}\n")
                f.write("-" * 80 + "\n")
            
            return True
        except Exception as e:
            print(f"[LogManager] Error logging OCR data: {e}")
            return False
    
    def should_cleanup(self) -> bool:
        """Check if cleanup should be performed.
        
        Returns:
            True if cleanup interval has passed, False otherwise
        """
        current_time = time.time()
        return (current_time - self.last_cleanup_time) >= self.cleanup_interval_seconds
    
    def cleanup_old_logs(self) -> int:
        """Delete all log files.
        
        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            
            if not os.path.exists(self.log_dir):
                return 0
            
            for filename in os.listdir(self.log_dir):
                if filename.endswith(".log"):
                    file_path = os.path.join(self.log_dir, filename)
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"[LogManager] Error deleting {filename}: {e}")
            
            self.last_cleanup_time = time.time()
            return deleted_count
        except Exception as e:
            print(f"[LogManager] Error during cleanup: {e}")
            return 0
    
    def check_and_cleanup(self) -> Optional[int]:
        """Check if cleanup is needed and perform it.
        
        Returns:
            Number of files deleted if cleanup was performed, None otherwise
        """
        if self.should_cleanup():
            deleted = self.cleanup_old_logs()
            print(f"[LogManager] Cleanup performed: deleted {deleted} log files")
            return deleted
        return None
