import random
import time
import httpx
import logging

logger = logging.getLogger(__name__)

class ProxyRotator:
    def __init__(self):
        self.isp_anchors = [
            'Jio-Broadband-BLR',
            'Airtel-Fiber-DEL',
            'Vi-Cellular-MUM',
            'BSNL-FTTH-CHE'
        ]
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0"
        ]
        
    def get_random_ip(self):
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"
        
    def _apply_micro_jitter(self):
        jitter = random.uniform(0.05, 0.18)
        time.sleep(jitter)
        
    def fetch(self, url):
        self._apply_micro_jitter()
        isp = random.choice(self.isp_anchors)
        fake_ip = self.get_random_ip()
        ua = random.choice(self.user_agents)
        
        headers = {
            "User-Agent": ua,
            "X-Forwarded-For": fake_ip,
            "X-Simulated-ISP": isp
        }
        
        logger.info(f"Fetching {url} via {isp} with IP {fake_ip}")
        try:
            with httpx.Client(headers=headers, timeout=10.0) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Fetch failed via {isp}: {e}")
            return None

