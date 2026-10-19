"""Tiny request validator. Collects every problem, then raises one 422 error."""
import re
from datetime import date

from app.errors import ApiError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Validator:
    def __init__(self, data):
        if not isinstance(data, dict):
            raise ApiError(400, "BAD_REQUEST", "Request body must be a JSON object")
        self.data = data
        self.errors = {}

    def has(self, key):
        return key in self.data and self.data[key] is not None

    def _missing(self, key, required):
        if required:
            self.errors[key] = "This field is required"
        return None

    def string(self, key, min_len=1, max_len=255, required=True):
        if not self.has(key):
            return self._missing(key, required)
        value = self.data[key]
        if not isinstance(value, str):
            self.errors[key] = "Must be a string"
            return None
        value = value.strip()
        if not (min_len <= len(value) <= max_len):
            self.errors[key] = f"Must be {min_len} to {max_len} characters"
            return None
        return value

    def secret(self, key, max_len=128, required=True):
        """Passwords: not stripped, only length-checked."""
        if not self.has(key):
            return self._missing(key, required)
        value = self.data[key]
        if not isinstance(value, str) or not (1 <= len(value) <= max_len):
            self.errors[key] = f"Must be a string of 1 to {max_len} characters"
            return None
        return value

    def email(self, key, required=True):
        value = self.string(key, 3, 255, required)
        if value is None:
            return None
        if not EMAIL_RE.match(value):
            self.errors[key] = "Must be a valid email address"
            return None
        return value.lower()

    def new_password(self, key):
        value = self.secret(key)
        if value is None:
            return None
        if len(value) < 10 or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            self.errors[key] = "Must be at least 10 characters and contain a letter and a number"
            return None
        return value

    def integer(self, key, min_value=None, max_value=None, required=True):
        if not self.has(key):
            return self._missing(key, required)
        value = self.data[key]
        if isinstance(value, bool) or not isinstance(value, int):
            self.errors[key] = "Must be an integer"
            return None
        if (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
            self.errors[key] = f"Must be between {min_value} and {max_value}"
            return None
        return value

    def number(self, key, min_value=None, max_value=None, required=True):
        if not self.has(key):
            return self._missing(key, required)
        value = self.data[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.errors[key] = "Must be a number"
            return None
        if (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
            self.errors[key] = f"Must be between {min_value} and {max_value}"
            return None
        return float(value)

    def enum(self, key, choices, required=True):
        if not self.has(key):
            return self._missing(key, required)
        if self.data[key] not in choices:
            self.errors[key] = "Must be one of: " + ", ".join(choices)
            return None
        return self.data[key]

    def date(self, key, required=True):
        if not self.has(key):
            return self._missing(key, required)
        try:
            return date.fromisoformat(self.data[key])
        except (TypeError, ValueError):
            self.errors[key] = "Must be a date in YYYY-MM-DD format"
            return None

    def id_list(self, key, required=False):
        if not self.has(key):
            return self._missing(key, required)
        value = self.data[key]
        if (not isinstance(value, list) or len(value) > 500
                or any(isinstance(i, bool) or not isinstance(i, int) for i in value)):
            self.errors[key] = "Must be a list of integer ids"
            return None
        return list(dict.fromkeys(value))

    def fail(self, key, message):
        self.errors[key] = message

    def done(self):
        if self.errors:
            raise ApiError(422, "VALIDATION_ERROR", "Validation failed", self.errors)
