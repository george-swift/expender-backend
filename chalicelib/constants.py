# Account status
ACCOUNT_STATUS_ACTIVE = "active"
ACCOUNT_STATUS_DEACTIVATED = "deactivated"

# Pricing plans
USER_FREE_PLAN = "free"
USER_PRO_PLAN = "pro"

# Stripe-backed subscription states that grant premium usage.
PAID_SUBSCRIPTION_STATUSES = {"active", "trialing"}

# Smart scan limits
FREE_PLAN_SMART_SCAN_LIMIT = 30
PRO_PLAN_SMART_SCAN_LIMIT = float("inf")  # Unlimited for Pro plan

# Threshold for creating multiple expenses in a single batch
MAX_BATCH_SIZE = 25

# Supported currencies (ISO 4217)
CURRENCY_PATTERNS = {
    "AED": ["د.إ", "AED"],
    "ARS": ["$", "ARS"],
    "AUD": ["A$", "AUD"],
    "BRL": ["R$", "BRL"],
    "CAD": ["CA$", "CAD"],
    "CHF": ["CHF", "Fr"],
    "EUR": ["€", "EUR"],
    "GBP": ["£", "GBP"],
    "GHS": ["GH₵", "GHS"],
    "INR": ["₹", "INR"],
    "JPY": ["¥", "JPY"],
    "KES": ["KSh", "KES"],
    "MXN": ["MX$", "MXN"],
    "NGN": ["₦", "NGN"],
    "TRY": ["₺", "TRY"],
    "QAR": ["ر. ق", "QAR"],
    "USD": ["$", "USD"],
    "ZAR": ["R", "ZAR"],
}

# Supported expense categories
CATEGORIES = {
    "Advertising",
    "Benefits",
    "Car",
    "Employee Salaries",
    "Equipment",
    "Fees",
    "Home Office",
    "Insurance",
    "Interest",
    "Internet",
    "Labor",
    "Maintenance",
    "Marketing",
    "Meals and Entertainment",
    "Office Supplies",
    "Other",
    "Phone",
    "Professional Services",
    "Rent",
    "Shipping and Delivery",
    "Shopping",
    "Subscriptions",
    "Taxes",
    "Technology and Software",
    "Training and Development",
    "Travel",
    "Utilities",
}

# File size constraints for uploaded receipts
MIN_FILE_SIZE = 512  # 512 Bytes
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Allowed file formats for uploaded receipts
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
