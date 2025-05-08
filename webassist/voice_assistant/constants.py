"""
Constants for the voice assistant module.
Contains all hardcoded values, patterns, selectors, and JavaScript snippets used in the voice assistant.
"""

# URLs
LOGIN_URL = "https://www.redberyltest.in/#/signin"

# Prompts and messages
VOICE_PROMPT = "🎤 READY FOR VOICE COMMAND... (Say 'help' for available commands or 'text' to switch to text mode)"
TEXT_PROMPT = "Type your commands below. Type 'help' for available commands or 'exit' to quit."
VOICE_MODE_SWITCH_MESSAGE = "Switched to voice mode. Say your commands."
TEXT_MODE_SWITCH_MESSAGE = "Switched to text mode. Type your commands."

# Timeouts and delays
NAVIGATION_TIMEOUT = 30000  # 30 seconds
PAGE_LOAD_WAIT = 5000  # 5 seconds
DROPDOWN_OPEN_WAIT = 1000  # 1 second
FILTER_WAIT = 1000  # 1 second
SELECTION_WAIT = 1000  # 1 second
TAB_LOAD_WAIT = 2000  # 2 seconds
NAVIGATION_WAIT = 2  # 2 seconds (for asyncio.sleep)

# Command patterns
NAVIGATION_PATTERN = r'(?:go to|navigate to|open)\s+(.+)'
TAB_PATTERN = r'(?:click|select|open|go to)\s+(?:the\s+)?(\w+)\s+tab'
STATE_SEARCH_PATTERN = r'(?:search|find|look for)\s+(?:the\s+)?(?:state|states?)\s+(?:of\s+)?([a-zA-Z\s]+)'
LOGIN_PATTERN = r'(?:login|sign in|click login button)'
EMAIL_PASSWORD_PATTERN = r'enter\s+(?:email|email address|email adddress)\s+(\S+)(?:\s+(?:and|with|&)?\s+(?:password|pass|pwd|pword|oassword)\s+(\S+))?'
EMAIL_ONLY_PATTERNS = [
    r'enter (?:email|email address|email adddress)\s+(\S+@\S+)',
    r'(?:enter|input|type|fill)\s+(?:ema[a-z]+|email address|email adddress)?\s*(\S+@\S+)',
    r'(?:email|ema[a-z]+|email address|email adddress)\s+(\S+@\S+)',
    r'(?:enter|input|type|fill)\s+(?:email|ema[a-z]+|email address|email adddress)\s+(\S+)',
    r'(?:email|ema[a-z]+|email address|email adddress)\s+(\S+)'
]
PASSWORD_PATTERN = r'(?:enter|input|type|fill|use)\s+(?:the\s+)?(?:password|pass|passwd|pwd|pword|oassword)\s+(\S+)'
LOGIN_PATTERNS = [
    r'login with email\s+(\S+)\s+and password\s+(\S+)',
    r'log[a-z]* w[a-z]* (?:email|email address)?\s+(\S+)\s+[a-z]* (?:password|pass|p[a-z]*)\s+(\S+)',
    r'login\s+(?:with|using|w[a-z]*)\s+(?:email|email address)?\s*(\S+)\s+(?:and|with|[a-z]*)\s+(?:password|pass|p[a-z]*)\s*(\S+)',
    r'(?:login|sign in|signin)\s+(?:with|using|w[a-z]*)?\s*(?:email|username)?\s*(\S+)\s+(?:and|with|[a-z]*)\s*(?:password|pass|p[a-z]*)?\s*(\S+)',
    r'log[a-z]*.*?(\S+@\S+).*?(\S+)'
]

# Order selectors - these are used with string formatting to insert the order_id
ORDER_SELECTORS = [
    # Specific selectors for the observed UI structure
    'p.srch-cand-text1:has-text("ORDER-ID {}")',
    'p:has-text("ORDER-ID {}")',
    'tr:has-text("ORDER-ID {}")',
    'div.srch-cand-card:has-text("ORDER-ID {}")',
    'tr.p-selectable-row:has-text("{}")',

    # More specific selectors for the exact text
    'p:text("ORDER-ID {}")',
    'p:text-is("ORDER-ID {}")',
    'p:text-matches("ORDER-ID\\s+{}")',

    # Target the row containing the order ID
    'tr:has(p:has-text("ORDER-ID {}"))',
    'tr:has(div:has-text("ORDER-ID {}"))',
    'tr:has(p:text("ORDER-ID {}"))',

    # Target the clickable card
    'div.srch-cand-card:has(p:has-text("ORDER-ID {}"))',
    'div.srch-cand-card:has(p:text("ORDER-ID {}"))',

    # Generic selectors as fallbacks
    '#order-{}',
    '.order-row[data-order-id="{}"]',
    'tr[data-order-id="{}"]',
    'div[data-order-id="{}"]',
    'li[data-order-id="{}"]',
    '*[id*="order"][id*="{}"]',
    '*[data-id="{}"]',
    '*[data-order="{}"]',
    '*[data-orderid="{}"]',
    '*[data-order-id="{}"]',
    '*:has-text("Order #{}")',
    '*:has-text("Order ID: {}")',
    '*:has-text("Order: {}")',
    'tr:has-text("{}")',
    'td:has-text("{}")',
    '[id="{}"]',
    '[data-id="{}"]',
    '[data-testid="order-{}"]',
    '[data-order="{}"]',
    '[data-orderid="{}"]',
    '[data-order-id="{}"]',
    'a:has-text("{}")',
    'button:has-text("{}")',
    'div:has-text("{}")',
    'span:has-text("{}")',
    'p:has-text("{}")',
    '*:has-text("{}")'
]

