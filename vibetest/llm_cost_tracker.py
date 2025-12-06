
import threading

class CostTracker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CostTracker, cls).__new__(cls)
                    cls._instance._init_tracker()
        return cls._instance

    def _init_tracker(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        
        # Pricing per 1M tokens (approximate standard rates)
        # Structure: "model_keyword": (input_price, output_price)
        self.pricing = {
            "gpt-4o": (2.50, 10.00),
            "gpt-4": (30.00, 60.00), 
            "gpt-3.5": (0.50, 1.50),
            "gemini-1.5-pro": (3.50, 10.50),
            "gemini-1.5-flash": (0.075, 0.30),
            "gemini-2.5-flash": (0.075, 0.30), # Assuming similar to 1.5 flash for preview
            "claude-3-5-sonnet": (3.00, 15.00),
            "claude-3-haiku": (0.25, 1.25),
            "deepseek-chat": (0.14, 0.28), # deepseek-v3
        }
        self.default_price = (1.00, 3.00) # Fallback

    def add_usage(self, model: str, input_tokens: int, output_tokens: int):
        with self._lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            
            price_found = False
            model_lower = model.lower()
            
            # Find matching pricing
            input_rate, output_rate = self.default_price
            
            # Simple keyword matching
            for key, (in_p, out_p) in self.pricing.items():
                if key in model_lower:
                    input_rate = in_p
                    output_rate = out_p
                    price_found = True
                    break
            
            cost = (input_tokens / 1_000_000 * input_rate) + (output_tokens / 1_000_000 * output_rate)
            self.total_cost += cost

    def get_total_cost(self) -> float:
        with self._lock:
            return self.total_cost

    def reset(self):
        with self._lock:
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.total_cost = 0.0
