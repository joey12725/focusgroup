import re
import random
import numpy as np

class BlueprintParser:
    def __init__(self):
        self.functions = {
            'range': self._range,
            'choice': self._choice,
            'weighted': self._weighted,
            'normal': self._normal,
            'bool': self._bool
        }

    def parse(self, text: str):
        """
        Parses a string containing {{ function() }} syntax and replaces it with the result.
        If the result is a number or boolean, it attempts to return that type directly if the entire string is just the function.
        """
        pattern = r"\{\{\s*(.*?)\s*\}\}"
        matches = re.findall(pattern, text)
        
        if not matches:
            return text

        # If the entire string is a single template, return the typed result
        if re.fullmatch(pattern, text):
            return self._evaluate(matches[0])

        # Otherwise, replace all occurrences in the string
        result = text
        for match in matches:
            val = self._evaluate(match)
            result = result.replace(f"{{{{ {match} }}}}", str(val))
            result = result.replace(f"{{{{{match}}}}}", str(val)) # Handle cases without spaces
        
        return result

    def _evaluate(self, expression: str):
        # Extract function name and arguments
        match = re.match(r"(\w+)\((.*)\)", expression)
        if not match:
            raise ValueError(f"Invalid syntax: {expression}")
        
        func_name, args_str = match.groups()
        
        if func_name not in self.functions:
            raise ValueError(f"Unknown function: {func_name}")
        
        # Parse arguments
        args = self._parse_args(args_str)
        
        return self.functions[func_name](*args)

    def _parse_args(self, args_str: str):
        # Handle weighted syntax specifically if it looks like Key:Value pairs
        if ':' in args_str and not args_str.strip().startswith('{'):
            # Split by comma, but be careful about nested commas if any (though unlikely for this DSL)
            items = [item.strip() for item in args_str.split(',')]
            weighted_dict = {}
            for item in items:
                if ':' in item:
                    k, v = item.split(':', 1)
                    k = k.strip()
                    v = v.strip()
                    # Try to evaluate value (number), key is string
                    try:
                        val = eval(v)
                    except:
                        val = v
                    weighted_dict[k] = val
            return [weighted_dict]

        # General parsing for other functions
        args = []
        # Split by comma
        parts = [p.strip() for p in args_str.split(',')]
        
        for part in parts:
            # Handle kwarg syntax like median=75000 -> just take 75000
            if '=' in part:
                part = part.split('=', 1)[1].strip()
            
            try:
                # Try to eval as number/bool/quoted string
                val = eval(part, {"__builtins__": None}, {})
                args.append(val)
            except (NameError, SyntaxError):
                # If it fails, assume it's an unquoted string
                args.append(part)
            except Exception as e:
                # Fallback
                args.append(part)
                
        return args

    def _range(self, min_val, max_val):
        return random.randint(min_val, max_val)

    def _choice(self, *options):
        return random.choice(options)

    def _weighted(self, options: dict):
        choices = list(options.keys())
        weights = list(options.values())
        return random.choices(choices, weights=weights, k=1)[0]

    def _normal(self, mean, std):
        return int(np.random.normal(mean, std))

    def _bool(self, chance):
        return random.random() < chance

if __name__ == "__main__":
    # Quick test
    parser = BlueprintParser()
    print(f"Range: {parser.parse('{{ range(25, 45) }}')}")
    print(f"Choice: {parser.parse('{{ choice(\"Male\", \"Female\") }}')}")
    # Simplified weighted test to avoid quote hell
    w_res = parser.parse("{{ weighted('Admin': 0.8, 'Manager': 0.2) }}")
    print(f"Weighted: {w_res}")
    print(f"Normal: {parser.parse('{{ normal(75000, 15000) }}')}")
    print(f"Bool: {parser.parse('{{ bool(0.3) }}')}")