# Selectors
# Email selectors
EMAIL_SELECTORS = [
    '#floating_outlined3',  # Specific selector for redberyltest.in
    'input[id="floating_outlined3"]',
    'input[type="email"]',
    'input[name="email"]',
    'input[id*="email"]',
    'input[placeholder*="email"]',
    'input[type="text"][name*="user"]',
    'input[id*="user"]',
    'input',  # Generic fallback
    'input[type="text"]',
    'form input:first-child',
    'form input',
    '.form-control',
    'input.form-control',
    'input[autocomplete="email"]',
    'input[autocomplete="username"]'
]

# Password selectors
PASSWORD_SELECTORS = [
    '#floating_outlined15',  # Specific selector for redberyltest.in
    'input[id="floating_outlined15"]',
    'input[type="password"]',
    'input[name="password"]',
    'input[id*="password"]',
    'input[placeholder*="password"]',
    'input.password',
    '#password',
    '[aria-label*="password"]',
    '[data-testid*="password"]',
    'input[autocomplete="current-password"]',
    'input[autocomplete="new-password"]',
    'form input[type="password"]',
    'form input:nth-child(2)'
]

# Login button selectors
LOGIN_BUTTON_SELECTORS = [
    '#signInButton',  # Specific selector for redberyltest.in
    'button[id="signInButton"]',
    '#loginBtn',
    '#signinBtn',
    '#login-button',
    '#signin-button',
    'button[type="submit"]',
    'input[type="submit"]',
    'button[name="login"]',
    'button[name="signin"]',
    'button[value="Login"]',
    'button[value="Sign in"]',
    'input[type="submit"][value="Login"]',
    'input[type="submit"][value="Sign in"]',
    'button:has-text("Login")',
    'button:has-text("Sign in")',
    'button:has-text("Log in")',
    'button:has-text("Signin")',
    'a:has-text("Login")',
    'a:has-text("Sign in")',
    'a:has-text("Log in")',
    'a:has-text("Signin")',
    '.login-button',
    '.signin-button',
    '.submit-button',
    '[data-testid="login-button"]',
    '[data-testid="signin-button"]',
    '[data-testid="submit-button"]',
    'a[href="/login"]',
    'a[href="/signin"]',
    'a[href="login"]',
    'a[href="signin"]',
    'button',  # Generic fallback
    'input[type="button"]'
]

# Login link selectors
LOGIN_LINK_SELECTORS = [
    'a:has-text("Login")',
    'a:has-text("Sign in")',
    'button:has-text("Login")',
    'button:has-text("Sign in")',
    '.login-button',
    '.signin-button',
    'button.blue-btnnn:has-text("Login/Register")',
    'a:has-text("Login/Register")'
]

# State dropdown selectors
STATE_DROPDOWN_SELECTORS = [
    '.p-dropdown:has-text("Select State")',
    '.p-dropdown:has-text("State")',
    '.p-dropdown-label:has-text("Select State")',
    'div[aria-label="State"]',
    'div[aria-label="Select State"]',
    'div.p-dropdown',
    'div.state-dropdown',
    '[data-testid="state-dropdown"]'
]

# State filter selectors
STATE_FILTER_SELECTORS = [
    '.p-dropdown-filter',
    'input.p-inputtext',
    'input[type="text"]',
    '.p-dropdown-panel input',
    'input.p-dropdown-filter'
]

# Help text
HELP_TEXT = """
Available commands:
- 'go to [website]' or 'navigate to [website]': Navigate to a website
- 'search for [query]': Search for something on the current page
- 'search for state [state name]': Search for a state in a dropdown
- 'click [element]': Click on an element on the page
- 'click [name] tab': Click on a tab with the given name
- 'fill [field] with [value]': Fill a form field
- 'select [option] from [dropdown]': Select an option from a dropdown
- 'submit' or 'submit form': Submit the current form
- 'scroll down/up': Scroll the page
- 'login' or 'click login button': Find and click the login button
- 'enter email [email]': Fill in the email field
- 'enter password [password]': Fill in the password field
- 'login with email [email] and password [password]': Fill in login form and submit
- 'voice' or 'switch to voice mode': Switch to voice input mode
- 'text' or 'switch to text mode': Switch to text input mode
- 'help': Show this help message
- 'exit' or 'quit': Exit the program
"""

# JavaScript snippets
JS_FIND_STATE_DROPDOWN = """
() => {
    // Try to find dropdown by text content
    const dropdownElements = Array.from(document.querySelectorAll('.p-dropdown, div[role="combobox"]'))
        .filter(el => {
            const text = el.textContent.toLowerCase();
            return text.includes('state') || text.includes('select state');
        });

    if (dropdownElements.length > 0) {
        console.log('Found state dropdown via JavaScript:', dropdownElements[0].outerHTML);
        dropdownElements[0].click();
        return true;
    }

    console.log('No state dropdown found via JavaScript');
    return false;
}
"""

