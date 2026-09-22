import os
import json
import logging
from bs4 import BeautifulSoup
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SelfHealingScraper:
    def __init__(self, api_key=None, state_file='selectors.json'):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.state_file = state_file
        self.selectors = self._load_selectors()
        
    def _load_selectors(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading selectors: {e}")
        return {"airfare": ".price-value"} # default fallback
        
    def _save_selectors(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.selectors, f, indent=4)
            
    def _heal_selector(self, html_block, target_name):
        logger.warning(f"Initiating self-healing for '{target_name}'")
        if not self.api_key:
            logger.error("No Gemini API key found for self-healing.")
            return None
            
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = (
            f"Analyze the following HTML block and locate the CSS selector for the {target_name}. "
            "Return a JSON payload with the key 'selector' and the value as the CSS selector string. "
            "Example: {\"selector\": \".new-price-class\"}\n\n"
            f"HTML Block:\n{html_block}"
        )
        try:
            response = model.generate_content(prompt)
            # Parse json from response
            import re
            match = re.search(r'```json\n(.*?)\n```', response.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                data = json.loads(response.text)
                
            new_selector = data.get("selector")
            if new_selector:
                self.selectors[target_name] = new_selector
                self._save_selectors()
                logger.info(f"Healed selector for '{target_name}': {new_selector}")
                return new_selector
        except Exception as e:
            logger.error(f"Self-healing failed: {e}")
        return None

    def extract_value(self, html_content, target_name="airfare"):
        soup = BeautifulSoup(html_content, 'html.parser')
        selector = self.selectors.get(target_name, ".price-value")
        element = soup.select_one(selector)
        
        if element:
            return element.text.strip()
            
        # Extraction failed, trigger self-healing
        body = soup.find('body')
        html_block = str(body)[:3000] if body else html_content[:3000]
        
        new_selector = self._heal_selector(html_block, target_name)
        if new_selector:
            element = soup.select_one(new_selector)
            if element:
                return element.text.strip()
        return None

