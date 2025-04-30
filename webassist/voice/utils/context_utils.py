from typing import List, Dict, Any
from webassist.models.context import PageContext, InteractionContext
import re

class ContextUtils:
    def __init__(self, assistant):
        self.assistant = assistant

    async def get_page_context(self) -> Dict[str, Any]:
        """Get the current page context"""
        try:
            # Get page title and URL
            title = await self.assistant.page.title()
            url = self.assistant.page.url

            # Get visible text content
            visible_text = await self.assistant.page.evaluate("""() => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: (node) => {
                            // Check if the node's parent is visible
                            const style = window.getComputedStyle(node.parentElement);
                            return style.display !== 'none' && 
                                   style.visibility !== 'hidden' && 
                                   style.opacity !== '0' &&
                                   node.textContent.trim() !== '' ?
                                NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
                        }
                    }
                );
                
                const texts = [];
                let node;
                while (node = walker.nextNode()) {
                    texts.push(node.textContent.trim());
                }
                return texts.join(' ');
            }""")

            # Get input fields
            input_fields = await self._check_for_input_fields()

            # Get buttons
            buttons = await self.assistant.page.evaluate("""() => {
                const buttons = [];
                document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]').forEach(button => {
                    if (window.getComputedStyle(button).display !== 'none' && 
                        window.getComputedStyle(button).visibility !== 'hidden') {
                        buttons.push({
                            text: button.textContent.trim(),
                            type: button.tagName.toLowerCase(),
                            role: button.getAttribute('role') || 'button'
                        });
                    }
                });
                return buttons;
            }""")

            # Get links
            links = await self.assistant.page.evaluate("""() => {
                const links = [];
                document.querySelectorAll('a').forEach(link => {
                    if (window.getComputedStyle(link).display !== 'none' && 
                        window.getComputedStyle(link).visibility !== 'hidden') {
                        links.push({
                            text: link.textContent.trim(),
                            href: link.href
                        });
                    }
                });
                return links;
            }""")

            # Create page context
            context = {
                "title": title,
                "url": url,
                "visible_text": visible_text,
                "input_fields": input_fields,
                "buttons": buttons,
                "links": links
            }

            return context
        except Exception as e:
            self.assistant.speak(f"Error getting page context: {str(e)}")
            return {}

    async def _check_for_input_fields(self) -> Dict[str, Any]:
        """Check for input fields on the page"""
        try:
            # Get all input fields
            input_fields = await self.assistant.page.evaluate("""() => {
                const fields = {
                    hasEmailField: false,
                    hasPasswordField: false,
                    hasTextFields: false,
                    hasCheckboxes: false,
                    hasRadioButtons: false,
                    hasDropdowns: false,
                    hasFileInputs: false,
                    hasDateInputs: false,
                    hasNumberInputs: false,
                    hasSearchInputs: false,
                    hasTelInputs: false,
                    hasUrlInputs: false,
                    hasColorInputs: false,
                    hasRangeInputs: false,
                    hasHiddenInputs: false,
                    hasSubmitButtons: false,
                    hasResetButtons: false,
                    hasButtonButtons: false
                };

                // Check for specific input types
                document.querySelectorAll('input, select, textarea').forEach(field => {
                    if (window.getComputedStyle(field).display !== 'none' && 
                        window.getComputedStyle(field).visibility !== 'hidden') {
                        const type = field.type || field.tagName.toLowerCase();
                        const name = field.name || '';
                        const placeholder = field.placeholder || '';
                        const id = field.id || '';
                        const value = field.value || '';
                        const isRequired = field.required || false;
                        const isDisabled = field.disabled || false;
                        const isReadOnly = field.readOnly || false;
                        const maxLength = field.maxLength || -1;
                        const minLength = field.minLength || -1;
                        const pattern = field.pattern || '';
                        const autocomplete = field.autocomplete || '';
                        const ariaLabel = field.getAttribute('aria-label') || '';
                        const ariaLabelledby = field.getAttribute('aria-labelledby') || '';
                        const ariaDescribedby = field.getAttribute('aria-describedby') || '';
                        const role = field.getAttribute('role') || '';
                        const dataTestid = field.getAttribute('data-testid') || '';
                        const className = field.className || '';

                        // Update fields object based on input type
                        switch (type) {
                            case 'email':
                                fields.hasEmailField = true;
                                break;
                            case 'password':
                                fields.hasPasswordField = true;
                                break;
                            case 'text':
                            case 'textarea':
                                fields.hasTextFields = true;
                                break;
                            case 'checkbox':
                                fields.hasCheckboxes = true;
                                break;
                            case 'radio':
                                fields.hasRadioButtons = true;
                                break;
                            case 'select':
                                fields.hasDropdowns = true;
                                break;
                            case 'file':
                                fields.hasFileInputs = true;
                                break;
                            case 'date':
                            case 'datetime-local':
                            case 'month':
                            case 'time':
                            case 'week':
                                fields.hasDateInputs = true;
                                break;
                            case 'number':
                            case 'range':
                                fields.hasNumberInputs = true;
                                break;
                            case 'search':
                                fields.hasSearchInputs = true;
                                break;
                            case 'tel':
                                fields.hasTelInputs = true;
                                break;
                            case 'url':
                                fields.hasUrlInputs = true;
                                break;
                            case 'color':
                                fields.hasColorInputs = true;
                                break;
                            case 'hidden':
                                fields.hasHiddenInputs = true;
                                break;
                            case 'submit':
                                fields.hasSubmitButtons = true;
                                break;
                            case 'reset':
                                fields.hasResetButtons = true;
                                break;
                            case 'button':
                                fields.hasButtonButtons = true;
                                break;
                        }
                    }
                });

                return fields;
            }""")

            return input_fields
        except Exception as e:
            self.assistant.speak(f"Error checking for input fields: {str(e)}")
            return {}

    def filter_html(self, html: str) -> str:
        """Filter HTML to remove sensitive information"""
        try:
            # Remove script tags
            html = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html, flags=re.IGNORECASE)
            
            # Remove style tags
            html = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', html, flags=re.IGNORECASE)
            
            # Remove comments
            html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
            
            # Remove sensitive attributes
            html = re.sub(r'\b(data-[\w-]+|aria-[\w-]+|role|id|class|style|on\w+)\s*=\s*["\'][^"\']*["\']', '', html)
            
            # Remove empty tags
            html = re.sub(r'<(\w+)\b[^>]*>\s*<\/\1>', '', html)
            
            # Remove multiple spaces
            html = re.sub(r'\s+', ' ', html)
            
            return html.strip()
        except Exception as e:
            self.assistant.speak(f"Error filtering HTML: {str(e)}")
            return html 