JS_FIND_STATE_FILTER = """
(stateName) => {
    // Try to find filter input
    const filterInputs = Array.from(document.querySelectorAll('input.p-dropdown-filter, .p-dropdown-panel input, input.p-inputtext'));

    if (filterInputs.length > 0) {
        console.log('Found filter input via JavaScript:', filterInputs[0].outerHTML);
        filterInputs[0].value = stateName;
        filterInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
        filterInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    console.log('No filter input found via JavaScript');
    return false;
}
"""

JS_FIND_STATE_ITEM = """
(stateName) => {
    // Try to find state item by text content
    const stateItems = Array.from(document.querySelectorAll('.p-dropdown-item, li[role="option"], .p-dropdown-items li'))
        .filter(el => {
            const text = el.textContent.toLowerCase();
            return text.includes(stateName.toLowerCase());
        });

    if (stateItems.length > 0) {
        console.log('Found state item via JavaScript:', stateItems[0].outerHTML);
        stateItems[0].click();
        return true;
    }

    console.log('No state item found via JavaScript');
    return false;
}
"""

JS_FIND_TAB = """
(tabName) => {
    // Try to find tab by text content
    const tabElements = Array.from(document.querySelectorAll('li, a, button, [role="tab"], .nav-item, .tab'))
        .filter(el =>
            el.textContent.toLowerCase().includes(tabName.toLowerCase()) &&
            (window.getComputedStyle(el).display !== 'none') &&
            (window.getComputedStyle(el).visibility !== 'hidden')
        );

    if (tabElements.length > 0) {
        console.log('Found tab element via JavaScript:', tabElements[0].outerHTML);
        tabElements[0].click();
        return true;
    }

    // Try to find by ID or class
    const idElements = document.querySelectorAll(`#${tabName.toLowerCase()}-tab, .${tabName.toLowerCase()}-tab`);
    if (idElements.length > 0) {
        console.log('Found tab by ID/class:', idElements[0].outerHTML);
        idElements[0].click();
        return true;
    }

    console.log('No tab element found via JavaScript');
    return false;
}
"""

# JavaScript for finding login link
JS_FIND_LOGIN_LINK = """
() => {
    // Try to find login link by text content or href
    const loginTexts = ['log in', 'login', 'sign in', 'signin', 'account'];

    // Check links
    const links = Array.from(document.querySelectorAll('a'));
    for (const link of links) {
        const text = link.textContent.toLowerCase();
        const href = link.getAttribute('href') || '';

        if (loginTexts.some(loginText => text.includes(loginText)) ||
            loginTexts.some(loginText => href.includes(loginText))) {
            console.log('Clicking login link: ' + link.outerHTML);
            link.click();
            return true;
        }
    }

    // Check buttons
    const buttons = Array.from(document.querySelectorAll('button'));
    for (const button of buttons) {
        const text = button.textContent.toLowerCase();
        if (loginTexts.some(loginText => text.includes(loginText))) {
            console.log('Clicking login button: ' + button.outerHTML);
            button.click();
            return true;
        }
    }

    // Check any element with login text that seems clickable
    const allElements = Array.from(document.querySelectorAll('*'));
    for (const el of allElements) {
        const text = el.textContent.toLowerCase();
        if (loginTexts.some(loginText => text.includes(loginText)) &&
            (el.onclick || el.getAttribute('role') === 'button' ||
             el.tagName === 'DIV' || el.tagName === 'SPAN')) {
            console.log('Clicking element with login text: ' + el.outerHTML);
            el.click();
            return true;
        }
    }

    // Try to find the login button by its class for redberyltest.in
    const blueButton = document.querySelector('button.blue-btnnn');
    if (blueButton) {
        console.log('Clicking blue button: ' + blueButton.outerHTML);
        blueButton.click();
        return true;
    }

    console.log('No login link found');
    return false;
}
"""

# JavaScript for filling email field
JS_FILL_EMAIL = """
(email) => {
    // Try to find email input by various attributes
    let emailInputs = Array.from(document.querySelectorAll('input')).filter(el =>
        el.type === 'email' ||
        el.name === 'email' ||
        el.id === 'email' ||
        (el.placeholder && el.placeholder.toLowerCase().includes('email')) ||
        el.id === 'floating_outlined3' ||
        (el.labels && Array.from(el.labels).some(label => label.textContent.toLowerCase().includes('email')))
    );

    // If no email inputs found, try any visible text/password input
    if (emailInputs.length === 0) {
        emailInputs = Array.from(document.querySelectorAll('input')).filter(el =>
            (el.type === 'text' || !el.type || el.type === '') &&
            el.offsetParent !== null
        );
    }

    // If still no inputs found, try any input
    if (emailInputs.length === 0) {
        emailInputs = Array.from(document.querySelectorAll('input')).filter(el =>
            el.type !== 'hidden' && el.type !== 'submit' && el.type !== 'button'
        );
    }

    if (emailInputs.length > 0) {
        emailInputs[0].value = email;
        emailInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
        emailInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
        console.log('Filled input with JavaScript: ' + emailInputs[0].outerHTML);
        return true;
    }

    console.log('No suitable input field found');
    return false;
}
"""

