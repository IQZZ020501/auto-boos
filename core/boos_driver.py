import logging
import os
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common.cookie_store import load_cookies, sanitize_cookie, save_cookies
from core import selectors


class BoosDriver:
    def __init__(
            self,
            logger: logging.Logger | None = None,
            driver=None,
            cookie_path: str = "cookies.json",
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.driver = driver or webdriver.Edge()
        self.cookie_path = cookie_path

    def _has_recommend_talents_menu(self, timeout_seconds: int = 3) -> bool:
        """判断是否已进入登录后的工作台：能找到“推荐牛人”入口即可认为登录成功。"""
        wait = WebDriverWait(self.driver, timeout_seconds)

        def found(_):
            for kind, value in selectors.RECOMMEND_TALENTS_SELECTORS:
                try:
                    if kind == "xpath":
                        els = self.driver.find_elements(By.XPATH, value)
                    else:
                        els = self.driver.find_elements(By.CSS_SELECTOR, value)
                    for el in els:
                        if el.is_displayed():
                            return True
                except Exception as e:
                    self.logger.error(f"检测推荐牛人入口时出错（选择器={kind}:{value}）：{str(e)}")
                    continue
            return False

        try:
            return bool(wait.until(found))
        except TimeoutException:
            return False
        except Exception as e:
            self.logger.error(f"检测推荐牛人入口时出错：{str(e)}")
            return False

    def _try_login_with_cookies(self) -> bool:
        """尝试使用本地 cookies 恢复登录；成功返回 True，失败返回 False。"""
        if not os.path.exists(self.cookie_path):
            self.logger.info("未找到 cookies 文件，跳过 cookie 登录")
            return False

        cookies = load_cookies(self.cookie_path)
        if not cookies:
            self.logger.info("cookies 文件为空，跳过 cookie 登录")
            return False

        self.logger.info(f"检测到 cookies 文件，尝试恢复登录：{self.cookie_path}")

        # 必须先访问同域页面，再 add_cookie
        self.driver.get("https://www.zhipin.com/")

        applied = 0
        for c in cookies:
            try:
                self.driver.add_cookie(sanitize_cookie(c))
                applied += 1
            except Exception as e:
                self.logger.warning(f"注入 cookie 失败：{str(e)}")
                continue

        self.logger.info(f"已注入 cookies: {applied}/{len(cookies)}，刷新页面验证登录态")
        self.driver.refresh()

        # 关一次可能出现的下载弹层，避免遮挡菜单
        self._close_download_popup_if_present(timeout_seconds=2)

        # 以“推荐牛人入口是否存在”作为登录成功判定
        if self._has_recommend_talents_menu(timeout_seconds=4):
            self.logger.info("cookie 登录成功（已检测到推荐牛人入口），跳过扫码流程")
            return True

        self.logger.info("cookie 登录失败（未检测到推荐牛人入口），将回退到扫码登录")
        return False

    def _inject_cookies_if_present(self) -> int:
        """仅注入本地 cookies（若存在），返回成功注入的数量。"""
        if not os.path.exists(self.cookie_path):
            return 0
        cookies = load_cookies(self.cookie_path)
        if not cookies:
            return 0

        # 必须先访问同域页面，再 add_cookie
        self.driver.get("https://www.zhipin.com/")

        applied = 0
        for c in cookies:
            try:
                self.driver.add_cookie(sanitize_cookie(c))
                applied += 1
            except Exception as e:
                self.logger.warning(f"注入 cookie 失败：{str(e)}")
                continue
        return applied

    def _click_login_if_present(self, timeout_seconds: int = 3) -> bool:
        """如果页面存在“登录”按钮就点击；不存在则返回 False。"""
        try:
            wait = WebDriverWait(self.driver, timeout_seconds)
            btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.LOGIN_BUTTON_CSS)))
            self.logger.info("检测到登录按钮，准备点击")
            btn.click()
            self.logger.info("已点击登录按钮")
            return True
        except TimeoutException:
            return False
        except Exception as e:
            self.logger.error(f"点击登录按钮时出错：{str(e)}")
            return False

    def _persist_cookies(self):
        """保存当前会话 cookies 到本地文件。"""
        try:
            cookies = self.driver.get_cookies()
            save_cookies(self.cookie_path, cookies)
            self.logger.info(f"已保存 cookies：{self.cookie_path}")
        except Exception as e:
            self.logger.warning(f"保存 cookies 失败：{str(e)}")

    # -------- 基础工具 --------
    def _safe_click(self, element, timeout: int = 10):
        """尽量可靠地点击元素：滚动到可视区、等待可点击、优先原生点击，失败再用 JS 点击。"""
        wait = WebDriverWait(self.driver, timeout)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        wait.until(lambda d: element.is_displayed())

        try:
            ActionChains(self.driver).move_to_element(element).pause(0.1).perform()
        except Exception as e:
            self.logger.error(f"移动到元素时出错：{str(e)}")

        try:
            # 某些 selenium 版本对 WebElement 支持不一致，这里失败就忽略
            wait.until(EC.element_to_be_clickable(element))
        except Exception as e:
            self.logger.error(f"等待元素可点击时出错：{str(e)}")

        try:
            element.click()
            return
        except Exception as e:
            self.logger.error(f"原生点击元素时出错，尝试用 JS 点击：{str(e)}")
            self.driver.execute_script("arguments[0].click();", element)

    def _find_cards_in_current_context(self, selector: str):
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as e:
            self.logger.error(f"在当前上下文查找卡片元素时出错（选择器={selector}）：{str(e)}")
            return []

    def _find_cards_any_frame(self, selector: str):
        """在主文档及所有 iframe 中查找卡片元素，返回 (frame_element_or_None, elements)。"""
        self.driver.switch_to.default_content()
        elements = self._find_cards_in_current_context(selector)
        if elements:
            return None, elements

        frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe")
        for frame in frames:
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                elements = self._find_cards_in_current_context(selector)
                if elements:
                    return frame, elements
            except Exception as e:
                self.logger.error(f"切换到 iframe 查找卡片元素时出错：{str(e)}")
                continue

        self.driver.switch_to.default_content()
        return None, []

    def _switch_to_recommend_frame_if_present(self, timeout_seconds: int = 6) -> bool:
        """若存在 recommendFrame，则切换进入该 iframe；成功返回 True，否则 False。"""
        try:
            self.driver.switch_to.default_content()
        except Exception as e:
            self.logger.error(f"切换到默认内容时出错：{str(e)}")
            pass

        try:
            wait = WebDriverWait(self.driver, timeout_seconds)
            frame = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors.RECOMMEND_FRAME_CSS)))
            self.driver.switch_to.frame(frame)
            return True
        except TimeoutException:
            return False
        except Exception as e:
            self.logger.error(f"切换到 recommendFrame 时出错：{str(e)}")
            return False

    # -------- 业务流程：登录 --------
    def _click_login(self):
        self.logger.info("开始执行登录流程")
        self.driver.maximize_window()
        self.driver.implicitly_wait(10)
        self.logger.info("正在打开BOSS直聘网站...")
        self.driver.get("https://www.zhipin.com/")
        self.logger.info("网站加载完成")

        self.logger.info("等待登录按钮加载...")
        wait = WebDriverWait(self.driver, 10)
        login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.LOGIN_BUTTON_CSS)))
        self.logger.info("登录按钮已加载，准备点击")
        login_btn.click()
        self.logger.info("已点击登录按钮")

    def _click_app_scan_login(self):
        """点击APP扫码登录"""
        self.logger.info("等待APP扫码登录按钮加载...")
        wait = WebDriverWait(self.driver, 10)
        app_scan_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.APP_SCAN_SWITCH_CSS)))
        self.logger.info("APP扫码登录按钮已加载，准备点击")
        app_scan_btn.click()
        self.logger.info("已点击APP扫码登录按钮")

    def _get_qrcode(self):
        self.logger.info("等待二维码图片加载...")
        wait = WebDriverWait(self.driver, 20)
        qr_code = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selectors.QRCODE_IMG_CSS)))
        self.logger.info("二维码图片已显示")

        self.logger.info("等待二维码图片完全渲染...")
        wait.until(lambda driver: qr_code.size["width"] > 0 and qr_code.size["height"] > 0)
        self.logger.info("二维码图片渲染完成")

        qr_code_url = qr_code.get_attribute("src")
        # qr_code.screenshot("qr_code.png")
        self.logger.info(f"二维码URL: {qr_code_url}")
        # self.logger.info("二维码已保存为 'qr_code.png'")

    def _close_download_popup_if_present(self, timeout_seconds: int = 3):
        """登录后可能会弹出“立即下载”引导层；若存在则关闭。"""
        try:
            wait = WebDriverWait(self.driver, timeout_seconds)

            try:
                download_link = wait.until(
                    EC.visibility_of_element_located((By.XPATH, selectors.DOWNLOAD_LINK_XPATH))
                )
                href = download_link.get_attribute("href")
                self.logger.info(f"检测到下载弹层：立即下载链接={href}")
            except TimeoutException:
                return

            try:
                close_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selectors.DOWNLOAD_CLOSE_ICON_XPATH)))
                self._safe_click(close_btn)
                self.logger.info("已关闭下载弹层（X）")
                return
            except Exception as e:
                self.logger.warning(f"尝试关闭下载弹层（X）时出现异常：{str(e)}")
                close_btns = self.driver.find_elements(By.CSS_SELECTOR, selectors.DOWNLOAD_CLOSE_ICON_CSS)
                for btn in close_btns:
                    if btn.is_displayed():
                        self._safe_click(btn)
                        self.logger.info("已关闭下载弹层（i.icon-close）")
                        return

        except Exception as e:
            self.logger.warning(f"检测/关闭下载弹层时出现异常：{str(e)}")

    def _select_first_job_in_dropdown(self, timeout_seconds: int = 8) -> bool:
        """在推荐牛人页，打开职位下拉并点击第一个职位项（尽力执行）。"""
        try:
            wait = WebDriverWait(self.driver, timeout_seconds)
            label = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.JOB_DROPDOWN_LABEL_CSS)))
            self._safe_click(label)

            # 优先点当前项（如果下拉里有），否则点第一个
            time.sleep(0.2)
            items = self.driver.find_elements(By.CSS_SELECTOR, selectors.JOB_ITEM_CSS)
            if not items:
                self.logger.info("职位下拉已打开但未找到职位列表项，跳过职位选择")
                return False

            current = None
            for el in items:
                try:
                    if "curr" in (el.get_attribute("class") or ""):
                        current = el
                        break
                except Exception as e:
                    self.logger.error(f"检查职位项是否为当前项时出错：{str(e)}")
                    continue

            target = current or items[0]
            try:
                self.logger.info(f"准备选择职位：{target.text.strip()}")
            except Exception as e:
                self.logger.error(f"获取职位文本时出错：{str(e)}")
                pass
            self._safe_click(target)
            return True
        except TimeoutException:
            self.logger.info("未找到职位下拉入口，跳过职位选择")
            return False
        except Exception as e:
            self.logger.warning(f"选择职位时出现异常：{str(e)}")
            return False

    def _select_city_district(self, city: str, district: str, timeout_seconds: int = 10) -> bool:
        """在推荐牛人页选择城市/区县（尽力执行）。"""
        try:
            wait = WebDriverWait(self.driver, timeout_seconds)
            entry = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.AREA_ENTRY_CSS)))
            self._safe_click(entry)

            # 等待面板出现
            wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, selectors.AREA_PANEL_CSS))

            city_xpath = selectors.AREA_CITY_ITEM_XPATH_TEMPLATE.format(city=city)
            district_xpath = selectors.AREA_DISTRICT_ITEM_XPATH_TEMPLATE.format(district=district)

            try:
                city_el = wait.until(EC.element_to_be_clickable((By.XPATH, city_xpath)))
                self._safe_click(city_el)
            except TimeoutException:
                # 有些页面城市默认已选中，找不到也继续
                self.logger.info(f"未找到城市项（{city}），尝试继续选择区县")

            try:
                district_el = wait.until(EC.element_to_be_clickable((By.XPATH, district_xpath)))
                self._safe_click(district_el)
            except TimeoutException:
                self.logger.info(f"未找到区县项（{district}），跳过区县选择")
                return False

            try:
                confirm_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.AREA_CONFIRM_BUTTON_CSS))
                )
                self._safe_click(confirm_btn)
            except TimeoutException:
                self.logger.info("未找到区县确认按钮，可能自动生效")

            self.logger.info(f"已尝试选择区县：{city} {district}")
            return True
        except TimeoutException:
            self.logger.info("未找到区县入口，跳过区县选择")
            return False
        except Exception as e:
            self.logger.warning(f"选择区县时出现异常：{str(e)}")
            return False

    def _click_filter_and_apply_last_if_present(self, timeout_seconds: int = 8) -> bool:
        """点击“筛选”，若出现“是否应用上次的筛选条件？”则点击“应用”（尽力执行）。"""
        try:
            wait = WebDriverWait(self.driver, timeout_seconds)
            filter_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selectors.FILTER_BUTTON_XPATH)))
            self._safe_click(filter_btn)
            clicked_filter = True
        except TimeoutException:
            self.logger.info("未找到筛选按钮，跳过筛选点击")
            return False
        except Exception as e:
            self.logger.warning(f"点击筛选按钮时出现异常：{str(e)}")
            return False

        # 尽力处理“应用上次筛选条件”弹层
        try:
            wait = WebDriverWait(self.driver, 3)
            modal = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selectors.RECOVER_LAST_FILTER_MODAL_CSS)))
            if modal:
                apply_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.RECOVER_LAST_FILTER_APPLY_CSS))
                )
                self._safe_click(apply_btn)
                self.logger.info("已点击：应用上次筛选条件")
        except TimeoutException:
            # 没弹层很正常
            pass
        except Exception as e:
            self.logger.warning(f"处理上次筛选条件弹层时出现异常：{str(e)}")

        # 用户补充：点击完筛选后需要点“确定/确认”
        try:
            clicked_confirm = False
            for xp in selectors.FILTER_CONFIRM_BUTTON_XPATH_CANDIDATES:
                try:
                    btn = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
                    self._safe_click(btn)
                    clicked_confirm = True
                    self.logger.info(f"已点击筛选确认按钮（选择器={xp}）")
                    break
                except TimeoutException:
                    continue
                except Exception as e:
                    self.logger.warning(f"尝试点击筛选确认按钮时出现异常：{str(e)}")
                    continue
            if not clicked_confirm:
                self.logger.info("未检测到筛选确认按钮（确定/确认），可能无需确认")
        except Exception as e:
            self.logger.warning(f"点击筛选确认按钮时出现异常：{str(e)}")

        return clicked_filter

    def _click_first_tag_if_present(self, timeout_seconds: int = 3) -> bool:
        """尽力点击页面上的“第一个标签”（不保证命中，找不到就跳过）。"""
        candidates = [
            ".filter-tag",  # 常见：筛选标签
            ".tag",  # 通用 tag
            ".label",  # 兜底：可能命中职位 label（因此放后面）
        ]

        end = time.time() + timeout_seconds
        while time.time() < end:
            for css in candidates:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, css)
                    els = [e for e in els if e.is_displayed()]
                    if els:
                        self._safe_click(els[0])
                        try:
                            self.logger.info(f"已点击第一个标签（选择器={css}，文本={els[0].text.strip()}）")
                        except Exception as e:
                            self.logger.error(f"获取标签文本时出错：{str(e)}")
                            self.logger.info(f"已点击第一个标签（选择器={css}）")
                        return True
                except Exception as e:
                    self.logger.error(f"尝试点击第一个标签时出现异常（选择器={css}）：{str(e)}")
                    continue
            time.sleep(0.2)

        self.logger.info("未找到可点击的“第一个标签”，已跳过")
        return False

    def _apply_recommend_filters_flow(self, city: str = "盐城", district: str = "亭湖区"):
        """点击推荐牛人后：选职位→选区县→点筛选→点应用→点第一个标签（按用户描述尽力执行）。"""
        self.logger.info("开始执行推荐牛人页筛选流程（职位/区县/筛选）")
        try:
            # 页面往往需要一点时间渲染 iframe
            time.sleep(1)

            # 推荐牛人主体通常在 recommendFrame iframe 内
            switched = self._switch_to_recommend_frame_if_present(timeout_seconds=8)
            if switched:
                self.logger.info("已切换到 recommendFrame，开始查找筛选相关元素")
            else:
                self.logger.info("未检测到 recommendFrame，将在主文档中查找筛选相关元素")

            self._select_first_job_in_dropdown(timeout_seconds=8)
            self._select_city_district(city=city, district=district, timeout_seconds=10)
            self._click_filter_and_apply_last_if_present(timeout_seconds=8)
            self._click_first_tag_if_present(timeout_seconds=3)
        finally:
            try:
                self.driver.switch_to.default_content()
            except Exception as e:
                self.logger.error(f"切换回主文档时出错：{str(e)}")
                pass

    # -------- 业务流程：推荐牛人/详情 --------
    def _click_recommend_talents(self):
        """点击推荐牛人"""
        self.logger.info("准备点击推荐牛人按钮")
        wait = WebDriverWait(self.driver, 10)

        recommend_btn = None
        used = None
        for kind, value in selectors.RECOMMEND_TALENTS_SELECTORS:
            try:
                if kind == "xpath":
                    recommend_btn = wait.until(EC.element_to_be_clickable((By.XPATH, value)))
                else:
                    recommend_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, value)))
                used = f"{kind}:{value}"
                break
            except Exception as e:
                self.logger.error(f"尝试查找推荐牛人按钮时出错（选择器={kind}:{value}）：{str(e)}")
                continue

        if recommend_btn:
            self.logger.info(f"成功找到推荐牛人按钮，使用选择器: {used}")
            recommend_btn.click()
            self.logger.info("成功点击推荐牛人按钮")
        else:
            self.logger.error("未能找到推荐牛人按钮")

    def _click_talent_cards(self):
        """点击牛人名片获取详细信息"""
        self.logger.info("准备点击牛人名片")
        wait = WebDriverWait(self.driver, 25)

        try:
            self.logger.info(f"当前URL: {self.driver.current_url}")
            try:
                self.logger.info(f"当前标题: {self.driver.title}")
            except Exception as e:
                self.logger.error(f"获取当前标题时出错：{str(e)}")
                pass

            self.logger.info("等待牛人卡片列表加载（主文档/iframe）...")

            found_frame = None
            cards = []

            def locate_cards(d):
                nonlocal found_frame, cards
                for selector in selectors.CARD_SELECTOR_CANDIDATES:
                    frame, els = self._find_cards_any_frame(selector)
                    if els:
                        found_frame = frame
                        cards = els
                        return True
                return False

            wait.until(locate_cards)

            visible_cards = [c for c in cards if c.is_displayed()]
            if visible_cards:
                cards = visible_cards

            self.logger.info(f"找到 {len(cards)} 个牛人卡片，准备点击第一个")

            before_handles = set(self.driver.window_handles)
            before_url = self.driver.current_url

            first_card = cards[0]
            geek_id = first_card.get_attribute("data-geekid")
            self.logger.info(f"即将点击牛人卡片 data-geekid={geek_id}")

            self._safe_click(first_card)
            self.logger.info("已触发点击，等待打开详情...")

            def detail_opened(d):
                if len(d.window_handles) > len(before_handles):
                    return "new_window"
                if d.current_url != before_url:
                    return "url_changed"
                panel_css_candidates = [
                    "[class*='detail']",
                    "[class*='resume']",
                    "[class*='geek'] [class*='detail']",
                ]
                for css in panel_css_candidates:
                    try:
                        if d.find_elements(By.CSS_SELECTOR, css):
                            return "panel"
                    except Exception as e:
                        self.logger.error(f"检查详情面板时出错（选择器={css}）：{str(e)}")
                        continue
                return False

            try:
                opened_mode = WebDriverWait(self.driver, 8).until(detail_opened)
            except TimeoutException:
                opened_mode = None

            after_handles = set(self.driver.window_handles)
            new_handles = list(after_handles - before_handles)
            if new_handles:
                self.driver.switch_to.window(new_handles[0])
                self.logger.info("检测到新窗口已打开，已切换到详情窗口")
            elif opened_mode in {"url_changed", "panel"}:
                self.logger.info(f"检测到详情已打开（方式={opened_mode}），当前URL={self.driver.current_url}")
            else:
                self.logger.warning(
                    "点击后未检测到详情打开（可能点到了非可点击区域/被遮挡/站点拦截），建议提高选择器精确度或查看页面是否实际发生变化"
                )

        except Exception as e:
            try:
                self.logger.error(f"点击牛人卡片失败时URL: {self.driver.current_url}")
                self.logger.error(f"点击牛人卡片失败时标题: {self.driver.title}")
                self.driver.save_screenshot("debug_click_card_timeout.png")
                self.logger.error("已保存截图 debug_click_card_timeout.png 便于排查")
            except Exception as e:
                self.logger.error(f"保存调试信息时出错：{str(e)}")
                pass
            self.logger.error(f"点击牛人卡片流程出错: {str(e)}", exc_info=True)
        finally:
            try:
                self.driver.switch_to.default_content()
            except Exception as e:
                self.logger.error(f"切换回主文档时出错：{str(e)}")
                pass

    def _press_right_key_forever(self, interval_seconds: int = 5):
        """每隔 interval_seconds 秒发送一次键盘右方向键（可 Ctrl+C 退出）。"""
        self.logger.info(f"开始循环按键：每隔 {interval_seconds} 秒按一次右方向键（Ctrl+C 退出）")
        try:
            while True:
                try:
                    self.driver.switch_to.default_content()
                    ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
                    self.logger.info("已发送：右方向键")
                except Exception as e:
                    self.logger.warning(f"发送右方向键失败：{str(e)}")

                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            self.logger.info("检测到 Ctrl+C，已退出按键循环")

    # -------- 对外 API --------
    def login_and_run(self):
        self.logger.info("=" * 50)
        self.logger.info("开始BOSS直聘自动登录流程")
        self.logger.info("=" * 50)

        # 流程优化：先注入 cookies（若有）-> 刷新 -> 点击登录（若有）-> 判断推荐牛人
        try:
            self.driver.get("https://www.zhipin.com/")
        except Exception as e:
            self.logger.error(f"打开首页时出错：{str(e)}")
            pass

        applied = self._inject_cookies_if_present()
        if applied:
            self.logger.info(f"已注入 cookies（{applied} 个），刷新页面")
            try:
                self.driver.refresh()
            except Exception as e:
                self.logger.error(f"刷新页面时出错：{str(e)}")
                pass
        else:
            self.logger.info("未注入 cookies（无文件或为空）")

        self._close_download_popup_if_present(timeout_seconds=2)

        # 点击登录（如果按钮存在）；有些情况下已登录则没有登录按钮
        self._click_login_if_present(timeout_seconds=3)

        if self._has_recommend_talents_menu(timeout_seconds=4):
            self.logger.info("已检测到推荐牛人入口，视为登录成功")
            self._persist_cookies()
            self._close_download_popup_if_present(timeout_seconds=2)
        else:
            # 未检测到推荐牛人，走扫码
            self._click_app_scan_login()
            self._get_qrcode()

            self.logger.info("\n请使用手机APP扫描二维码并完成登录，登录成功后按回车键继续...")
            input("扫码登录完成后，按回车键继续...")
            self.logger.info("用户确认登录完成")

            self._persist_cookies()
            self._close_download_popup_if_present(timeout_seconds=3)

        # 无论 cookie 还是扫码，登录成功后都直接进入推荐牛人
        # 如果这里找不到推荐牛人按钮，大概率说明仍未登录/被拦截
        self._click_recommend_talents()

        self._close_download_popup_if_present(timeout_seconds=2)

        # 用户需求：点击完推荐牛人后，先选职位与城市区县，再点筛选并应用上次条件
        self._apply_recommend_filters_flow(city="盐城", district="亭湖区")

        self._click_talent_cards()

        self._press_right_key_forever(interval_seconds=5)

    def close(self):
        self.logger.info("正在关闭浏览器...")
        self.driver.quit()
        self.logger.info("浏览器已关闭")
