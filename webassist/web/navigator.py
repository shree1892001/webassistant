"""
Web navigation module for WebAssist
"""

import re
import logging
from typing import Dict, Any, List, Optional

from playwright.async_api import Page

from webassist.speech.synthesizer import SpeechSynthesizer
from webassist.llm.provider import LLMProvider
from webassist.models.result import InteractionResult


class WebNavigator:
    """Web navigation class"""

    def __init__(self, page: Page, llm_provider: LLMProvider, speaker: SpeechSynthesizer):
        """Initialize the navigator"""
        self.page = page
        self.llm_provider = llm_provider
        self.speaker = speaker
        self.logger = logging.getLogger(__name__)

    async def browse_website(self, url: str) -> bool:
        """Navigate to a website"""
        try:
            if "://" in url:
                self.speaker.speak(f"🌐 Navigating to {url}")
                await self.page.goto(url, wait_until="networkidle", timeout=20000)
            elif url.startswith('#') or url.startswith('/#'):
                current_url = self.page.url
                base_url = current_url.split('#')[0]
                new_url = f"{base_url}{url}" if url.startswith('#') else f"{base_url}{url[1:]}"
                self.speaker.speak(f"🌐 Navigating within page to {url}")
                await self.page.goto(new_url, wait_until="networkidle", timeout=20000)
            elif not url.startswith(('http://', 'https://')):
                if "/" in url and not url.startswith("/"):
                    domain = url.split("/")[0]
                    self.speaker.speak(f"🌐 Navigating to https://{domain}")
                    await self.page.goto(f"https://{domain}", wait_until="networkidle", timeout=20000)
                else:
                    self.speaker.speak(f"🌐 Navigating to https://{url}")
                    await self.page.goto(f"https://{url}", wait_until="networkidle", timeout=20000)
            else:
                current_url = self.page.url
                domain_match = re.match(r'^(?:http|https)://[^/]+', current_url)
                if domain_match:
                    domain = domain_match.group(0)
                    new_url = f"{domain}/{url}"
                    self.speaker.speak(f"🌐 Navigating to {new_url}")
                    await self.page.goto(new_url, wait_until="networkidle", timeout=20000)
                else:
                    self.speaker.speak(f"🌐 Navigating to https://{url}")
                    await self.page.goto(f"https://{url}", wait_until="networkidle", timeout=20000)

            self.speaker.speak(f"📄 Loaded: {await self.page.title()}")
            await self._dismiss_popups()
            return True
        except Exception as e:
            self.speaker.speak(f"❌ Navigation failed: {str(e)}")
            if url.startswith('#') or url.startswith('/#'):
                if 'signin' in url or 'login' in url:
                    self.speaker.speak("Trying to find login option...")
                    login_selectors = await self._get_llm_selectors("find login or sign in link or button",
                                                          await self._get_page_context())
                    for selector in login_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                await self.page.locator(selector).first.click()
                                await self.page.wait_for_timeout(2000)
                                self.speaker.speak("Found and clicked login option")
                                return True
                        except Exception as click_err:
                            continue
            return False

    async def _dismiss_popups(self) -> None:
        """Dismiss popups on the page"""
        try:
            context = await self._get_page_context()
            popup_selectors = await self._get_llm_selectors(
                "find popup close button, cookie acceptance button, or dismiss button", context)

            for selector in popup_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.locator(selector).first.click(timeout=2000)
                        self.speaker.speak("🗑️ Closed popup")
                        await self.page.wait_for_timeout(1000)
                        break
                except:
                    pass
        except:
            pass

    async def _get_page_context(self) -> Dict[str, Any]:
        """Get the current page context"""
        try:
            await self.page.wait_for_timeout(1000)

            input_fields = []
            inputs = self.page.locator("input:visible, textarea:visible, select:visible")
            count = await inputs.count()

            for i in range(min(count, 10)):
                try:
                    field = inputs.nth(i)
                    field_info = {
                        "tag": await field.evaluate("el => el.tagName.toLowerCase()"),
                        "type": await field.evaluate("el => el.type || ''"),
                        "id": await field.evaluate("el => el.id || ''"),
                        "name": await field.evaluate("el => el.name || ''"),
                        "placeholder": await field.evaluate("el => el.placeholder || ''"),
                        "aria-label": await field.evaluate("el => el.getAttribute('aria-label') || ''")
                    }
                    input_fields.append(field_info)
                except:
                    pass

            menu_items = []
            try:
                menus = self.page.locator(
                    "[role='menubar'] [role='menuitem'], .p-menuitem, nav a, .navigation a, .menu a, header a")
                menu_count = await menus.count()

                for i in range(min(menu_count, 20)):
                    try:
                        menu_item = menus.nth(i)
                        text = await menu_item.inner_text()
                        text = text.strip()
                        if text:
                            submenu_locator = menu_item.locator(
                                ".p-submenu-icon, [class*='submenu'], [class*='dropdown'], [class*='caret']")
                            has_submenu = await submenu_locator.count() > 0
                            menu_items.append({
                                "text": text,
                                "has_submenu": has_submenu
                            })
                    except:
                        pass
            except:
                pass

            buttons = []
            try:
                button_elements = self.page.locator(
                    "button:visible, [role='button']:visible, input[type='submit']:visible, input[type='button']:visible")
                button_count = await button_elements.count()

                for i in range(min(button_count, 10)):
                    try:
                        button = button_elements.nth(i)
                        text = await button.inner_text()
                        text = text.strip()
                        buttons.append({
                            "text": text,
                            "id": await button.evaluate("el => el.id || ''"),
                            "class": await button.evaluate("el => el.className || ''"),
                            "type": await button.evaluate("el => el.type || ''")
                        })
                    except:
                        pass
            except:
                pass

            body_locator = self.page.locator("body")
            inner_text = await body_locator.inner_text()
            inner_html = await body_locator.inner_html()

            return {
                "title": await self.page.title(),
                "url": self.page.url,
                "text": inner_text[:1000],
                "html": self._filter_html(inner_html[:4000]),
                "input_fields": input_fields,
                "menu_items": menu_items,
                "buttons": buttons
            }
        except Exception as e:
            self.logger.error(f"Context error: {e}")
            return {}

    def _filter_html(self, html: str) -> str:
        """Filter HTML for LLM prompt"""
        return re.sub(
            r'<(input|button|a|form|select|textarea|div|ul|li)[^>]*>',
            lambda m: m.group(0) + '\n',
            html
        )[:3000]

    async def _get_llm_selectors(self, task: str, context: Dict[str, Any]) -> List[str]:
        """Use LLM to generate selectors for a task based on page context"""
        return await self.llm_provider.get_selectors(task, context)

    async def go_back(self) -> bool:
        """Go back to the previous page"""
        try:
            await self.page.go_back()
            self.speaker.speak(f"◀️ Went back to {await self.page.title()}")
            return True
        except Exception as e:
            self.speaker.speak("❌ Could not go back")
            self.logger.error(f"Go back error: {e}")
            return False

    async def go_forward(self) -> bool:
        """Go forward to the next page"""
        try:
            await self.page.go_forward()
            self.speaker.speak(f"▶️ Went forward to {await self.page.title()}")
            return True
        except Exception as e:
            self.speaker.speak("❌ Could not go forward")
            self.logger.error(f"Go forward error: {e}")
            return False

    async def refresh(self) -> bool:
        """Refresh the current page"""
        try:
            await self.page.reload()
            self.speaker.speak(f"🔄 Refreshed {await self.page.title()}")
            return True
        except Exception as e:
            self.speaker.speak("❌ Could not refresh")
            self.logger.error(f"Refresh error: {e}")
            return False