# JavaScript for checking login errors
JS_CHECK_LOGIN_ERRORS = """
() => {
    const errorTexts = [
        'invalid email',
        'invalid password',
        'incorrect email',
        'incorrect password',
        'wrong email',
        'wrong password',
        'email not found',
        'password incorrect',
        'login failed',
        'authentication failed',
        'error',
        'failed'
    ];

    // Check for error messages
    const allElements = document.querySelectorAll('*');

    for (const element of allElements) {
        if (element.offsetParent !== null) { // Check if visible
            const text = element.textContent.trim().toLowerCase();
            if (text && errorTexts.some(errorText => text.includes(errorText))) {
                return element.textContent.trim();
            }
        }
    }

    return null;
}
"""

# JavaScript for checking input fields
JS_CHECK_INPUT_FIELDS = """
() => {
    // Check for specific elements we know exist in the form
    const emailField = document.getElementById('floating_outlined3');
    const passwordField = document.getElementById('floating_outlined15');
    const signInButton = document.getElementById('signInButton');

    // Check for any input elements
    const inputs = document.querySelectorAll('input');
    const forms = document.querySelectorAll('form');

    // Log what we found for debugging
    console.log('DOM inspection results:', {
        emailField: emailField ? true : false,
        passwordField: passwordField ? true : false,
        signInButton: signInButton ? true : false,
        inputCount: inputs.length,
        formCount: forms.length
    });

    // Return detailed information about what we found
    return {
        hasEmailField: emailField ? true : false,
        hasPasswordField: passwordField ? true : false,
        hasSignInButton: signInButton ? true : false,
        inputCount: inputs.length,
        formCount: forms.length,

        // Include details about inputs for debugging
        inputs: Array.from(inputs).slice(0, 5).map(input => ({
            id: input.id,
            type: input.type,
            name: input.name,
            placeholder: input.placeholder
        }))
    };
}
"""

# Service checkbox selectors
SERVICE_CHECKBOX_SELECTORS = [
    '.wizard-card-checkbox-container',
    '.wizard-card-checkbox-main',
    '.wizard-card-checkbox-text1',
    '.p-checkbox'
]

# Service name patterns
SERVICE_NAME_PATTERNS = {
    "ein": ["ein"],
    "good standing": ["cgs-good standing", "good standing", "cgs"],
    "articles of organization": ["articles of organization", "articles"],
    "s-election": ["s - election", "s-election", "s election"],
    "corporate kit": ["corporate kit", "corp kit"],
    "registered agent": ["registered agent", "initial registered agent"]
}

# Payment option selectors
PAYMENT_OPTION_SELECTORS = [
    'section > div:has-text("Pay now")',
    'section > div:has-text("Pay later")',
    '.p-checkbox'
]

# Billing info dropdown selectors
BILLING_INFO_DROPDOWN_SELECTORS = [
    "#RA_Billing_Information",
    "div[id='RA_Billing_Information']",
    ".p-dropdown:has-text('Select Billing Info')",
    ".p-dropdown-label:has-text('Billing Info')",
    "div.p-dropdown:has(.p-dropdown-label:has-text('Billing Info'))",
    "span.p-float-label:has(div#RA_Billing_Information)",
    "div.field:has(label:has-text('Select Billing Info')) .p-dropdown",
    "div.field:has(label:has-text('Billing Info')) .p-dropdown"
]

# Organizer dropdown selectors
ORGANIZER_DROPDOWN_SELECTORS = [
    '#Organizer',
    'div[id="Organizer"]',
    '.p-dropdown:has-text("Select Organizer")',
    '.p-dropdown-label:has-text("Organizer")',
    'div.p-dropdown:has(.p-dropdown-label:has-text("Organizer"))',
    'span.p-float-label:has(div#Organizer)',
    'div.field:has(label:has-text("Select Organizer")) .p-dropdown',
    'div.field:has(label:has-text("Organizer")) .p-dropdown'
]

# Add organizer button selectors
ADD_ORGANIZER_BUTTON_SELECTORS = [
    'button:has-text("Add Organizer")',
    '.p-button:has-text("Add Organizer")',
    'button.p-button:has(.p-button-label:has-text("Add Organizer"))',
    'button.vstate-button:has-text("Add Organizer")',
    'button[aria-label="Add Organizer"]',
    '.p-button:has(.pi-plus):has-text("Add Organizer")'
]

# Member checkbox selectors
MEMBER_CHECKBOX_SELECTORS = [
    '.p-datatable-tbody > tr',
    '.p-datatable-tbody > tr td:first-child',
    '.p-datatable-tbody > tr td:first-child .p-checkbox',
    '.srch-cand-checkbox .p-checkbox'
]

# Member/Manager dropdown selectors
MEMBER_MANAGER_DROPDOWN_SELECTORS = [
    '.p-datatable-tbody > tr td:nth-child(2) .p-dropdown',
    '.p-dropdown:has(.p-dropdown-label:has-text("Member"))',
    '.p-dropdown:has(.p-dropdown-label:has-text("Manager"))'
]

# Add Member/Manager button selectors
ADD_MEMBER_MANAGER_BUTTON_SELECTORS = [
    'button:has-text("Add Member Or Manager")',
    '.p-button:has-text("Add Member Or Manager")',
    'button.p-button:has(.p-button-label:has-text("Add Member Or Manager"))',
    'button.vstate-button:has-text("Add Member Or Manager")',
    'button[aria-label="Add Member Or Manager"]',
    '.p-button:has(.pi-plus):has-text("Add Member Or Manager")'
]

