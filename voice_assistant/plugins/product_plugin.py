from typing import Dict, Any, Optional, List
from ..core.plugin import BasePlugin
from ..utils.constants import COMMAND_PATTERNS, ERROR_MESSAGES, SUCCESS_MESSAGES

class ProductPlugin(BasePlugin):
    """Plugin for handling product management functionality"""
    
    def __init__(self, page, speech, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.page = page
        self.speech = speech

    def _get_command_patterns(self) -> Dict[str, str]:
        """Get command patterns for product plugin"""
        return {
            'check_product': r'check product (.*)',
            'check_all_products': r'check all products'
        }

    async def handle_command(self, command: str) -> bool:
        """Handle product-related commands"""
        command = command.lower().strip()
        
        # Handle product checkbox
        if self._matches_pattern(command, self.command_patterns['check_product']):
            product_name = self._extract_pattern(command, self.command_patterns['check_product'])
            return await self._check_product_checkbox(product_name)

        # Handle check all products
        if self._matches_pattern(command, self.command_patterns['check_all_products']):
            return await self._check_all_products()

        return False

    async def _check_product_checkbox(self, product_name: str) -> bool:
        """Check a product checkbox"""
        try:
            # Find the product checkbox
            product_checkbox = await self.page.query_selector(f'.p-checkbox:text("{product_name}")')
            if not product_checkbox:
                self.speech.speak(ERROR_MESSAGES['product_not_found'])
                return False

            # Check if already checked
            is_checked = await product_checkbox.is_checked()
            if not is_checked:
                await product_checkbox.click()
                self.speech.speak(SUCCESS_MESSAGES['product_checked'].format(product=product_name))
            else:
                self.speech.speak(SUCCESS_MESSAGES['product_already_checked'].format(product=product_name))
            return True
        except Exception as e:
            self.speech.speak(f"Error checking product: {str(e)}")
            return False

    async def _check_all_products(self) -> bool:
        """Check all product checkboxes"""
        try:
            # Find all product checkboxes
            product_checkboxes = await self.page.query_selector_all('.p-checkbox')
            if not product_checkboxes:
                self.speech.speak(ERROR_MESSAGES['no_products_found'])
                return False

            # Check each checkbox
            for checkbox in product_checkboxes:
                if not await checkbox.is_checked():
                    await checkbox.click()

            self.speech.speak(SUCCESS_MESSAGES['all_products_checked'])
            return True
        except Exception as e:
            self.speech.speak(f"Error checking all products: {str(e)}")
            return False

    def get_help_text(self) -> List[str]:
        """Get help text for product commands"""
        return [
            "check product [name] - Check a product checkbox",
            "check all products - Check all product checkboxes"
        ]

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for product plugin"""
        return {
            'enabled': bool,
            'timeout': int,
            'max_retries': int
        } 