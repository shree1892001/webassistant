"""Constants for the voice assistant"""

from typing import Dict, List, Any

# Default configuration
DEFAULT_CONFIG = {
    'voice': {
        'rate': 150,
        'volume': 1.0,
        'voice': 'default'
    },
    'browser': {
        'browser_type': 'chromium',
        'headless': False
    },
    'plugins': {},
    'input_mode': 'text'
}

DEFAULT_API_KEY = "YOUR_GEMINI_API_KEY"  # Replace with actual API key

DROPDOWN_FILTER_SELECTORS = {
    'input': [
        "//input[contains(@class, 'p-dropdown-filter')]",
        "//input[@type='text'][contains(@class, 'p-dropdown-filter')]"
    ]
}

# EIN Service Selectors
EIN_SERVICE_SELECTORS = {
    'container': ".wizard-card-checkbox-text1",
    'checkbox': [
        "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]//input[@type='checkbox']",
        "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]//input"
    ],
    'text': [
        "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]",
        "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]"
    ],
    'tooltip': [
        "//button[@data-bs-toggle='tooltip']",
        "//i[contains(@class, 'pi-info-circle')]"
    ]
}

# Command patterns
COMMAND_PATTERNS: Dict[str, str] = {
    'filter_dropdown': r'filter (?:dropdown|list) (?:for )?(.*)',
    'clear_filter': r'clear (?:dropdown|list) filter',
    'select_option': r'select (?:option|item) (?:from )?(?:dropdown|list) (.*)',
    'enter_text': r'(?:enter|type|input) (?:text )?(?:in|into|for) (.*)',
    'click_button': r'click (?:on )?(?:button|link) (.*)',
    'navigate': r'(?:go to|navigate to|open) (.*)',
    'login': r'login (?:with|using) (?:email|username) (.*) (?:and|with) password (.*)'
}

# Selector patterns
SELECTOR_PATTERNS: Dict[str, List[str]] = {
    'dropdown': [
        'input.p-dropdown-filter',
        'input[type="text"][class*="dropdown"]',
        '.p-dropdown input',
        'select',
        '[role="combobox"]'
    ],
    'button': [
        'button',
        'input[type="button"]',
        'input[type="submit"]',
        '[role="button"]',
        'a[href]'
    ],
    'input': [
        'input[type="text"]',
        'input[type="email"]',
        'input[type="password"]',
        'textarea',
        '[role="textbox"]'
    ]
}

# Error messages
ERROR_MESSAGES: Dict[str, str] = {
    'filter_not_found': 'Dropdown filter input not found',
    'filter_not_visible': 'Dropdown filter input is not visible',
    'filter_disabled': 'Dropdown filter input is disabled',
    'filter_text_failed': 'Failed to enter search text correctly',
    'filter_clear_failed': 'Failed to clear filter input',
    'option_not_found': 'Could not find the specified option',
    'navigation_failed': 'Failed to navigate to the specified URL',
    'login_failed': 'Failed to login with provided credentials'
}

# Success messages
SUCCESS_MESSAGES: Dict[str, str] = {
    'filter_text_entered': 'Successfully entered search text: {text}',
    'filter_cleared': 'Successfully cleared filter input',
    'option_selected': 'Successfully selected option: {option}',
    'navigation_success': 'Successfully navigated to: {url}',
    'login_success': 'Successfully logged in'
}

# Default Values
DEFAULT_VALUES = {
    'ein_price': '$45.00',
    'ein_description': 'Preparation & submission of required forms to obtain an EIN with the IRS.'
}

# Timeouts
TIMEOUTS = {
    'selector': 5000,  # 5 seconds
    'action_delay': 500  # 500 milliseconds
} 