# General checkbox selectors
CHECKBOX_SELECTORS = [
    ".p-checkbox",  # General PrimeNG checkbox class
    ".p-checkbox-box",  # PrimeNG checkbox box
    ".p-checkbox-icon",  # From the provided HTML
    "span.p-checkbox-icon",
    "input[type='checkbox']",
    ".p-checkbox input",
    "div.p-checkbox",
    "div.checkbox",
    "label.checkbox",
    "[role='checkbox']",
    ".form-check-input",
    ".custom-control-input"
]

# JavaScript for finding and clicking service checkboxes
JS_FIND_SERVICE_CHECKBOX = """
(patterns) => {
    // Find all checkbox containers
    const checkboxContainers = document.querySelectorAll('.wizard-card-checkbox-container');
    console.log('Found', checkboxContainers.length, 'checkbox containers');

    for (const container of checkboxContainers) {
        // Get the service name text
        const serviceTextElement = container.querySelector('.wizard-card-checkbox-text1');
        if (!serviceTextElement) continue;

        const serviceText = serviceTextElement.textContent.toLowerCase();
        console.log('Checking service:', serviceText);

        // Check if this service matches any of our patterns
        const isMatch = patterns.some(pattern => serviceText.includes(pattern));

        if (isMatch) {
            console.log('Found matching service:', serviceText);

            // Find the checkbox within this container
            const checkbox = container.querySelector('.p-checkbox');
            if (checkbox) {
                // Check if it's already checked and disabled
                const isDisabled = checkbox.classList.contains('p-checkbox-disabled');
                if (isDisabled) {
                    console.log('Checkbox is disabled, cannot click');
                    return { success: false, reason: 'disabled' };
                }

                // Check if it's already checked
                const isChecked = checkbox.classList.contains('p-checkbox-checked');
                if (isChecked) {
                    console.log('Checkbox is already checked');
                    return { success: true, reason: 'already_checked' };
                }

                // Click the checkbox
                checkbox.click();
                console.log('Clicked checkbox');
                return { success: true, reason: 'clicked' };
            } else {
                console.log('No checkbox found in container');
            }
        }
    }

    return { success: false, reason: 'not_found' };
}
"""

# JavaScript for finding and clicking payment options
JS_FIND_PAYMENT_OPTION = """
(option) => {
    // Find all payment option sections
    const sections = document.querySelectorAll('section > div');
    console.log('Found', sections.length, 'payment sections');

    for (const section of sections) {
        // Get the text content
        const textContent = section.textContent.trim();
        console.log('Checking section:', textContent);

        // Check if this section matches our option
        if (textContent.includes(option)) {
            console.log('Found matching payment option:', textContent);

            // Find the checkbox within this section
            const checkbox = section.querySelector('.p-checkbox');
            if (checkbox) {
                // Check if it's already checked
                const isChecked = checkbox.classList.contains('p-checkbox-checked');
                if (isChecked) {
                    console.log('Checkbox is already checked');
                    return { success: true, reason: 'already_checked' };
                }

                // Click the checkbox
                checkbox.click();
                console.log('Clicked checkbox');
                return { success: true, reason: 'clicked' };
            } else {
                console.log('No checkbox found in section');
            }
        }
    }

    return { success: false, reason: 'not_found' };
}
"""

# JavaScript for finding and clicking billing info dropdown
JS_FIND_BILLING_INFO_DROPDOWN = """
() => {
    // Try to find by ID
    const byId = document.getElementById('RA_Billing_Information');
    if (byId) {
        console.log('Found billing info dropdown by ID');
        byId.click();
        return true;
    }

    // Try to find by text content
    const labels = Array.from(document.querySelectorAll('label'));
    for (const label of labels) {
        if (label.textContent.includes('Billing Info') || label.textContent.includes('Select Billing')) {
            const field = label.closest('.field');
            if (field) {
                const dropdown = field.querySelector('.p-dropdown');
                if (dropdown) {
                    console.log('Found billing info dropdown by label text');
                    dropdown.click();
                    return true;
                }
            }
        }
    }

    // Try to find any dropdown with billing text
    const dropdowns = document.querySelectorAll('.p-dropdown');
    for (const dropdown of dropdowns) {
        const label = dropdown.textContent.toLowerCase();
        if (label.includes('billing') || label.includes('bill')) {
            console.log('Found billing info dropdown by text content');
            dropdown.click();
            return true;
        }
    }

    return false;
}
"""

# JavaScript for finding and clicking organizer dropdown
JS_FIND_ORGANIZER_DROPDOWN = """
() => {
    // Try to find by ID
    const byId = document.getElementById('Organizer');
    if (byId) {
        console.log('Found organizer dropdown by ID');
        byId.click();
        return true;
    }

    // Try to find by text content
    const labels = Array.from(document.querySelectorAll('label'));
    for (const label of labels) {
        if (label.textContent.includes('Select Organizer')) {
            const field = label.closest('.field');
            if (field) {
                const dropdown = field.querySelector('.p-dropdown');
                if (dropdown) {
                    console.log('Found organizer dropdown by label text');
                    dropdown.click();
                    return true;
                }
            }
        }
    }

    // Try to find any dropdown with organizer text
    const dropdowns = document.querySelectorAll('.p-dropdown');
    for (const dropdown of dropdowns) {
        const label = dropdown.textContent.toLowerCase();
        if (label.includes('organizer')) {
            console.log('Found organizer dropdown by text content');
            dropdown.click();
            return true;
        }
    }

    return false;
}
"""

