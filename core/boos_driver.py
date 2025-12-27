import logging
import os
import time
import random

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
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
        # 1. 关键词列表
        self.target_keywords = [
            "快递员", "外卖员", "配送员", "保安", "货车司机", "送餐员",
            "普工", "操作工", "服务员", "商务司机", "家政", "清洁工", "搬运工",
            "司机", "送货员", "仓库管理员", "物流专员", "物流助理", "配送专员",
            "仓库专员", "仓库管理员", "物流调度", "快递员兼职", "送餐兼职",
            "兼职司机", "临时工", "钟点工", "搬家工", "保洁员", "家政服务",
            "送货司机", "配送司机", "快递配送", "外卖配送", "物流司机",
            "仓库工人", "仓储管理员", "物流操作员", "配送助理", "快递分拣员",
            "送餐员兼职", "快递员全职", "外卖员全职", "配送员全职",
            "保安兼职", "货车司机兼职", "司机兼职", "搬运工兼职",
            "仓库管理员兼职", "物流专员兼职", "仓库专员兼职",
            "物流调度兼职", "临时工兼职", "钟点工兼职", "保洁员兼职",
            "家政服务兼职", "送货司机兼职"
        ]

    def _has_recommend_talents_menu(self, timeout_seconds: int = 3) -> bool:
        """判断是否已进入登录后的工作台"""
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
                    continue
            return False

        try:
            return bool(wait.until(found))
        except TimeoutException:
            return False
        except Exception as e:
            self.logger.error(f"检测推荐牛人入口时出错：{str(e)}")
            return False

    def _inject_cookies_if_present(self) -> int:
        if not os.path.exists(self.cookie_path):
            return 0
        cookies = load_cookies(self.cookie_path)
        if not cookies:
            return 0

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
        try:
            cookies = self.driver.get_cookies()
            save_cookies(self.cookie_path, cookies)
            self.logger.info(f"已保存 cookies：{self.cookie_path}")
        except Exception as e:
            self.logger.warning(f"保存 cookies 失败：{str(e)}")

    # -------- 基础工具 --------
    def _safe_click(self, element, timeout: int = 10):
        wait = WebDriverWait(self.driver, timeout)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        wait.until(lambda d: element.is_displayed())

        try:
            ActionChains(self.driver).move_to_element(element).pause(0.1).perform()
        except Exception as e:
            pass

        try:
            wait.until(EC.element_to_be_clickable(element))
        except Exception as e:
            pass

        try:
            element.click()
            return
        except Exception as e:
            self.logger.warning(f"原生点击失败，尝试JS点击: {str(e)[:50]}...")
            try:
                self.driver.execute_script("arguments[0].click();", element)
            except Exception as js_e:
                self.logger.error(f"JS点击也失败: {str(js_e)}")

    def _find_cards_any_frame(self, selector: str):
        """在主文档及所有 iframe 中查找卡片元素"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return None, elements
        except Exception as e:
            self.logger.error(f"查找卡片时出错（主文档）：{str(e)}")

        self.driver.switch_to.default_content()
        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            return None, elements

        frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe")
        for frame in frames:
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return frame, elements
            except Exception as e:
                continue

        self.driver.switch_to.default_content()
        return None, []

    def _click_app_scan_login(self):
        self.logger.info("等待APP扫码登录按钮加载...")
        wait = WebDriverWait(self.driver, 10)
        app_scan_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selectors.APP_SCAN_SWITCH_CSS)))
        app_scan_btn.click()
        self.logger.info("已点击APP扫码登录按钮")

    def _get_qrcode(self):
        self.logger.info("等待二维码图片加载...")
        wait = WebDriverWait(self.driver, 20)
        qr_code = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selectors.QRCODE_IMG_CSS)))
        self.logger.info("二维码图片已显示")
        wait.until(lambda driver: qr_code.size["width"] > 0 and qr_code.size["height"] > 0)
        qr_code_url = qr_code.get_attribute("src")
        self.logger.info(f"二维码URL: {qr_code_url}")

    def _close_download_popup_if_present(self, timeout_seconds: int = 3):
        try:
            wait = WebDriverWait(self.driver, timeout_seconds)
            try:
                wait.until(EC.visibility_of_element_located((By.XPATH, selectors.DOWNLOAD_LINK_XPATH)))
            except TimeoutException:
                return

            try:
                close_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selectors.DOWNLOAD_CLOSE_ICON_XPATH)))
                self._safe_click(close_btn)
                self.logger.info("已关闭下载弹层（X）")
                return
            except Exception as e:
                close_btns = self.driver.find_elements(By.CSS_SELECTOR, selectors.DOWNLOAD_CLOSE_ICON_CSS)
                for btn in close_btns:
                    if btn.is_displayed():
                        self._safe_click(btn)
                        return
        except Exception as e:
            self.logger.error(f"关闭下载弹层时出错：{str(e)}")

    def _click_recommend_talents(self):
        self.logger.info("准备点击推荐牛人按钮")
        wait = WebDriverWait(self.driver, 10)
        recommend_btn = None
        for kind, value in selectors.RECOMMEND_TALENTS_SELECTORS:
            try:
                if kind == "xpath":
                    recommend_btn = wait.until(EC.element_to_be_clickable((By.XPATH, value)))
                else:
                    recommend_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, value)))
                break
            except Exception as e:
                continue

        if recommend_btn:
            recommend_btn.click()
            self.logger.info("成功点击推荐牛人按钮")
        else:
            self.logger.error("未能找到推荐牛人按钮")

    # -------- 核心工具：滚动与翻页 --------

    def _scroll_down_list(self):
        """【打招呼模式专用】向下滚动列表，触发加载更多"""
        self.logger.info("执行向下滚动 (Loading More)...")
        try:
            # 1. 尝试滚动到页面底部
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # 2. 尝试发送 PageDown 键（辅助触发）
            ActionChains(self.driver).send_keys(Keys.PAGE_DOWN).perform()
            time.sleep(3)  # 等待新数据加载
        except Exception as e:
            self.logger.warning(f"向下滚动失败: {str(e)}")

    def _turn_page_right_detail(self):
        """【刷浏览量模式专用】在详情页按右键，切换下一位"""
        try:
            # 确保焦点在页面上
            ActionChains(self.driver).send_keys(Keys.ARROW_RIGHT).perform()
            self.logger.info("执行向右翻页 (Next Candidate)")
        except Exception as e:
            self.logger.warning(f"向右翻页失败: {str(e)}")

    # -------- 核心逻辑：自动打招呼 --------

    def _handle_limit_dialog(self) -> bool:
        """检查并处理每日沟通上限提示。返回 True 表示遇到了上限。"""
        try:
            # 1. 检测是否有“今日主动沟通数已达上限”的文本
            # 考虑到弹窗可能在 top level document，先尝试切换回 default_content
            try:
                self.driver.switch_to.default_content()
            except:
                pass

            # 使用 contains 文本匹配，比较稳健
            xpath_text = "//h3[contains(text(), '今日主动沟通数已达上限')]"

            # 快速检查是否存在上限提示元素
            try:
                # 显式等待短时间
                wait = WebDriverWait(self.driver, 2)
                el = wait.until(EC.presence_of_element_located((By.XPATH, xpath_text)))
                if not el.is_displayed():
                    return False
            except TimeoutException:
                return False

            self.logger.warning("【检测到】今日主动沟通数已达上限！准备关闭弹窗...")

            # 2. 尝试多种方式关闭弹窗
            close_strategies = [
                (By.CSS_SELECTOR, ".boss-popup__close"),  # HTML中看到的类名
                (By.XPATH, "/html/body/div[7]/div[1]/div[2]/i"),  # 用户指定的XPath
                (By.CSS_SELECTOR, ".dialog-close"),  # 常见备用
                (By.CSS_SELECTOR, ".close-icon"),  # 常见备用
            ]

            closed = False
            for by_mode, selector in close_strategies:
                try:
                    btns = self.driver.find_elements(by_mode, selector)
                    for btn in btns:
                        if btn.is_displayed():
                            self.logger.info(f"尝试点击关闭按钮: {selector}")
                            # 强制使用JS点击，因为可能有遮罩层
                            self.driver.execute_script("arguments[0].click();", btn)
                            closed = True
                            time.sleep(1)
                            break
                    if closed: break
                except Exception as e:
                    self.logger.warning(f"尝试关闭策略 {selector} 失败: {str(e)}")

            # 3. 兜底：按 ESC
            if not closed:
                self.logger.warning("未找到明确的关闭按钮，尝试按ESC键强行关闭...")
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)

            return True

        except Exception as e:
            self.logger.error(f"处理上限弹窗逻辑出错: {str(e)}")
            return True

    def _run_greet_loop(self, target_count: int):
        """
        打招呼模式逻辑：
        1. 列表找人 -> 找不到则【向下滚动】
        2. 找到 -> 点进详情 -> 打招呼 -> (检查是否上限) -> 关闭 -> 回列表
        """
        self.logger.info(f"开始执行自动打招呼，目标人数：{target_count}")

        greeted_count = 0
        processed_ids = set()

        while greeted_count < target_count:
            # 1. 查找当前页面所有可见卡片
            cards = []

            for selector in selectors.CARD_SELECTOR_CANDIDATES:
                frame, els = self._find_cards_any_frame(selector)
                if els:
                    cards = [e for e in els if e.is_displayed()]
                    if cards:
                        break

            # 如果当前视图没卡片，直接滚动加载
            if not cards:
                self.logger.warning("当前视图未找到可见卡片，向下滚动刷新...")
                self._scroll_down_list()
                continue

            # 2. 筛选符合条件的卡片
            target_card = None
            target_id = None

            for card in cards:
                try:
                    gid = card.get_attribute("data-geekid")
                    if gid in processed_ids:
                        continue

                    text_content = card.text
                    has_keyword = any(kw in text_content for kw in self.target_keywords)

                    is_online = False
                    try:
                        online_icon = card.find_element(By.CSS_SELECTOR, ".online-marker")
                        if online_icon.is_displayed():
                            is_online = True
                    except:
                        is_online = False

                    if has_keyword and is_online:
                        target_card = card
                        target_id = gid
                        self.logger.info(f"找到匹配牛人 [在线]: {text_content.replace(chr(10), ' ')[:30]}...")
                        break

                except Exception as e:
                    continue

            # 3. 执行操作
            if target_card:
                processed_ids.add(target_id)
                try:
                    self.logger.info(f"[{greeted_count + 1}/{target_count}] 正在点击牛人名片...")
                    self._safe_click(target_card)

                    status = self._perform_detail_actions()

                    if status == "LIMIT_REACHED":
                        print("\n" + "!" * 40)
                        print("【停止任务】今日主动沟通数已达上限（需付费购买）。")
                        print("已自动退出详情页，正在返回主菜单...")
                        print("!" * 40 + "\n")
                        return  # 直接返回，结束 _run_greet_loop
                    elif status == "SUCCESS":
                        greeted_count += 1
                        self.logger.info(f"成功打招呼！当前进度: {greeted_count}/{target_count}")
                    else:
                        self.logger.warning("打招呼流程未完全成功，跳过此人")

                except Exception as e:
                    self.logger.error(f"处理牛人卡片时出错: {str(e)}")
            else:
                self.logger.info("当前视图无更多符合条件的牛人，向下滚动加载更多...")
                self._scroll_down_list()

        self.logger.info("已达到目标打招呼人数。")

    def _close_detail_page(self):
        """关闭详情页的通用方法"""
        try:
            self.driver.switch_to.default_content()
        except:
            pass

        close_xpath = "/html/body/div[2]/div[1]/div[2]/i"
        try:
            wait = WebDriverWait(self.driver, 3)
            close_btn = wait.until(EC.element_to_be_clickable((By.XPATH, close_xpath)))
            self._safe_click(close_btn)
            self.logger.info("已关闭详情页")
        except Exception:
            try:
                close_btn = self.driver.find_element(By.CSS_SELECTOR, ".iboss-close, .dialog-close")
                self.driver.execute_script("arguments[0].click();", close_btn)
            except Exception:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

    def _perform_detail_actions(self) -> str:
        """
        进入详情页后的动作：停留5s -> 打招呼 -> 检查上限 -> 停留3s -> 关闭
        返回状态: 'SUCCESS', 'FAILED', 'LIMIT_REACHED'
        """
        try:
            self.logger.info("进入详情，停留 5 秒...")
            time.sleep(5)

            # 点击打招呼
            greet_btn_xpath = "/html/body/div[2]/div[1]/div[1]/div/div/div[1]/div/div[2]/div/div/div[1]/div/div/div[2]/div/span/div/button"
            greet_clicked = False

            try:
                # 尝试查找并点击
                btn = self.driver.find_element(By.XPATH, greet_btn_xpath)
                self._safe_click(btn)
                greet_clicked = True
                self.logger.info("已点击打招呼按钮")
            except Exception as e:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, ".btn.btn-greet")
                    self._safe_click(btn)
                    greet_clicked = True
                except Exception as e:
                    self.logger.error(f"未找到打招呼按钮: {str(e)}")

            if greet_clicked:
                # 点击后等待一下，检查是否出现上限提示
                time.sleep(2)

                # 检查是否出现上限弹窗
                if self._handle_limit_dialog():
                    time.sleep(1)  # 等待弹窗关闭动画
                    self._close_detail_page()  # 关闭详情页
                    return "LIMIT_REACHED"

            self.logger.info("停留 3 秒...")
            time.sleep(3)

            # 关闭详情页
            self._close_detail_page()

            return "SUCCESS" if greet_clicked else "FAILED"

        except Exception as e:
            self.logger.error(f"详情页操作异常: {str(e)}")
            try:
                self._close_detail_page()
            except:
                pass
            return "FAILED"

    # -------- 核心逻辑：刷浏览量 --------

    def _run_browse_loop(self, max_minutes: int = 20):
        """
        刷浏览量模式逻辑：
        1. 点开第一个人进入详情页
        2. 循环：按右键 (向右翻页)，默认限制时长
        """
        self.logger.info(f"准备进入刷浏览量模式，默认限时 {max_minutes} 分钟...")

        cards = []
        for selector in selectors.CARD_SELECTOR_CANDIDATES:
            frame, els = self._find_cards_any_frame(selector)
            if els:
                cards = [e for e in els if e.is_displayed()]
                if cards:
                    break

        if cards:
            self.logger.info("正在打开第一个牛人卡片，进入详情页...")
            self._safe_click(cards[0])
            time.sleep(3)  # 等待详情打开
        else:
            self.logger.warning("未找到卡片，无法进入详情页，请手动打开一个详情页。")
            self._scroll_down_list()

        self.logger.info(f"开始执行翻页（每3秒按一次右方向键）。限时 {max_minutes} 分钟。按 Ctrl+C 可在控制台中断。")
        print(f"\n正在刷浏览量... (程序将在详情页不断按 '→' 键切换下一位，限时 {max_minutes} 分钟)")

        start_time = time.time()
        end_time = start_time + (max_minutes * 60)

        try:
            while time.time() < end_time:
                self._turn_page_right_detail()

                # 偶尔输出一下剩余时间
                remaining = int(end_time - time.time())
                if remaining > 0 and remaining % 60 == 0:
                    self.logger.info(f"剩余时间: {remaining // 60} 分钟")

                time.sleep(3)

            self.logger.info("刷浏览量任务时间结束。")
            print("\n时间到，已结束刷浏览量任务，返回主菜单。")

            # 任务结束，尝试退出详情页
            self._close_detail_page()

        except KeyboardInterrupt:
            self.logger.info("用户中断刷浏览量模式。")

    # -------- 新增：扫码检测逻辑 --------
    def _wait_for_scan_login(self):
        """轮询检测是否扫码成功，以及二维码是否需要刷新"""
        self.logger.info("进入扫码检测模式...")
        print("\n" + "=" * 40)
        print("请使用手机 BOSS直聘 APP 扫描屏幕上的二维码进行登录。")
        print("程序将自动检测登录状态，请勿关闭窗口...")
        print("=" * 40 + "\n")

        while True:
            # 1. 检测登录成功（推荐牛人入口出现）
            if self._has_recommend_talents_menu(timeout_seconds=2):
                self.logger.info("检测到推荐牛人入口，扫码登录成功！")
                break

            # 2. 检测二维码是否失效
            try:
                # 优先使用 CSS 选择器定位失效提示框内的按钮
                # HTML: <div class="invalid-box">...<button ...>点击刷新</button></div>
                invalid_box_btns = self.driver.find_elements(By.CSS_SELECTOR, ".invalid-box button")

                # 如果 CSS 没找到，尝试用户提供的 XPath
                if not invalid_box_btns:
                    user_xpath = "/html/body/div/div/div[2]/div[2]/div[2]/div[2]/div[1]/div/button"
                    invalid_box_btns = self.driver.find_elements(By.XPATH, user_xpath)

                if invalid_box_btns:
                    btn = invalid_box_btns[0]
                    if btn.is_displayed():
                        self.logger.warning("检测到二维码已失效，正在自动点击刷新...")
                        self._safe_click(btn)
                        # 等待刷新动画
                        time.sleep(3)
                        self.logger.info("二维码已刷新。")

                        # --- 获取新二维码URL ---
                        try:
                            # 重新查找二维码图片元素
                            qr_img = self.driver.find_element(By.CSS_SELECTOR, selectors.QRCODE_IMG_CSS)
                            new_src = qr_img.get_attribute("src")
                            self.logger.info(f"新的二维码URL: {new_src}")
                        except Exception as e:
                            self.logger.warning(f"获取新二维码URL失败: {str(e)}")
                        # ---------------------
            except Exception as e:
                pass

            time.sleep(1)

    # -------- 对外 API --------
    def login_and_run(self):
        self.logger.info("=" * 50)
        self.logger.info("开始BOSS直聘自动流程")
        self.logger.info("=" * 50)

        try:
            self.driver.get("https://www.zhipin.com/")
        except Exception as e:
            self.logger.error(f"打开BOSS直聘首页时出错：{str(e)}")

        self._inject_cookies_if_present()
        self._close_download_popup_if_present(timeout_seconds=2)
        self._click_login_if_present(timeout_seconds=3)

        if self._has_recommend_talents_menu(timeout_seconds=4):
            self.logger.info("已检测到推荐牛人入口，视为登录成功")
            self._persist_cookies()
            self._close_download_popup_if_present(timeout_seconds=2)
        else:
            self._click_app_scan_login()
            self._get_qrcode()

            # 使用新的轮询等待方法替换 input
            self._wait_for_scan_login()

            self._persist_cookies()
            self._close_download_popup_if_present(timeout_seconds=3)

        self._click_recommend_talents()
        self._close_download_popup_if_present(timeout_seconds=2)

        self.logger.info("等待用户手动筛选...")
        print("\n" + "=" * 40)
        print("【步骤1】请在浏览器中手动选择：")
        print("   1. 职位 (Job)")
        print("   2. 城市和区县 (City/District)")
        print("   3. 其他筛选条件")
        print("=" * 40 + "\n")

        input("手动选择完成后，请按回车键开始任务...")

        while True:
            print("\n" + "-" * 30)
            print("请选择接下来的操作：")
            print("1. 开始/继续 自动打招呼 (筛选关键词+在线)")
            print("2. 刷浏览量 (进入卡片详情页一直向右刷新)")
            print("3. 退出程序")
            print("-" * 30)

            choice = input("请输入序号 (1/2/3): ").strip()

            if choice == "1":
                try:
                    num = int(input("请输入本次要打招呼的人数: "))
                    print(f"开始执行：在结果中查找 {self.target_keywords} 且 [在线] 的用户...")
                    print("提示：如果当前屏没有合适人选，程序会自动向下滚动 (Scroll Down)。")
                    self._run_greet_loop(num)
                except ValueError:
                    print("输入无效，请输入数字。")

            elif choice == "2":
                self._run_browse_loop(max_minutes=20)

            elif choice == "3":
                self.logger.info("用户选择退出。")
                break
            else:
                print("无效的选择，请重新输入。")

    def close(self):
        self.logger.info("正在关闭浏览器...")
        self.driver.quit()
        self.logger.info("浏览器已关闭")
