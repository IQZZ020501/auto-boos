"""页面选择器集中管理，方便维护与替换。"""

# 登录页
LOGIN_BUTTON_CSS = "[ka='header-login']"
APP_SCAN_SWITCH_CSS = ".switch-tip"
QRCODE_IMG_CSS = "img[src*='qrcode']"

# 左侧菜单：推荐牛人
RECOMMEND_TALENTS_SELECTORS = [
    ("css", "a[ka='menu-geek-recommend']"),
    ("xpath", "//div[contains(@class, 'menu-item-content') and contains(., '推荐牛人')]"),
    ("xpath", "//span[text()='推荐牛人']/.."),
    ("css", "a[href*='recommend']"),
]

# 牛人卡片（不同版本可能有差异，按从精确到宽松的顺序尝试）
CARD_SELECTOR_CANDIDATES = [
    "li.card-item div.card-inner[data-geekid]",
    "div.card-inner[data-geekid]",
    "[data-geekid]",
]

# 登录后“立即下载”弹层（用户提供的 XPath）
DOWNLOAD_LINK_XPATH = "/html/body/div[5]/div[1]/div[1]/div/div/a"
DOWNLOAD_CLOSE_ICON_XPATH = "/html/body/div[5]/div[1]/div[2]/i"
DOWNLOAD_CLOSE_ICON_CSS = "i.icon-close"

# 推荐牛人页：职位下拉（顶部职位选择器）
JOB_DROPDOWN_LABEL_CSS = ".job-selecter-wrap .ui-dropmenu-label"
JOB_ITEM_CURRENT_CSS = ".job-selecter-wrap .ui-dropmenu-list .job-list .job-item.curr"
JOB_ITEM_CSS = ".job-selecter-wrap .ui-dropmenu-list .job-list .job-item"

# 推荐牛人页主体 iframe
RECOMMEND_FRAME_CSS = "iframe[name='recommendFrame']"

# 推荐牛人页：城市关联区县选择
AREA_ENTRY_CSS = ".trade-entry-warp .trade-entry"
AREA_PANEL_CSS = ".trade-entry-warp .check-area-warp"
AREA_CITY_ITEM_XPATH_TEMPLATE = (
    "//div[contains(@class,'check-city-left')]"
    "//*[contains(@class,'area-item') and normalize-space()='{city}']"
)
AREA_DISTRICT_ITEM_XPATH_TEMPLATE = (
    "//div[contains(@class,'check-district-center')]"
    "//*[contains(@class,'area-item') and normalize-space()='{district}']"
)
AREA_CONFIRM_BUTTON_CSS = ".trade-entry-warp .check-area-bottom-right .confirm-btn"

# 推荐牛人页：筛选 + 是否应用上次筛选条件
FILTER_BUTTON_XPATH = "//div[contains(@class,'filter-label-wrap')][.//text()[contains(.,'筛选')]]"
RECOVER_LAST_FILTER_MODAL_CSS = ".recover-last-change-params"
RECOVER_LAST_FILTER_APPLY_CSS = ".recover-last-change-params .recover"

# 推荐牛人页：筛选面板确认按钮（不同版本文案可能为“确定/确认”）
FILTER_CONFIRM_BUTTON_XPATH_CANDIDATES = [
    "/html/body/div/div/div/div[1]/div/div/div/div/div[5]/div/div[2]/div[2]/div[2]",
    "//button[normalize-space()='确定']",
    "//button[normalize-space()='确认']",
    "//div[contains(@class,'filter') or contains(@class,'dialog') or contains(@class,'drawer')]//button[normalize-space()='确定']",
    "//div[contains(@class,'filter') or contains(@class,'dialog') or contains(@class,'drawer')]//button[normalize-space()='确认']",
]