# JavaScript for finding and clicking add organizer button
JS_FIND_ADD_ORGANIZER_BUTTON = """
() => {
    // Try to find by aria-label
    const buttons = document.querySelectorAll('button');
    for (const button of buttons) {
        if (button.getAttribute('aria-label') === 'Add Organizer') {
            console.log('Found add organizer button by aria-label');
            button.click();
            return true;
        }
    }

    // Try to find by text content
    const addButtons = Array.from(document.querySelectorAll('button'));
    for (const button of addButtons) {
        if (button.textContent.includes('Add Organizer')) {
            console.log('Found add organizer button by text content');
            button.click();
            return true;
        }
    }

    // Try to find by class and icon
    const plusButtons = document.querySelectorAll('.p-button');
    for (const button of plusButtons) {
        if (button.querySelector('.pi-plus') &&
            button.textContent.toLowerCase().includes('organizer')) {
            console.log('Found add organizer button by class and icon');
            button.click();
            return true;
        }
    }

    return false;
}
"""

# JavaScript for finding and clicking member checkbox
JS_FIND_MEMBER_CHECKBOX = """
(rowIndex) => {
    // Find all rows in the member table
    const rows = document.querySelectorAll('.p-datatable-tbody > tr');
    console.log('Found', rows.length, 'member rows');

    if (rowIndex >= rows.length) {
        console.log('Row index out of bounds');
        return { success: false, reason: 'out_of_bounds' };
    }

    const row = rows[rowIndex];

    // Find the checkbox within this row
    const checkboxCell = row.querySelector('td:first-child');
    if (!checkboxCell) {
        console.log('No checkbox cell found in row');
        return { success: false, reason: 'no_cell' };
    }

    const checkbox = checkboxCell.querySelector('.p-checkbox');
    if (checkbox) {
        // Check if it's already checked
        const isChecked = checkbox.classList.contains('p-checkbox-checked');
        if (isChecked) {
            console.log('Checkbox is already checked');
            return { success: true, reason: 'already_checked' };
        }

        // Click the checkbox
        checkbox.click();
        console.log('Clicked checkbox');
        return { success: true, reason: 'clicked' };
    } else {
        console.log('No checkbox found in cell');
        return { success: false, reason: 'no_checkbox' };
    }
}
"""

# JavaScript for finding member by name and clicking their checkbox
JS_FIND_MEMBER_BY_NAME = """
(memberName) => {
    // Normalize the member name for comparison
    const memberNameLower = memberName.toLowerCase();
    console.log('Looking for member with name:', memberNameLower);

    // Find all rows in the member table
    const rows = document.querySelectorAll('.p-datatable-tbody > tr');
    console.log('Found', rows.length, 'member rows');

    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];

        // Get the name cell (3rd column)
        const nameCell = row.querySelector('td:nth-child(3)');
        if (!nameCell) continue;

        const name = nameCell.textContent.trim().toLowerCase();
        console.log('Checking row', i, 'with name:', name);

        // Check if this is the member we're looking for
        if (name.includes(memberNameLower)) {
            console.log('Found matching member:', name);

            // Find the checkbox within this row
            const checkboxCell = row.querySelector('td:first-child');
            if (!checkboxCell) {
                console.log('No checkbox cell found in row');
                continue;
            }

            const checkbox = checkboxCell.querySelector('.p-checkbox');
            if (checkbox) {
                // Check if it's already checked
                const isChecked = checkbox.classList.contains('p-checkbox-checked');
                if (isChecked) {
                    console.log('Checkbox is already checked');
                    return { success: true, reason: 'already_checked', rowIndex: i };
                }

                // Click the checkbox
                checkbox.click();
                console.log('Clicked checkbox');
                return { success: true, reason: 'clicked', rowIndex: i };
            } else {
                console.log('No checkbox found in cell');
            }
        }
    }

    return { success: false, reason: 'not_found' };
}
"""

# JavaScript for setting member/manager dropdown value
JS_SET_MEMBER_MANAGER_TYPE = """
(rowIndex, type) => {
    // Find all rows in the member table
    const rows = document.querySelectorAll('.p-datatable-tbody > tr');
    console.log('Found', rows.length, 'member rows');

    if (rowIndex >= rows.length) {
        console.log('Row index out of bounds');
        return { success: false, reason: 'out_of_bounds' };
    }

    const row = rows[rowIndex];

    // Find the dropdown within this row (2nd column)
    const dropdownCell = row.querySelector('td:nth-child(2)');
    if (!dropdownCell) {
        console.log('No dropdown cell found in row');
        return { success: false, reason: 'no_cell' };
    }

    const dropdown = dropdownCell.querySelector('.p-dropdown');
    if (!dropdown) {
        console.log('No dropdown found in cell');
        return { success: false, reason: 'no_dropdown' };
    }

    // Check current value
    const currentValue = dropdown.querySelector('.p-dropdown-label').textContent.trim();
    console.log('Current dropdown value:', currentValue);

    if (currentValue.toLowerCase() === type.toLowerCase()) {
        console.log('Dropdown already set to', type);
        return { success: true, reason: 'already_set' };
    }

    // Click to open dropdown
    dropdown.click();
    console.log('Clicked dropdown to open');

    // Wait a bit for the dropdown panel to appear
    setTimeout(() => {
        // Find the dropdown panel
        const panel = document.querySelector('.p-dropdown-panel');
        if (!panel) {
            console.log('Dropdown panel not found');
            return { success: false, reason: 'no_panel' };
        }

        // Find the option with the desired type
        const option = Array.from(panel.querySelectorAll('li.p-dropdown-item')).find(
            item => item.textContent.trim().toLowerCase() === type.toLowerCase()
        );

        if (!option) {
            console.log('Option not found in dropdown');
            return { success: false, reason: 'no_option' };
        }

        // Click the option
        option.click();
        console.log('Clicked option:', type);
        return { success: true, reason: 'clicked' };
    }, 500);

    return { success: true, reason: 'pending' };
}
"""

