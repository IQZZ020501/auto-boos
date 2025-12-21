import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('boos_auto.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BoosDriver:
    def __init__(self):
        self.driver = webdriver.Edge()

    def _find_cards_in_current_context(self, selector: str):
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            return []

    def _find_cards_any_frame(self, selector: str):
        """在主文档及所有 iframe 中查找卡片元素，返回 (frame_element_or_None, elements)。"""
        # 先在主文档查
        self.driver.switch_to.default_content()
        elements = self._find_cards_in_current_context(selector)
        if elements:
            return None, elements

        # 再遍历 iframe
        frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe")
        for frame in frames:
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                elements = self._find_cards_in_current_context(selector)
                if elements:
                    return frame, elements
            except Exception:
                continue

        self.driver.switch_to.default_content()
        return None, []

    def _safe_click(self, element, timeout: int = 10):
        """尽量可靠地点击元素：滚动到可视区、等待可点击、优先原生点击，失败再用 JS 点击。"""
        wait = WebDriverWait(self.driver, timeout)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        wait.until(lambda d: element.is_displayed())

        try:
            ActionChains(self.driver).move_to_element(element).pause(0.1).perform()
        except Exception:
            pass

        try:
            wait.until(EC.element_to_be_clickable(element))
        except Exception:
            # 某些场景 element_to_be_clickable 不接受 WebElement，会抛异常；忽略即可
            pass

        try:
            element.click()
            return
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)

    def _click_login(self):
        logger.info("开始执行登录流程")
        self.driver.maximize_window()
        self.driver.implicitly_wait(10)
        logger.info("正在打开BOSS直聘网站...")
        self.driver.get("https://www.zhipin.com/")
        logger.info("网站加载完成")

        # 等待登录按钮加载完成并可点击
        logger.info("等待登录按钮加载...")
        wait = WebDriverWait(self.driver, 10)
        login_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[ka='header-login']"))
        )
        logger.info("登录按钮已加载，准备点击")
        login_btn.click()
        logger.info("已点击登录按钮")

    def _click_app_scan_login(self):
        """点击APP扫码登录"""
        logger.info("等待APP扫码登录按钮加载...")
        # 等待APP扫码登录按钮加载完成并可点击
        wait = WebDriverWait(self.driver, 10)
        app_scan_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".switch-tip"))
        )
        logger.info("APP扫码登录按钮已加载，准备点击")
        app_scan_btn.click()
        logger.info("已点击APP扫码登录按钮")

    def _get_qrcode(self):
        logger.info("等待二维码图片加载...")
        # 等待二维码图片加载完成并可见
        wait = WebDriverWait(self.driver, 20)
        qr_code = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "img[src*='qrcode']"))
        )
        logger.info("二维码图片已显示")

        # 额外等待确保图片完全渲染（等待元素有宽度）
        logger.info("等待二维码图片完全渲染...")
        wait.until(lambda driver: qr_code.size['width'] > 0 and qr_code.size['height'] > 0)
        logger.info("二维码图片渲染完成")

        qr_code_url = qr_code.get_attribute("src")
        qr_code.screenshot("qr_code.png")
        logger.info(f"二维码URL: {qr_code_url}")
        logger.info("二维码已保存为 'qr_code.png'")

    def _click_recommend_talents(self):
        """点击推荐牛人"""
        logger.info("准备点击推荐牛人按钮")
        # 等待推荐牛人按钮加载完成并可点击
        wait = WebDriverWait(self.driver, 10)

        # 尝试多种选择器以确保能找到推荐牛人元素
        selectors = [
            "a[ka='menu-geek-recommend']",
            "//div[contains(@class, 'menu-item-content') and contains(., '推荐牛人')]",
            "//span[text()='推荐牛人']/..",
            "a[href*='recommend']",
        ]

        recommend_btn = None
        for selector in selectors:
            try:
                logger.debug(f"尝试使用选择器: {selector}")
                if selector.startswith("//"):
                    recommend_btn = wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    recommend_btn = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                logger.info(f"成功找到推荐牛人按钮，使用选择器: {selector}")
                print(f"找到推荐牛人按钮，使用选择器: {selector}")
                break
            except Exception as e:
                logger.debug(f"选择器 {selector} 未找到元素，继续尝试下一个")
                continue

        if recommend_btn:
            recommend_btn.click()
            logger.info("成功点击推荐牛人按钮")
            print("成功点击推荐牛人按钮！")
        else:
            logger.error("未能找到推荐牛人按钮")
            print("未能找到推荐牛人按钮")

    def _click_talent_cards(self):
        """点击牛人名片获取详细信息"""
        logger.info("准备点击牛人名片")
        wait = WebDriverWait(self.driver, 25)

        # 你提供的结构里关键是 data-geekid；common-wrap/外层容器在不同版本可能会变
        card_selector_candidates = [
            "li.card-item div.card-inner[data-geekid]",
            "div.card-inner[data-geekid]",
            "[data-geekid]",
        ]

        try:
            logger.info(f"当前URL: {self.driver.current_url}")
            try:
                logger.info(f"当前标题: {self.driver.title}")
            except Exception:
                pass

            logger.info("等待牛人卡片列表加载（主文档/iframe）...")

            found_frame = None
            cards = []

            def locate_cards(d):
                nonlocal found_frame, cards
                for selector in card_selector_candidates:
                    frame, els = self._find_cards_any_frame(selector)
                    if els:
                        found_frame = frame
                        cards = els
                        return True
                return False

            wait.until(locate_cards)

            # 过滤可见元素（虚拟列表/懒加载可能会导致部分不可见）
            visible_cards = [c for c in cards if c.is_displayed()]
            if visible_cards:
                cards = visible_cards

            logger.info(f"找到 {len(cards)} 个牛人卡片，准备点击第一个")
            print(f"找到 {len(cards)} 个牛人卡片")

            before_handles = set(self.driver.window_handles)
            before_url = self.driver.current_url

            first_card = cards[0]
            geek_id = first_card.get_attribute("data-geekid")
            logger.info(f"即将点击牛人卡片 data-geekid={geek_id}")

            self._safe_click(first_card)
            logger.info("已触发点击，等待打开详情...")

            def detail_opened(d):
                # 1) 新窗口/新标签页
                if len(d.window_handles) > len(before_handles):
                    return "new_window"
                # 2) SPA 路由变化
                if d.current_url != before_url:
                    return "url_changed"
                # 3) 详情面板（类名可能变化，这里用较宽松的 contains）
                panel_css_candidates = [
                    "[class*='detail']",
                    "[class*='resume']",
                    "[class*='geek'] [class*='detail']",
                ]
                for css in panel_css_candidates:
                    try:
                        if d.find_elements(By.CSS_SELECTOR, css):
                            return "panel"
                    except Exception:
                        continue
                return False

            try:
                opened_mode = WebDriverWait(self.driver, 8).until(detail_opened)
            except TimeoutException:
                opened_mode = None

            # 若打开了新窗口，则切换到新窗口
            after_handles = set(self.driver.window_handles)
            new_handles = list(after_handles - before_handles)
            if new_handles:
                self.driver.switch_to.window(new_handles[0])
                logger.info("检测到新窗口已打开，已切换到详情窗口")
                print("检测到新窗口已打开，已切换到详情窗口")
            elif opened_mode in {"url_changed", "panel"}:
                logger.info(f"检测到详情已打开（方式={opened_mode}），当前URL={self.driver.current_url}")
                print("检测到详情已打开")
            else:
                logger.warning("点击后未检测到详情打开（可能点到了非可点击区域/被遮挡/站点拦截），建议提高选择器精确度或查看页面是否实际发生变化")
                print("点击后未检测到详情打开（可能点到了非可点击区域/被遮挡/站点拦截）")

        except Exception as e:
            try:
                logger.error(f"点击牛人卡片失败时URL: {self.driver.current_url}")
                logger.error(f"点击牛人卡片失败时标题: {self.driver.title}")
                self.driver.save_screenshot("debug_click_card_timeout.png")
                logger.error("已保存截图 debug_click_card_timeout.png 便于排查")
            except Exception:
                pass
            logger.error(f"点击牛人卡片流程出错: {str(e)}", exc_info=True)
            print(f"点击牛人卡片流程出错: {str(e)}")
        finally:
            # 避免后续操作卡在 iframe 上下文
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass

    def login(self):
        logger.info("=" * 50)
        logger.info("开始BOSS直聘自动登录流程")
        logger.info("=" * 50)

        self._click_login()
        self._click_app_scan_login()
        self._get_qrcode()

        print("\n请使用手机APP扫描二维码并完成登录，登录成功后按回车键继续...")
        logger.info("等待用户扫码登录...")
        input("扫码登录完成后，按回车键继续...")
        logger.info("用户确认登录完成")

        # 登录成功后点击推荐牛人
        self._click_recommend_talents()

        # 点击牛人名片获取详细信息
        self._click_talent_cards()

        input("点击回车结束程序...")
        logger.info("登录流程全部完成")

    def close(self):
        logger.info("正在关闭浏览器...")
        self.driver.quit()
        logger.info("浏览器已关闭")


if __name__ == '__main__':
    logger.info("程序启动")
    boos_driver = BoosDriver()
    try:
        boos_driver.login()
        logger.info("程序执行成功")
        print("\n程序执行成功！")
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}", exc_info=True)
        print(f"\n程序执行出错: {str(e)}")
    finally:
        boos_driver.close()
        logger.info("程序结束")
        print("\n程序已结束")
