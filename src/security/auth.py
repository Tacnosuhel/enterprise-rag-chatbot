# API authentication, token verification, and RBAC
# src/security/auth.py

USER_PROFILES = {
    "alice_eng": {
        "name": "Alice (Engineer)",
        "role": "engineer",
        "allowed_departments": ["engineering", "general"]
    },
    "bob_finance": {
        "name": "Bob (Financial Analyst)",
        "role": "finance",
        "allowed_departments": ["finance", "general"]
    },
    "charlie_hr": {
        "name": "Charlie (HR Specialist)",
        "role": "hr",
        "allowed_departments": ["hr", "general"]
    },
    "david_mkt": {
        "name": "David (Marketing Lead)",
        "role": "marketing",
        "allowed_departments": ["marketing", "general"]
    },
    "admin_exec": {
        "name": "Admin / Executive",
        "role": "admin",
        "allowed_departments": ["engineering", "finance", "general", "hr", "marketing"]
    }
}

def get_user_permissions(user_key: str):
    """Returns user profile and their permitted departments."""
    return USER_PROFILES.get(user_key, {
        "name": "Guest",
        "role": "guest",
        "allowed_departments": ["general"]
    })