# JavaScript for finding and clicking Add Member/Manager button
JS_FIND_ADD_MEMBER_MANAGER_BUTTON = """
() => {
    // Try to find by aria-label
    const buttons = document.querySelectorAll('button');
    for (const button of buttons) {
        if (button.getAttribute('aria-label') === 'Add Member Or Manager') {
            console.log('Found add member/manager button by aria-label');
            button.click();
            return true;
        }
    }

    // Try to find by text content
    const addButtons = Array.from(document.querySelectorAll('button'));
    for (const button of addButtons) {
        if (button.textContent.includes('Add Member Or Manager')) {
            console.log('Found add member/manager button by text content');
            button.click();
            return true;
        }
    }

    // Try to find by class and icon
    const plusButtons = document.querySelectorAll('.p-button');
    for (const button of plusButtons) {
        if (button.querySelector('.pi-plus') &&
            button.textContent.toLowerCase().includes('member or manager')) {
            console.log('Found add member/manager button by class and icon');
            button.click();
            return true;
        }
    }

    return false;
}
"""

# JavaScript for finding and clicking a named checkbox
JS_FIND_NAMED_CHECKBOX = """
(checkboxName) => {
    const checkboxNameLower = checkboxName.toLowerCase();
    console.log('Looking for checkbox with name:', checkboxNameLower);

    // Method 1: Find by associated label text
    const labels = Array.from(document.querySelectorAll('label'));
    for (const label of labels) {
        if (label.offsetParent !== null && label.textContent.toLowerCase().includes(checkboxNameLower)) {
            console.log('Found label with matching text:', label.textContent);

            // Try to find the checkbox associated with this label
            const forId = label.getAttribute('for');
            if (forId) {
                const input = document.getElementById(forId);
                if (input && (input.type === 'checkbox' || input.classList.contains('p-checkbox'))) {
                    console.log('Found checkbox by label for attribute');
                    input.click();
                    return true;
                }
            }

            // Check if the label contains a checkbox
            const containedCheckbox = label.querySelector('input[type="checkbox"], .p-checkbox');
            if (containedCheckbox) {
                console.log('Found checkbox within label');
                containedCheckbox.click();
                return true;
            }

            // If we found a matching label but no checkbox, try clicking the label itself
            console.log('Clicking the label itself');
            label.click();
            return true;
        }
    }

    // Method 2: Find checkbox near text matching the name
    const textNodes = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while (node = walker.nextNode()) {
        if (node.textContent.toLowerCase().includes(checkboxNameLower)) {
            textNodes.push(node);
        }
    }

    for (const textNode of textNodes) {
        // Look for checkboxes near this text node
        let element = textNode.parentElement;
        for (let i = 0; i < 5; i++) { // Check up to 5 levels up
            if (!element) break;

            // Check for checkboxes within this element
            const nearbyCheckbox = element.querySelector('input[type="checkbox"], .p-checkbox, .p-checkbox-box, .p-checkbox-icon');
            if (nearbyCheckbox) {
                console.log('Found checkbox near matching text');
                nearbyCheckbox.click();
                return true;
            }

            element = element.parentElement;
        }
    }

    // Method 3: Try to find checkbox by name, id, or aria-label attributes
    const checkboxSelectors = [
        `input[name="${checkboxNameLower}"]`,
        `input[id*="${checkboxNameLower}"]`,
        `input[aria-label*="${checkboxNameLower}"]`,
        `[role="checkbox"][aria-label*="${checkboxNameLower}"]`,
        `.p-checkbox[aria-label*="${checkboxNameLower}"]`
    ];

    for (const selector of checkboxSelectors) {
        const element = document.querySelector(selector);
        if (element && element.offsetParent !== null) {
            console.log('Found checkbox by attribute selector:', selector);
            element.click();
            return true;
        }
    }

    return false;
}
"""

