import re
from typing import Tuple

class SecurityGuardrails:
    def __init__(self):
        # 1. PII Patterns for Output Masking
        self.pii_patterns = {
            "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "PHONE": re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            "CREDIT_CARD": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            "AADHAAR": re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b'),
            "SSN": re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
        }

        # 2. Input Security Patterns (Prompt Injection / Jailbreak)
        self.injection_keywords = [
            "ignore previous instructions",
            "ignore all instructions",
            "system prompt",
            "bypass rbac",
            "drop table",
            "dan mode",
            "jailbreak"
        ]

        # 3. Out-of-Domain Keywords (Arbitrary coding or generic generation)
        self.out_of_scope_keywords = [
            "write a python script",
            "write a program",
            "write code",
            "solve this leetcode",
            "create a website",
            "write a poem",
            "tell me a joke"
        ]

        # 4. Small-talk / Greeting Patterns
        self.greeting_patterns = [
            r"^(hi|hello|hey|good\s*(morning|afternoon|evening)|hola|namaste)[\s!.,?]*$",
            r"^who are you[\s?]*$",
            r"^what can you do[\s?]*$",
            r"^help[\s?]*$"
        ]

        # 5. Domain Department Keywords (Must match exact RBAC names)
        self.dept_keywords = {
            "technology": [
                "microservice", "rate limit", "api", "architecture", "database",
                "deploy", "docker", "server", "latency", "redis", "endpoint",
                "disaster recovery", "rto", "rpo", "backup", "engineering", "tech"
            ],
            "hr": [
                "leave", "maternity", "paternity", "holiday", "salary",
                "payroll", "conduct", "work from home", "insurance", "hr",
                "benefits", "vacation", "sick leave", "human resources"
            ],
            "finance": [
                "budget", "revenue", "expense", "tax", "audit", "fiscal",
                "quarterly", "profit", "financial", "accounting"
            ]
        }

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """Validates input prompt for prompt injection attempts."""
        if not prompt or not isinstance(prompt, str):
            return False, "Empty or invalid prompt format."

        prompt_lower = prompt.lower()
        for kw in self.injection_keywords:
            if kw in prompt_lower:
                return False, f"Prompt injection pattern detected: '{kw}'."

        return True, "Valid prompt."

    def is_greeting(self, prompt: str) -> bool:
        """Checks if prompt is just a friendly greeting or small talk."""
        prompt_clean = prompt.strip().lower()
        for pattern in self.greeting_patterns:
            if re.match(pattern, prompt_clean):
                return True
        return False

    def check_domain_scope(self, prompt: str) -> Tuple[bool, str]:
        """Ensures the question targets FinSolve enterprise scope, not arbitrary code/tasks."""
        prompt_lower = prompt.lower()
        for kw in self.out_of_scope_keywords:
            if kw in prompt_lower:
                return False, (
                    "I am FinSolve's Enterprise Assistant, restricted strictly to FinSolve policies, "
                    "architecture, and company documentation. I cannot generate arbitrary code or general-purpose content."
                )
        return True, ""

    def classify_department(self, prompt: str) -> str:
        """
        Maps user query to exact departments: 'technology', 'hr', 'finance', or 'general'.
        """
        prompt_lower = prompt.lower()
        for dept, keywords in self.dept_keywords.items():
            for kw in keywords:
                if kw in prompt_lower:
                    return dept
        return "general"

    def mask_pii_output(self, text: str) -> str:
        """Sanitizes PII data before displaying output."""
        if not isinstance(text, str):
            text = str(text)

        sanitized_text = text
        for label, pattern in self.pii_patterns.items():
            replacement = f"[{label}_REDACTED]"
            sanitized_text = pattern.sub(replacement, sanitized_text)

        return sanitized_text


# Singleton instance
guardrails = SecurityGuardrails()