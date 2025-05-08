import re

class SelectionHandler:
    """Handles selection-related commands (dropdowns, checkboxes, etc.)"""

    def __init__(self, page, speak_func, llm_utils, browser_utils):
        """Initialize the selection handler

        Args:
            page: Playwright page object
            speak_func: Function to speak text
            llm_utils: LLM utilities for generating selectors and actions
            browser_utils: Browser utilities for common operations
        """
        self.page = page
        self.speak = speak_func
        self.llm_utils = llm_utils
        self.browser_utils = browser_utils

    async def handle_command(self, command):
        """Handle selection-related commands

        Args:
            command: User command string

        Returns:
            bool: True if command was handled, False otherwise
        """
        # Handle entity type selection command
        entity_type_match = re.search(r'(?:select|choose|pick)\s+(?:entity\s+type\s+)?(LLC|CORP|Corporation|Limited\s+Liability\s+Company)(?:\s+(?:as\s+entity\s+type|entity\s+type))?', command, re.IGNORECASE)
        if entity_type_match:
            entity_type = entity_type_match.group(1).strip()
            return await self._select_entity_type(entity_type)

        # Handle entity type dropdown command
        entity_dropdown_match = re.search(r'(?:click|select|open)(?:\s+(?:on|the))?\s+(?:entity\s+type)(?:\s+dropdown)?', command, re.IGNORECASE)
        if entity_dropdown_match:
            await self.speak("Looking for entity type dropdown...")
            # First ensure entity type is selected
            result = await self._ensure_entity_type_selected()
            if result:
                await self.speak("Entity type is already selected")
                return True
            else:
                # Try to click the entity type dropdown
                clicked = await self.page.evaluate("""() => {
                    const allDropdowns = document.querySelectorAll('.p-dropdown');
                    if (allDropdowns.length > 0) {
                        console.log("Clicking entity type dropdown (first dropdown)");
                        allDropdowns[0].click();
                        return true;
                    }
                    return false;
                }""")

                if clicked:
                    await self.speak("Clicked the entity type dropdown")
                    return True
                else:
                    await self.speak("Could not find entity type dropdown")
                    return False

        # Handle county selection command
        county_match = re.search(r'(?:select|choose|pick)\s+(?:county\s+)?([A-Za-z\s]+)(?:\s+(?:county|as\s+county))?', command, re.IGNORECASE)
        if county_match:
            county_name = county_match.group(1).strip()
            return await self._handle_county_selection(county_name)

        # Handle county dropdown command
        county_dropdown_match = re.search(r'(?:cl[ci]?[ck]k?|select|open)(?:\s+(?:on|the))?\s+(?:county)(?:\s+dropdown)?', command, re.IGNORECASE)
        if county_dropdown_match:
            await self.speak("Looking for county dropdown...")
            return await self._click_county_dropdown()

        # Handle state selection command
        state_match = re.search(r'(?:select|choose|pick)\s+(?:state\s+)?([A-Za-z\s]+)(?:\s+(?:state|as\s+state))?', command, re.IGNORECASE)
        if state_match:
            state_name = state_match.group(1).strip()
            return await self._handle_state_selection(state_name)

        # Handle state dropdown command
        state_dropdown_match = re.search(r'(?:click|select|open)\s+(?:the\s+)?state(?:\s+dropdown)?', command, re.IGNORECASE)
        if state_dropdown_match:
            await self.speak("Looking for state dropdown in address form...")
            # Try to click the state dropdown using label and placeholder
            clicked = await self.page.evaluate("""() => {
                // Try to find the dropdown by label 'State' and placeholder 'Select a State'
                const stateLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.trim() === 'Select a State');
                if (stateLabels.length > 0) {
                    const dropdownContainer = stateLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        dropdownContainer.click();
                        return true;
                    }
                }
                // Fallback: try by label text
                const labels = Array.from(document.querySelectorAll('label, span, div'))
                    .filter(el => el.textContent.trim().toLowerCase().includes('state'));
                for (const label of labels) {
                    let current = label;
                    while (current.nextElementSibling) {
                        current = current.nextElementSibling;
                        if (current.classList.contains('p-dropdown')) {
                            current.click();
                            return true;
                        }
                    }
                }
                // Fallback: try by position (second dropdown in address form)
                const dropdowns = document.querySelectorAll('.p-dropdown');
                if (dropdowns.length >= 2) {
                    dropdowns[1].click();
                    return true;
                }
                return false;
            }""")
            if clicked:
                await self.speak("Clicked the State dropdown in address form.")
                await self.page.wait_for_timeout(1000)
                return True
            else:
                await self.speak("Could not find the State dropdown in address form.")
                return False

        # Handle state dropdown command (formation state)
        state_dropdown_match = re.search(r'(?:cl[ci]?[ck]k?|select|open)(?:\s+(?:on|the))?\s+(?:state(?:\s+of\s+formation)?|formation\s+state|state\s+dropdown)(?:\s+dropdown)?', command, re.IGNORECASE)
        if state_dropdown_match:
            await self.speak("Looking for state of formation dropdown...")
            # Use the specialized method for state dropdown
            return await self._click_state_dropdown_direct()

        # Handle principal address dropdown command
        address_dropdown_match = re.search(r'(?:click|select|open)(?:\s+(?:on|the))?\s+(?:principal(?:\s+address)?|address)(?:\s+dropdown)?', command, re.IGNORECASE)
        if address_dropdown_match:
            await self.speak("Looking for principal address dropdown...")
            return await self._click_principal_address_dropdown()

        # Handle product checkbox commands
        product_match = re.search(r'(?:check|select)\s+(?:product\s+)?(.+?)(?:\s+product)?', command, re.IGNORECASE)
        if product_match:
            product_name = product_match.group(1).strip()
            if product_name.lower() == "all products":
                return await self._check_all_products()
            else:
                return await self._check_product_checkbox(product_name)

        return False

    async def _handle_state_selection(self, state_name):
        """Handle selecting a state from a dropdown"""
        await self.speak(f"Looking for state: {state_name}")
        try:
            # First click the state dropdown
            await self._click_state_dropdown_direct()

            # Wait for dropdown items to appear
            await self.page.wait_for_timeout(1000)

            # Select the state
            selected = await self.page.evaluate("""(stateName) => {
                // Find the dropdown item with matching text
                const items = Array.from(document.querySelectorAll('.p-dropdown-item'));
                console.log(`Found ${items.length} dropdown items`);

                // Log all available options for debugging
                items.forEach(item => console.log(`Option: ${item.textContent.trim()}`));

                // Try to find an exact match first
                let match = items.find(item =>
                    item.textContent.trim().toLowerCase() === stateName.toLowerCase()
                );

                // If no exact match, try partial match
                if (!match) {
                    match = items.find(item =>
                        item.textContent.trim().toLowerCase().includes(stateName.toLowerCase())
                    );
                }

                if (match) {
                    console.log(`Clicking state: ${match.textContent.trim()}`);
                    match.click();
                    return true;
                }

                return false;
            }""", state_name)

            if selected:
                await self.speak(f"Selected state: {state_name}")
                return True
            else:
                await self.speak(f"Could not find state: {state_name}")
                return False

        except Exception as e:
            print(f"Error selecting state: {e}")
            await self.speak(f"Error selecting state: {str(e)}")
            return False

    async def _click_state_dropdown_direct(self):
        """Click the state dropdown using direct DOM manipulation"""
        await self.speak("Looking for state dropdown...")
        try:
            # Use JavaScript to find and click the state dropdown
            clicked = await self.page.evaluate("""() => {
                console.log("Looking for state dropdown...");

                // First try to find by placeholder text "Select State"
                const stateLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.trim() === 'Select State' ||
                                 el.textContent.trim() === 'State' ||
                                 el.textContent.trim() === 'Select a State');

                console.log(`Found ${stateLabels.length} dropdown labels with state text`);

                if (stateLabels.length > 0) {
                    const dropdownContainer = stateLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        console.log("Clicking state dropdown by label text");
                        dropdownContainer.click();
                        return true;
                    }
                }

                // Try by label element
                const labels = Array.from(document.querySelectorAll('label'))
                    .filter(el => el.textContent.trim().toLowerCase().includes('state'));

                console.log(`Found ${labels.length} label elements with state text`);

                for (const label of labels) {
                    // Try to find dropdown in the same container
                    const parent = label.parentElement;
                    if (parent) {
                        const dropdown = parent.querySelector('.p-dropdown');
                        if (dropdown) {
                            console.log("Clicking state dropdown by label element");
                            dropdown.click();
                            return true;
                        }
                    }

                    // Try next sibling
                    let current = label;
                    while (current.nextElementSibling) {
                        current = current.nextElementSibling;
                        if (current.classList.contains('p-dropdown')) {
                            console.log("Clicking state dropdown by sibling relationship");
                            current.click();
                            return true;
                        }
                    }
                }

                // Fallback: try by position (second dropdown in form)
                const dropdowns = document.querySelectorAll('.p-dropdown');
                if (dropdowns.length >= 2) {
                    console.log("Clicking state dropdown by position (second dropdown)");
                    dropdowns[1].click();
                    return true;
                }

                console.log("Could not find state dropdown");
                return false;
            }""")

            if clicked:
                print("Successfully clicked state dropdown")
                return True
            else:
                print("Failed to click state dropdown using JavaScript")
                return False

        except Exception as e:
            print(f"Error clicking state dropdown: {e}")
            return False

    async def _click_county_dropdown(self):
        """Click the county dropdown using direct DOM manipulation"""
        await self.speak("Looking for county dropdown...")
        try:
            # Use JavaScript to find and click the county dropdown
            clicked = await self.page.evaluate("""() => {
                console.log("Looking for county dropdown...");

                // First try to find by placeholder text "Select County"
                const countyLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.trim() === 'Select County');

                console.log(`Found ${countyLabels.length} dropdown labels with county text`);

                if (countyLabels.length > 0) {
                    const dropdownContainer = countyLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        console.log("Clicking county dropdown by label text");
                        dropdownContainer.click();
                        return true;
                    }
                }

                // Try by label element
                const labels = Array.from(document.querySelectorAll('label'))
                    .filter(el => el.textContent.trim().toLowerCase().includes('county'));

                console.log(`Found ${labels.length} label elements with county text`);

                for (const label of labels) {
                    // Try to find dropdown in the same container
                    const parent = label.parentElement;
                    if (parent) {
                        const dropdown = parent.querySelector('.p-dropdown');
                        if (dropdown) {
                            console.log("Clicking county dropdown by label element");
                            dropdown.click();
                            return true;
                        }
                    }

                    // Try next sibling
                    let current = label;
                    while (current.nextElementSibling) {
                        current = current.nextElementSibling;
                        if (current.classList.contains('p-dropdown')) {
                            console.log("Clicking county dropdown by sibling relationship");
                            current.click();
                            return true;
                        }
                    }
                }

                // Try by position (third dropdown in form, after entity type and state)
                const dropdowns = document.querySelectorAll('.p-dropdown');
                if (dropdowns.length >= 3) {
                    console.log("Clicking county dropdown by position (third dropdown)");
                    dropdowns[2].click();
                    return true;
                }

                console.log("Could not find county dropdown");
                return false;
            }""")

            if clicked:
                print("Successfully clicked county dropdown")
                await self.speak("Clicked the county dropdown")
                await self.page.wait_for_timeout(1000)
                return True
            else:
                print("Failed to click county dropdown using JavaScript")
                await self.speak("Could not find county dropdown")
                return False

        except Exception as e:
            print(f"Error clicking county dropdown: {e}")
            await self.speak(f"Error clicking county dropdown: {str(e)}")
            return False

    async def _handle_county_selection(self, county_name):
        """Handle selecting a county from a dropdown"""
        await self.speak(f"Looking for county: {county_name}")
        try:
            # First click the county dropdown
            await self._click_county_dropdown()

            # Wait for dropdown items to appear
            await self.page.wait_for_timeout(1000)

            # Select the county
            selected = await self.page.evaluate("""(countyName) => {
                // Find the dropdown item with matching text
                const items = Array.from(document.querySelectorAll('.p-dropdown-item'));
                console.log(`Found ${items.length} dropdown items`);

                // Log all available options for debugging
                items.forEach(item => console.log(`Option: ${item.textContent.trim()}`));

                // Try to find an exact match first
                let match = items.find(item =>
                    item.textContent.trim().toLowerCase() === countyName.toLowerCase()
                );

                // If no exact match, try partial match
                if (!match) {
                    match = items.find(item =>
                        item.textContent.trim().toLowerCase().includes(countyName.toLowerCase())
                    );
                }

                if (match) {
                    console.log(`Clicking county: ${match.textContent.trim()}`);
                    match.click();
                    return true;
                }

                return false;
            }""", county_name)

            if selected:
                await self.speak(f"Selected county: {county_name}")
                return True
            else:
                await self.speak(f"Could not find county: {county_name}")
                return False

        except Exception as e:
            print(f"Error selecting county: {e}")
            await self.speak(f"Error selecting county: {str(e)}")
            return False

    async def _click_principal_address_dropdown(self):
        """Click the principal address dropdown"""
        await self.speak("Looking for principal address dropdown...")
        try:
            # Use JavaScript to find and click the principal address dropdown
            clicked = await self.page.evaluate("""() => {
                console.log("Looking for principal address dropdown...");

                // Try to find by placeholder text
                const addressLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.trim().includes('Address') ||
                                 el.textContent.trim().includes('Principal'));

                console.log(`Found ${addressLabels.length} dropdown labels with address text`);

                if (addressLabels.length > 0) {
                    const dropdownContainer = addressLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        console.log("Clicking address dropdown by label text");
                        dropdownContainer.click();
                        return true;
                    }
                }

                // Try by label element
                const labels = Array.from(document.querySelectorAll('label'))
                    .filter(el => el.textContent.trim().toLowerCase().includes('address') ||
                                 el.textContent.trim().toLowerCase().includes('principal'));

                console.log(`Found ${labels.length} label elements with address text`);

                for (const label of labels) {
                    // Try to find dropdown in the same container
                    const parent = label.parentElement;
                    if (parent) {
                        const dropdown = parent.querySelector('.p-dropdown');
                        if (dropdown) {
                            console.log("Clicking address dropdown by label element");
                            dropdown.click();
                            return true;
                        }
                    }

                    // Try next sibling
                    let current = label;
                    while (current.nextElementSibling) {
                        current = current.nextElementSibling;
                        if (current.classList.contains('p-dropdown')) {
                            console.log("Clicking address dropdown by sibling relationship");
                            current.click();
                            return true;
                        }
                    }
                }

                console.log("Could not find address dropdown");
                return false;
            }""")

            if clicked:
                print("Successfully clicked principal address dropdown")
                return True
            else:
                print("Failed to click principal address dropdown using JavaScript")
                return False

        except Exception as e:
            print(f"Error clicking principal address dropdown: {e}")
            return False

    async def _check_product_checkbox(self, product_name):
        """Specifically check a product checkbox from a product list

        Args:
            product_name: The name of the product to check
        """
        await self.speak(f"Looking for product checkbox for {product_name}...")
        try:
            # Use JavaScript to find and check the product checkbox
            checked = await self.page.evaluate("""(productName) => {
                console.log("Looking for product checkbox for:", productName);

                // Function to find product checkboxes by product name
                const findProductCheckbox = (name) => {
                    // Normalize the product name for comparison
                    const normalizedName = name.toLowerCase().trim();

                    // Find all product containers
                    const productContainers = document.querySelectorAll('.wizard-card-checkbox-container, .hover-card');
                    console.log(`Found ${productContainers.length} potential product containers`);

                    // Look through each container for matching product text
                    for (const container of productContainers) {
                        const containerText = container.textContent.toLowerCase();

                        // Check if this container has text matching our product name
                        if (containerText.includes(normalizedName)) {
                            console.log(`Found container with text matching "${name}"`);

                            // Look for checkbox in this container
                            const checkbox = container.querySelector('input[type="checkbox"]');
                            if (checkbox) {
                                console.log(`Found standard checkbox in container for "${name}"`);
                                return checkbox;
                            }

                            // Look for PrimeNG/PrimeReact checkbox
                            const primeCheckbox = container.querySelector('.p-checkbox');
                            if (primeCheckbox) {
                                console.log(`Found PrimeNG/React checkbox in container for "${name}"`);
                                return primeCheckbox;
                            }

                            // Look for any element with checkbox class
                            const checkboxElement = container.querySelector('[class*="checkbox"]');
                            if (checkboxElement) {
                                console.log(`Found element with checkbox class in container for "${name}"`);
                                return checkboxElement;
                            }
                        }
                    }

                    // If we couldn't find by container, try to find by proximity to text
                    const textElements = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent.toLowerCase().includes(normalizedName));

                    console.log(`Found ${textElements.length} elements containing "${name}" text`);

                    for (const element of textElements) {
                        // Look for checkbox in parent container
                        let parent = element;
                        let depth = 0;
                        const MAX_DEPTH = 5;

                        while (parent && depth < MAX_DEPTH) {
                            // Check for checkbox in this parent
                            const checkbox = parent.querySelector('input[type="checkbox"]');
                            if (checkbox) {
                                console.log(`Found checkbox in ancestor of "${name}" text`);
                                return checkbox;
                            }

                            // Check for PrimeNG/PrimeReact checkbox
                            const primeCheckbox = parent.querySelector('.p-checkbox');
                            if (primeCheckbox) {
                                console.log(`Found PrimeNG/React checkbox in ancestor of "${name}" text`);
                                return primeCheckbox;
                            }

                            parent = parent.parentElement;
                            depth++;
                        }
                    }

                    return null;
                };

                // Try to find the product checkbox
                const checkbox = findProductCheckbox(productName);

                if (checkbox) {
                    console.log(`Found checkbox for product "${productName}", clicking it`);

                    // For standard HTML checkboxes
                    if (checkbox.tagName === 'INPUT' && checkbox.type === 'checkbox') {
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                        checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                        checkbox.dispatchEvent(new Event('click', { bubbles: true }));
                        return true;
                    }

                    // For PrimeNG/PrimeReact checkboxes
                    if (checkbox.classList.contains('p-checkbox')) {
                        // Find the actual checkbox element inside the container
                        const checkboxBox = checkbox.querySelector('.p-checkbox-box');
                        if (checkboxBox) {
                            checkboxBox.click();
                        } else {
                            checkbox.click();
                        }
                        return true;
                    }

                    // For any other element that might be a checkbox
                    checkbox.click();
                    return true;
                }

                // If we couldn't find the specific product, try to find any unchecked product checkboxes
                const allProductCheckboxes = document.querySelectorAll('.wizard-card-checkbox-container input[type="checkbox"]:not(:checked), .wizard-card-checkbox-container .p-checkbox:not(.p-checkbox-checked)');
                console.log(`Found ${allProductCheckboxes.length} unchecked product checkboxes`);

                if (allProductCheckboxes.length > 0) {
                    console.log("Clicking first unchecked product checkbox");

                    // For standard HTML checkboxes
                    if (allProductCheckboxes[0].tagName === 'INPUT' && allProductCheckboxes[0].type === 'checkbox') {
                        allProductCheckboxes[0].checked = true;
                        allProductCheckboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
                        allProductCheckboxes[0].dispatchEvent(new Event('input', { bubbles: true }));
                        allProductCheckboxes[0].dispatchEvent(new Event('click', { bubbles: true }));
                        return true;
                    }

                    // For PrimeNG/PrimeReact checkboxes
                    if (allProductCheckboxes[0].classList.contains('p-checkbox')) {
                        const checkboxBox = allProductCheckboxes[0].querySelector('.p-checkbox-box');
                        if (checkboxBox) {
                            checkboxBox.click();
                        } else {
                            allProductCheckboxes[0].click();
                        }
                        return true;
                    }

                    // For any other element
                    allProductCheckboxes[0].click();
                    return true;
                }

                return false;
            }""", product_name)

            if checked:
                await self.speak(f"✓ Checked product {product_name}")
                return True
            else:
                await self.speak(f"Could not find product checkbox for {product_name}")
                return False
        except Exception as e:
            print(f"Error checking product checkbox: {e}")
            await self.speak(f"Error checking product checkbox for {product_name}")
            return False

    async def _check_all_products(self):
        """Check all product checkboxes in the product list"""
        await self.speak("Checking all available products...")
        try:
            # Use JavaScript to find and check all product checkboxes
            result = await self.page.evaluate("""() => {
                console.log("Looking for all product checkboxes");

                // Find all product containers
                const productContainers = document.querySelectorAll('.wizard-card-checkbox-container, .hover-card');
                console.log(`Found ${productContainers.length} potential product containers`);

                let checkedCount = 0;

                // Go through each container and check its checkbox
                for (const container of productContainers) {
                    // Look for checkbox in this container
                    const checkbox = container.querySelector('input[type="checkbox"]');
                    if (checkbox && !checkbox.checked) {
                        console.log(`Found and checking standard checkbox in container`);
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                        checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                        checkbox.dispatchEvent(new Event('click', { bubbles: true }));
                        checkedCount++;
                        continue;
                    }

                    // Look for PrimeNG/PrimeReact checkbox
                    const primeCheckbox = container.querySelector('.p-checkbox:not(.p-checkbox-checked)');
                    if (primeCheckbox) {
                        console.log(`Found and checking PrimeNG/React checkbox in container`);
                        // Find the actual checkbox element inside the container
                        const checkboxBox = primeCheckbox.querySelector('.p-checkbox-box');
                        if (checkboxBox) {
                            checkboxBox.click();
                        } else {
                            primeCheckbox.click();
                        }
                        checkedCount++;
                        continue;
                    }

                    // Look for any element with checkbox class
                    const checkboxElement = container.querySelector('[class*="checkbox"]');
                    if (checkboxElement) {
                        console.log(`Found and checking element with checkbox class in container`);
                        checkboxElement.click();
                        checkedCount++;
                    }
                }

                // If we didn't find any product containers, try a more generic approach
                if (productContainers.length === 0) {
                    console.log("No product containers found, trying generic checkboxes");

                    // Find all checkboxes that might be product checkboxes
                    const checkboxes = [];

                    // Look for PrimeNG/PrimeReact checkboxes
                    const primeCheckboxes = document.querySelectorAll('.p-checkbox');
                    console.log(`Found ${primeCheckboxes.length} PrimeNG/PrimeReact checkboxes`);
                    checkboxes.push(...primeCheckboxes);

                    // Look for standard checkboxes
                    const standardCheckboxes = document.querySelectorAll('input[type="checkbox"]');
                    console.log(`Found ${standardCheckboxes.length} standard checkboxes`);
                    checkboxes.push(...standardCheckboxes);

                    // Check all checkboxes
                    for (const checkbox of checkboxes) {
                        try {
                            // For PrimeNG/PrimeReact checkboxes
                            if (checkbox.classList && checkbox.classList.contains('p-checkbox')) {
                                // Only check if not already checked
                                const isChecked = checkbox.querySelector('.p-checkbox-checked');
                                if (!isChecked) {
                                    checkbox.click();
                                    checkedCount++;
                                }
                            }
                            // For standard checkboxes
                            else if (checkbox.type === 'checkbox') {
                                if (!checkbox.checked) {
                                    checkbox.checked = true;
                                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                    checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                                    checkbox.dispatchEvent(new Event('click', { bubbles: true }));
                                    checkedCount++;
                                }
                            }
                        } catch (error) {
                            console.error("Error checking checkbox:", error);
                        }
                    }
                }

                return {
                    success: checkedCount > 0,
                    count: checkedCount,
                    totalContainers: productContainers.length
                };
            }""")

            if result.get('success'):
                await self.speak(f"✓ Checked {result.get('count')} products out of {result.get('totalContainers')} found")
                return True
            else:
                await self.speak(f"Could not find any product checkboxes to check")
                return False
        except Exception as e:
            print(f"Error checking all product checkboxes: {e}")
            await self.speak(f"Error checking all product checkboxes")
            return False

    async def _click_generic_dropdown(self, dropdown_name):
        """Generic method to click any dropdown by name

        Args:
            dropdown_name: The name/label of the dropdown to click
        """
        await self.speak(f"Looking for {dropdown_name} dropdown...")
        try:
            # Use JavaScript to find and click the dropdown
            clicked = await self.page.evaluate("""(dropdownName) => {
                console.log(`Looking for dropdown: "${dropdownName}"`);

                // Normalize the dropdown name for comparison
                const normalizedName = dropdownName.toLowerCase().trim();

                // STRATEGY 1: Try to find by ID that contains the dropdown name
                // Convert dropdown name to possible ID formats
                const possibleIds = [
                    dropdownName.replace(/\\s+/g, '_'),  // spaces to underscores
                    dropdownName.replace(/\\s+/g, ''),   // remove spaces
                    dropdownName.replace(/\\s+/g, '-'),  // spaces to hyphens
                    // Add more ID patterns as needed
                ];

                for (const id of possibleIds) {
                    const dropdownById = document.getElementById(id);
                    if (dropdownById) {
                        console.log(`Found dropdown by ID: ${id}`);
                        dropdownById.click();
                        return true;
                    }

                    // Try case-insensitive ID search
                    const elementsWithIdAttr = document.querySelectorAll('[id]');
                    for (const el of elementsWithIdAttr) {
                        if (el.id.toLowerCase().includes(normalizedName)) {
                            console.log(`Found dropdown with ID containing "${normalizedName}": ${el.id}`);
                            el.click();
                            return true;
                        }
                    }
                }

                // STRATEGY 2: Try to find by text content
                // Find elements containing the dropdown name text
                const textElements = Array.from(document.querySelectorAll('label, span, div, p, h1, h2, h3, h4, h5, h6'))
                    .filter(el => el.textContent.toLowerCase().includes(normalizedName));

                console.log(`Found ${textElements.length} elements containing "${dropdownName}" text`);

                if (textElements.length > 0) {
                    // Try to find a dropdown near each label
                    for (const element of textElements) {
                        console.log(`Found element with text: "${element.textContent.trim()}"`);

                        // Check if this element is a label with a "for" attribute
                        const forAttribute = element.getAttribute('for');
                        if (forAttribute) {
                            const associatedElement = document.getElementById(forAttribute);
                            if (associatedElement) {
                                console.log(`Found associated element by ID: ${forAttribute}`);
                                associatedElement.click();
                                return true;
                            }
                        }

                        // Look for dropdown in parent
                        const parent = element.parentElement;
                        if (parent) {
                            // Try various dropdown selectors
                            const dropdownSelectors = [
                                '.p-dropdown', // PrimeNG/React
                                '.dropdown', // Bootstrap
                                '[role="combobox"]', // Accessibility role
                                'select', // Standard HTML select
                                '.select', // Common class
                                '.v-select', // Vue
                                '.mat-select', // Angular Material
                                '.MuiSelect-root', // Material-UI
                                '.ant-select', // Ant Design
                                '.chakra-select', // Chakra UI
                                '.custom-select', // Bootstrap custom select
                                '.form-select' // Bootstrap 5
                            ];

                            for (const selector of dropdownSelectors) {
                                const dropdownInParent = parent.querySelector(selector);
                                if (dropdownInParent) {
                                    console.log(`Found dropdown (${selector}) in parent of "${dropdownName}" element`);
                                    dropdownInParent.click();
                                    return true;
                                }
                            }
                        }

                        // Look for dropdown in siblings
                        let sibling = element.nextElementSibling;
                        while (sibling) {
                            // Check if sibling is a dropdown
                            if (sibling.classList.contains('p-dropdown') ||
                                sibling.classList.contains('dropdown') ||
                                sibling.getAttribute('role') === 'combobox' ||
                                sibling.tagName === 'SELECT') {
                                console.log(`Found dropdown in sibling of "${dropdownName}" element`);
                                sibling.click();
                                return true;
                            }

                            // Check for dropdown inside sibling
                            const dropdownInSibling = sibling.querySelector('.p-dropdown, .dropdown, [role="combobox"], select');
                            if (dropdownInSibling) {
                                console.log(`Found dropdown inside sibling of "${dropdownName}" element`);
                                dropdownInSibling.click();
                                return true;
                            }

                            sibling = sibling.nextElementSibling;
                        }

                        // Look for dropdown in ancestors and their siblings
                        let ancestor = element.parentElement;
                        let depth = 0;
                        const MAX_DEPTH = 5; // Limit how far up we go to avoid performance issues

                        while (ancestor && depth < MAX_DEPTH) {
                            // Check siblings of ancestor
                            let ancestorSibling = ancestor.nextElementSibling;
                            while (ancestorSibling) {
                                const dropdownInAncestorSibling = ancestorSibling.querySelector('.p-dropdown, .dropdown, [role="combobox"], select');
                                if (dropdownInAncestorSibling) {
                                    console.log(`Found dropdown in ancestor's sibling`);
                                    dropdownInAncestorSibling.click();
                                    return true;
                                }
                                ancestorSibling = ancestorSibling.nextElementSibling;
                            }

                            ancestor = ancestor.parentElement;
                            depth++;
                        }
                    }
                }

                // STRATEGY 3: Try to find any dropdown with empty or placeholder text
                const placeholderTexts = ['empty', 'select...', 'choose...', 'select an option', 'please select'];
                for (const placeholderText of placeholderTexts) {
                    const placeholderDropdowns = Array.from(document.querySelectorAll('.p-dropdown-label, .dropdown-toggle, [role="combobox"], select'))
                        .filter(el => el.textContent.trim().toLowerCase() === placeholderText);

                    console.log(`Found ${placeholderDropdowns.length} dropdowns with "${placeholderText}" text`);

                    if (placeholderDropdowns.length > 0) {
                        // Find the parent dropdown container and click it
                        const dropdownContainer = placeholderDropdowns[0].closest('.p-dropdown, .dropdown, [role="combobox"]');
                        if (dropdownContainer) {
                            console.log(`Found and clicking dropdown container with "${placeholderText}" text`);
                            dropdownContainer.click();
                            return true;
                        } else {
                            // If no container found, click the element itself
                            console.log(`Clicking dropdown element with "${placeholderText}" text directly`);
                            placeholderDropdowns[0].click();
                            return true;
                        }
                    }
                }

                // STRATEGY 4: Look for dropdown triggers/icons near text matching the dropdown name
                const dropdownTriggers = document.querySelectorAll('.p-dropdown-trigger, .dropdown-toggle, [aria-haspopup="listbox"], .select-arrow');
                console.log(`Found ${dropdownTriggers.length} dropdown triggers/icons`);

                for (const trigger of dropdownTriggers) {
                    // Check if the trigger or its parent contains text matching the dropdown name
                    const triggerParent = trigger.parentElement;
                    if (triggerParent && triggerParent.textContent.toLowerCase().includes(normalizedName)) {
                        console.log(`Found dropdown trigger with parent text containing "${dropdownName}"`);
                        trigger.click();
                        return true;
                    }
                }

                // STRATEGY 5: Special handling for State of Formation dropdown
                if (normalizedName.includes('state') && normalizedName.includes('formation')) {
                    console.log("Using special handling for State of Formation dropdown");

                    // Look for dropdown with "Select State" text
                    const stateLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                        .filter(el => el.textContent.trim() === 'Select State');

                    if (stateLabels.length > 0) {
                        const dropdownContainer = stateLabels[0].closest('.p-dropdown');
                        if (dropdownContainer) {
                            console.log(`Found and clicking dropdown container with "Select State" text`);
                            dropdownContainer.click();
                            return true;
                        }
                    }

                    // If we have multiple dropdowns, check if the first one is entity type
                    const allDropdowns = document.querySelectorAll('.p-dropdown');
                    if (allDropdowns.length >= 2) {
                        const firstDropdownLabel = allDropdowns[0].querySelector('.p-dropdown-label');
                        const firstLabelText = firstDropdownLabel ? firstDropdownLabel.textContent.trim() : '';

                        // If first dropdown is entity type, click the second one
                        if (firstLabelText.toLowerCase().includes('entity') ||
                            firstLabelText === 'LLC' ||
                            firstLabelText === 'CORP' ||
                            firstLabelText === 'Select Entity Type') {
                            console.log(`First dropdown appears to be entity type, clicking second dropdown for state`);
                            allDropdowns[1].click();
                            return true;
                        }
                    }
                }

                // STRATEGY 6: Last resort - try all visible dropdowns
                const allDropdowns = document.querySelectorAll('.p-dropdown, .dropdown, [role="combobox"], select');
                console.log(`Found ${allDropdowns.length} total dropdowns on the page`);

                // Try to find one that might match our dropdown name
                for (const dropdown of allDropdowns) {
                    if (dropdown.textContent.toLowerCase().includes(normalizedName)) {
                        console.log(`Found dropdown with text containing "${dropdownName}"`);
                        dropdown.click();
                        return true;
                    }
                }

                // Special handling for state dropdown as last resort
                if (normalizedName.includes('state') && allDropdowns.length > 1) {
                    console.log(`Clicking second dropdown as last resort for state dropdown`);
                    allDropdowns[1].click();
                    return true;
                }

                // If we still haven't found it and there are dropdowns, click the first visible one
                if (allDropdowns.length > 0) {
                    // Find a visible dropdown
                    for (const dropdown of allDropdowns) {
                        if (window.getComputedStyle(dropdown).display !== 'none' &&
                            window.getComputedStyle(dropdown).visibility !== 'hidden') {
                            console.log(`Clicking first visible dropdown as last resort`);
                            dropdown.click();
                            return true;
                        }
                    }
                }

                return false;
            }""", dropdown_name)

            if clicked:
                await self.speak(f"Clicked the {dropdown_name} dropdown")
                return True
            else:
                self.speak(f"Could not find {dropdown_name} dropdown")
                return False
        except Exception as e:
            print(f"Error with {dropdown_name} dropdown click: {e}")
            self.speak(f"Error clicking {dropdown_name} dropdown")
            return False

    async def _ensure_entity_type_selected(self):
        """Ensure that an entity type is selected"""
        await self.speak("Checking if entity type is selected...")

        try:
            # Check if entity type is already selected
            entity_type_selected = await self.page.evaluate("""() => {
                // Get all dropdowns
                const allDropdowns = document.querySelectorAll('.p-dropdown');
                console.log(`Found ${allDropdowns.length} dropdowns for entity type check`);

                if (allDropdowns.length === 0) {
                    return { success: false, message: "No dropdowns found" };
                }

                // Check the first dropdown (entity type)
                const entityDropdown = allDropdowns[0];
                const label = entityDropdown.querySelector('.p-dropdown-label');

                if (!label) {
                    return { success: false, message: "No label found in entity dropdown" };
                }

                const labelText = label.textContent.trim();
                console.log(`Entity dropdown label text: "${labelText}"`);

                // Check if it has a placeholder class (indicating nothing selected)
                const hasPlaceholder = label.classList.contains('p-placeholder');

                // If it has text other than "Select Entity Type" and no placeholder class, it's selected
                if (!hasPlaceholder && labelText !== "Select Entity Type" && labelText !== "") {
                    return {
                        success: true,
                        message: `Entity type already selected: ${labelText}`,
                        selected: true,
                        value: labelText
                    };
                }

                // Otherwise, we need to select an entity type
                return {
                    success: true,
                    message: "Entity type not selected yet",
                    selected: false
                };
            }""")

            print(f"Entity type check result: {entity_type_selected}")

            if entity_type_selected.get('success'):
                if entity_type_selected.get('selected'):
                    # Entity type is already selected
                    await self.speak(f"Entity type is already selected: {entity_type_selected.get('value')}")
                    return True
                else:
                    # Entity type is not selected, we need to select one
                    await self.speak("Entity type not selected. Selecting LLC...")

                    # Click the entity type dropdown
                    clicked = await self.page.evaluate("""() => {
                        const allDropdowns = document.querySelectorAll('.p-dropdown');
                        if (allDropdowns.length > 0) {
                            console.log("Clicking entity type dropdown");
                            allDropdowns[0].click();
                            return true;
                        }
                        return false;
                    }""")

                    if clicked:
                        # Wait for dropdown panel to appear
                        await self.page.wait_for_selector('.p-dropdown-panel', timeout=2000)

                        # Select LLC option
                        selected = await self.page.evaluate("""() => {
                            // Find LLC option in the dropdown
                            const llcOption = Array.from(document.querySelectorAll('.p-dropdown-item'))
                                .find(item => item.textContent.trim() === 'LLC');

                            if (llcOption) {
                                console.log("Found LLC option, clicking it");
                                llcOption.click();
                                return true;
                            }
                            return false;
                        }""")

                        if selected:
                            await self.speak("Selected LLC as entity type")
                            return True
                        else:
                            await self.speak("Could not find LLC option")
                            return False
                    else:
                        await self.speak("Could not click entity type dropdown")
                        return False
            else:
                await self.speak("Could not check entity type selection")
                return False
        except Exception as e:
            print(f"Error checking entity type selection: {e}")
            await self.speak("Error checking entity type selection")
            return False

    async def _select_entity_type(self, entity_type):
        """Select a specific entity type from the dropdown"""
        await self.speak(f"Selecting entity type {entity_type}...")

        try:
            # Click the entity type dropdown
            clicked = await self.page.evaluate("""() => {
                const allDropdowns = document.querySelectorAll('.p-dropdown');
                if (allDropdowns.length > 0) {
                    console.log("Clicking entity type dropdown");
                    allDropdowns[0].click();
                    return true;
                }
                return false;
            }""")

            if clicked:
                # Wait for dropdown panel to appear
                await self.page.wait_for_selector('.p-dropdown-panel', timeout=2000)

                # Select the specified entity type option
                selected = await self.page.evaluate("""(entityType) => {
                    // Find the specified entity type option in the dropdown
                    const entityTypeOption = Array.from(document.querySelectorAll('.p-dropdown-item'))
                        .find(item => {
                            const itemText = item.textContent.trim().toLowerCase();
                            const searchText = entityType.toLowerCase();
                            return itemText === searchText ||
                                   itemText.startsWith(searchText) ||
                                   itemText.includes(searchText);
                        });

                    if (entityTypeOption) {
                        console.log(`Found entity type option: ${entityTypeOption.textContent.trim()}, clicking it`);
                        entityTypeOption.click();
                        return { success: true, selected: entityTypeOption.textContent.trim() };
                    }
                    return { success: false, message: "Could not find entity type option" };
                }""", entity_type)

                if selected and selected.get('success'):
                    await self.speak(f"Selected {selected.get('selected')} as entity type")
                    return True
                else:
                    await self.speak(f"Could not find entity type {entity_type}")
                    return False
            else:
                await self.speak("Could not click entity type dropdown")
                return False
        except Exception as e:
            print(f"Error selecting entity type: {e}")
            await self.speak(f"Error selecting entity type {entity_type}")
            return False
