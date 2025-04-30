from typing import List, Dict, Any

class NavigationHandler:
    def __init__(self, assistant):
        self.assistant = assistant

    async def handle_navigation(self, command: str) -> bool:
        """Handle navigation commands"""
        if command.lower().startswith(("go to ", "navigate to ", "open ")):
            # Extract URL
            parts = command.split(" ", 2)
            if len(parts) >= 3:
                url = parts[2]
                return await self.browse_website(url)
        return False

    async def browse_website(self, url: str) -> bool:
        """Navigate to URL"""
        try:
            # Clean up the URL
            url = url.strip()

            # Check if it's a valid URL format
            if not url.startswith(('http://', 'https://')):
                # Special handling for signin URLs
                if url.startswith('#/signin') or url.startswith('/#/signin') or 'signin' in url:
                    self.assistant.speak("Trying alternative approach for signin page...")
                    try:
                        # Try the known working URL
                        await self.assistant.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=40000)
                        self.assistant.speak("Successfully navigated to signin page")
                        return True
                    except Exception as alt_err:
                        self.assistant.speak(f"Alternative navigation also failed: {str(alt_err)}")

                        # As a last resort, try to find and click login button
                        self.assistant.speak("Trying to find login option...")
                        login_selectors = await self.assistant._get_llm_selectors("find login or sign in link or button",
                                                                          await self.assistant._get_page_context())
                        for selector in login_selectors:
                            try:
                                if await self.assistant.page.locator(selector).count() > 0:
                                    await self.assistant.page.locator(selector).first.click()
                                    await self.assistant.page.wait_for_timeout(10000)
                                    self.assistant.speak("Found and clicked login option")
                                    return True
                            except Exception:
                                continue
                    return False

                # Add https:// prefix for regular domains
                url = f"https://{url}"

            # Ensure there's a domain name
            domain_part = url.split('//')[1].split('/')[0]
            if not domain_part or domain_part == '':
                self.assistant.speak("Invalid URL: Missing domain name")
                return False

            print(f"Navigating to: {url}")
            await self.assistant.page.goto(url, wait_until="networkidle", timeout=20000)
            self.assistant.speak(f"Loaded: {await self.assistant.page.title()}")
            return True
        except Exception as e:
            self.assistant.speak(f"Navigation failed: {str(e)}")

            # Handle special case for login URLs
            if url.startswith('#/signin') or url.startswith('/#/signin') or 'signin' in url:
                self.assistant.speak("Trying alternative approach for signin page...")
                try:
                    # Try the known working URL
                    await self.assistant.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=30000)
                    self.assistant.speak("Successfully navigated to signin page")
                    return True
                except Exception as alt_err:
                    self.assistant.speak(f"Alternative navigation also failed: {str(alt_err)}")

                    # As a last resort, try to find and click login button
                    self.assistant.speak("Trying to find login option...")
                    login_selectors = await self.assistant._get_llm_selectors("find login or sign in link or button",
                                                                      await self.assistant._get_page_context())
                    for selector in login_selectors:
                        try:
                            if await self.assistant.page.locator(selector).count() > 0:
                                await self.assistant.page.locator(selector).first.click()
                                await self.assistant.page.wait_for_timeout(10000)
                                self.assistant.speak("Found and clicked login option")
                                return True
                        except Exception:
                            continue
            return False 