# JavaScript for finding and clicking any checkbox
JS_FIND_ANY_CHECKBOX = """
() => {
    // Try to find checkboxes by various methods

    // Method 1: Find by class
    const checkboxes = document.querySelectorAll('.p-checkbox, .p-checkbox-box, .p-checkbox-icon, input[type="checkbox"]');
    for (const checkbox of checkboxes) {
        if (checkbox.offsetParent !== null) { // Check if visible
            console.log('Found checkbox by class');
            checkbox.click();
            return true;
        }
    }

    // Method 2: Find by role
    const roleCheckboxes = document.querySelectorAll('[role="checkbox"]');
    for (const checkbox of roleCheckboxes) {
        if (checkbox.offsetParent !== null) { // Check if visible
            console.log('Found checkbox by role');
            checkbox.click();
            return true;
        }
    }

    // Method 3: Find by common checkbox patterns
    const labels = document.querySelectorAll('label');
    for (const label of labels) {
        if (label.offsetParent !== null) { // Check if visible
            const input = label.querySelector('input[type="checkbox"]');
            if (input) {
                console.log('Found checkbox within label');
                input.click();
                return true;
            }

            // Check if the label itself is clickable and looks like a checkbox
            if (label.classList.contains('checkbox') ||
                label.classList.contains('p-checkbox') ||
                label.querySelector('.checkbox') ||
                label.querySelector('.p-checkbox')) {
                console.log('Found checkbox-like label');
                label.click();
                return true;
            }
        }
    }

    // Method 4: Look for any element that visually appears to be a checkbox
    const allElements = document.querySelectorAll('*');
    for (const el of allElements) {
        if (el.offsetParent !== null) { // Check if visible
            const style = window.getComputedStyle(el);
            // Check if it's a small square element that might be a checkbox
            if ((style.width === style.height) &&
                (parseInt(style.width) <= 24) &&
                (style.border !== 'none' || style.backgroundColor !== 'transparent')) {
                console.log('Found potential checkbox by appearance');
                el.click();
                return true;
            }
        }
    }

    return false;
}
"""

# JavaScript for finding and clicking orders
JS_FIND_ORDER = """
(orderId) => {
    try {
        console.log("Looking for order with ID: " + orderId);

        // First, try to find elements with the specific ORDER-ID format
        const orderIdFormat = "ORDER-ID " + orderId;
        console.log("Looking for elements with text: " + orderIdFormat);

        // Try to find elements with the exact ORDER-ID text
        const textElements = Array.from(document.querySelectorAll('*'));
        for (const el of textElements) {
            if (el.textContent.includes(orderIdFormat)) {
                console.log('Found element with ORDER-ID text:', el.outerHTML);

                // Find the closest clickable parent
                let target = el;

                // First try to find a row (tr) or card (div.srch-cand-card)
                let row = el.closest('tr');
                if (row) {
                    console.log('Found row containing order ID:', row.outerHTML);
                    row.click();
                    return true;
                }

                let card = el.closest('div.srch-cand-card');
                if (card) {
                    console.log('Found card containing order ID:', card.outerHTML);
                    card.click();
                    return true;
                }

                // Check up to 5 levels of parents for clickable elements
                for (let i = 0; i < 5; i++) {
                    if (target.tagName === 'A' ||
                        target.tagName === 'BUTTON' ||
                        target.onclick ||
                        target.getAttribute('role') === 'button' ||
                        window.getComputedStyle(target).cursor === 'pointer' ||
                        target.tagName === 'TR' ||
                        target.tagName === 'TD' ||
                        target.tagName === 'DIV' ||
                        target.tagName === 'LI') {

                        console.log('Found clickable parent containing order ID:', target.outerHTML);
                        target.click();
                        return true;
                    }

                    if (target.parentElement) {
                        target = target.parentElement;
                    } else {
                        break;
                    }
                }

                // If we found the text but couldn't find a clickable parent, try clicking the text itself
                console.log('Clicking the element itself as last resort');
                el.click();
                return true;
            }
        }

        // Try data attributes that might contain the order ID
        const dataAttributes = [
            '[data-id="' + orderId + '"]',
            '[data-order-id="' + orderId + '"]',
            '[data-orderid="' + orderId + '"]',
            '[data-testid="order-' + orderId + '"]',
            '[data-order="' + orderId + '"]'
        ];

        for (const selector of dataAttributes) {
            const element = document.querySelector(selector);
            if (element) {
                console.log('Found element with data attribute:', selector);
                element.click();
                return true;
            }
        }

        // Try to find elements with ID containing the order ID
        const idSelectors = [
            '#order-' + orderId,
            '#' + orderId
        ];

        for (const selector of idSelectors) {
            const element = document.querySelector(selector);
            if (element) {
                console.log('Found element with ID:', selector);
                element.click();
                return true;
            }
        }

        // Try by any element containing the order ID
        const elements = Array.from(document.querySelectorAll('*'));
        for (const el of elements) {
            if (el.textContent.includes(orderId)) {
                // Check if this element or its parent is clickable
                let target = el;

                // Check up to 3 levels of parents
                for (let i = 0; i < 3; i++) {
                    if (target.tagName === 'A' ||
                        target.tagName === 'BUTTON' ||
                        target.onclick ||
                        target.getAttribute('role') === 'button' ||
                        window.getComputedStyle(target).cursor === 'pointer' ||
                        target.tagName === 'TR' ||
                        target.tagName === 'TD' ||
                        target.tagName === 'DIV' ||
                        target.tagName === 'LI') {

                        console.log('Found clickable element containing order ID:', target.outerHTML);
                        target.click();
                        return true;
                    }

                    if (target.parentElement) {
                        target = target.parentElement;
                    } else {
                        break;
                    }
                }
            }
        }

        console.log("Could not find order element");
        return false;
    } catch (error) {
        console.error("Error finding order:", error);
        return false;
    }
}
"""
