import logging
from pipline import run
# 获取 httpx 的日志记录器
httpx_logger = logging.getLogger('httpx')
# 将 httpx 的日志级别设置为 WARNING，这样 INFO 级别的日志就不会输出
httpx_logger.setLevel(logging.WARNING)
api_request_logger=logging.getLogger('api_request')
api_request_logger.setLevel(logging.WARNING)
run()