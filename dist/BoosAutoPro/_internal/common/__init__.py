"""通用工具模块（与具体业务页面无关的公共能力）。"""

from .cookie_store import load_cookies, save_cookies, sanitize_cookie
from .logger_config import setup_logging
