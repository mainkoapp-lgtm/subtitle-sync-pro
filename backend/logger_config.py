import logging
import os
from datetime import datetime

def setup_logger():
    # Windows AppData 경로 설정
    app_data = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SubtitleSyncPro')
    log_dir = os.path.join(app_data, 'logs')
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"sync_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 로거 생성
    logger = logging.getLogger('SubtitleSync')
    logger.setLevel(logging.DEBUG)
    
    # 기존 핸들러 제거 (중복 방지)
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_fmt)
    
    # 스트림 핸들러 (콘솔 출력)
    stream_handler = logging.StreamHandler()
    stream_fmt = logging.Formatter('%(levelname)s: %(message)s')
    stream_handler.setFormatter(stream_fmt)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger, log_file

logger, LOG_FILE_PATH = setup_logger()
