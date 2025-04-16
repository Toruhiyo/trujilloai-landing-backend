import logging
from src.utils.metaclasses import DynamicSingleton
import re
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailFormatter(metaclass=DynamicSingleton):
    # Private:
    DEFAULT_COMMON_DOMAINS = json.loads(
        (Path(__file__).parent / "configs" / "common-domains.json").read_text()
    )
    DEFAULT_POPULAR_EMAIL_PROVIDERS = json.loads(
        (Path(__file__).parent / "configs" / "popular-email-providers.json").read_text()
    )
    DEFAULT_SPOKEN_SYMBOLS = json.loads(
        (Path(__file__).parent / "configs" / "spoken-symbols.json").read_text()
    )

    def __init__(
        self,
        common_domains: list[str] = DEFAULT_COMMON_DOMAINS,
        popular_email_providers: list[str] = DEFAULT_POPULAR_EMAIL_PROVIDERS,
        spoken_symbols: dict[str, str] = DEFAULT_SPOKEN_SYMBOLS,
    ):
        self.__common_domains = common_domains
        self.__popular_email_providers = popular_email_providers
        self.__spoken_symbols = spoken_symbols
        # Create a mapping for domain to TLD (e.g., "comcast" -> "net")
        self.__domain_tld_mapping = {}
        for provider in self.__popular_email_providers:
            parts = provider.split(".")
            if len(parts) >= 2:
                self.__domain_tld_mapping[parts[0]] = ".".join(parts[1:])

    @property
    def __popular_domain_hosts(self) -> list[str]:
        return [provider.split(".")[0] for provider in self.__popular_email_providers]

    def compute(
        self,
        email: str,
    ) -> str:
        formatted_email = self.__compute_formatted_email(
            email,
        )
        if not self.__is_valid_email(formatted_email):
            logger.warning(f"Invalid email: {formatted_email}")

        return formatted_email

    # Private:
    def __compute_formatted_email(
        self,
        email: str,
    ) -> str:
        # Convert to lowercase
        email = email.lower()

        # Replace common speech-to-text patterns
        email = self.__replace_spoken_symbols(email)

        # Remove spaces
        email = email.replace(" ", "")

        # Check if we have a valid email format
        if self.__is_valid_email(email):
            return email

        # Handle the pattern user.provider (like user.hotmail)
        if "@" not in email and "." in email and email.count(".") == 1:
            username, domain = email.split(".", 1)
            # Check if domain is a known email provider
            for provider in self.__popular_domain_hosts:
                if domain == provider:
                    # Use the correct TLD from the mapping
                    tld = self.__domain_tld_mapping.get(provider, "com")
                    return f"{username}@{provider}.{tld}"

            # Check if the second part is a known TLD (com, org, etc.)
            if domain in [
                d.strip(".") for d in self.__common_domains if len(d.strip(".")) <= 3
            ]:
                return f"{username}@gmail.{domain}"

            # If the domain isn't recognized, use gmail.com as default
            if username not in [
                p.replace(".com", "") for p in self.__popular_email_providers
            ]:
                return f"{username}@gmail.com"

        # Try to fix missing @ symbol
        if "@" not in email:
            email = self.__fix_missing_at_symbol(email)

        # Fix incomplete domains
        email = self.__fix_incomplete_domain(email)

        return email

    def __replace_spoken_symbols(self, email: str) -> str:
        # Handle common name patterns with spoken symbols (like "name guion surname")
        email = self.__handle_name_patterns_with_symbols(email)

        # Process each replacement
        for word, symbol in self.__spoken_symbols.items():
            pattern = rf"(^|\s){re.escape(word)}(\s|$)"
            email = re.sub(pattern, rf"\1{symbol}\2", email)

        # Do a final cleanup to ensure all punctuation has no spaces
        email = re.sub(r"\s*@\s*", "@", email)
        email = re.sub(r"\s*\.\s*", ".", email)
        email = re.sub(r"\s*_\s*", "_", email)
        email = re.sub(r"\s*-\s*", "-", email)
        email = re.sub(r"\s*,\s*", ",", email)
        email = re.sub(r"\s*:\s*", ":", email)

        return email

    def __handle_name_patterns_with_symbols(self, email: str) -> str:
        """Handle patterns like 'First Middle guion Last' where symbols are spoken words."""
        # Special case for compound symbols like "guion medio"
        pattern_compound = (
            r"(\w+)(\s+\w+)?\s+(guion medio|guion bajo|barra baja)\s+(\w+)"
            r"(\s+arroba|\s+at|\s+en|\s+@)"
        )
        match = re.search(pattern_compound, email)
        if match:
            firstname = match.group(1)
            lastname = match.group(4)
            separator = match.group(5)
            symbol = "-" if match.group(3) == "guion medio" else "_"
            email = re.sub(
                pattern_compound, f"{firstname}{symbol}{lastname}{separator}", email
            )

        # Handle patterns with dash/hyphen variations between words
        pattern_dash = (
            r"(\w+)\s+(\w+)\s+(guion|dash|hyphen|raya|menos)\s+(\w+)"
            r"(\s+arroba|\s+at|\s+en|\s+@)"
        )
        match = re.search(pattern_dash, email)
        if match:
            firstname = match.group(1)
            lastname = match.group(4)
            separator = match.group(5)
            email = re.sub(pattern_dash, f"{firstname}-{lastname}{separator}", email)

        # Handle patterns with underscore variations between words
        pattern_underscore = (
            r"(\w+)\s+(underscore|subrayado|barra|underline)\s+(\w+)"
            r"(\s+arroba|\s+at|\s+en|\s+@)"
        )
        match = re.search(pattern_underscore, email)
        if match:
            firstname = match.group(1)
            lastname = match.group(3)
            separator = match.group(4)
            email = re.sub(
                pattern_underscore, f"{firstname}_{lastname}{separator}", email
            )

        return email

    def __is_valid_email(self, email: str) -> bool:
        # More strict regex to check if email has valid format
        email_pattern = r"^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    def __fix_incomplete_domain(self, email: str) -> str:
        """Add .com to incomplete domains like hotmail, gmail, etc."""
        if "@" not in email:
            return email

        username, domain = email.split("@", 1)

        # Check if domain is incomplete
        for provider in self.__popular_domain_hosts:
            if domain == provider:
                # Use the correct TLD from the mapping
                tld = self.__domain_tld_mapping.get(provider, "com")
                return f"{username}@{provider}.{tld}"

        # Check if domain has no TLD
        if "." not in domain:
            return f"{username}@{domain}.com"

        return email

    def __fix_missing_at_symbol(self, email: str) -> str:
        # Special case for domains with special TLDs
        for provider, tld in self.__domain_tld_mapping.items():
            if email.startswith(f"{provider} ") or email == provider:
                return f"user@{provider}.{tld}"

        # First special case: domain-only with dot
        if "." in email and email.count(".") == 1:
            # Handle specific domains
            for provider in self.__popular_domain_hosts:
                if email.startswith(f"{provider}."):
                    return f"user@{email}"
                elif email == f"{provider}":
                    # Use the correct TLD
                    tld = self.__domain_tld_mapping.get(provider, "com")
                    return f"user@{provider}.{tld}"

            # Default domain logic (from above is handled first)
            return email

        # Check for known domains first
        if self.__has_known_domain(email):
            return self.__add_at_with_known_domain(email)

        # Try to insert @ symbol where it likely belongs
        parts = re.split(r"\.", email)
        dot_count = email.count(".")

        # If there's only one dot and no @, use gmail.com as default domain
        if dot_count == 1 and len(parts) == 2:
            # Check if the second part is a TLD (com, org, etc.)
            tlds = [
                d.strip(".") for d in self.__common_domains if len(d.strip(".")) <= 3
            ]
            if parts[1] in tlds:
                return f"{parts[0]}@gmail.{parts[1]}"

            # Handle specific providers in domain part
            for provider in self.__popular_domain_hosts:
                if parts[1].startswith(provider):
                    # Use the correct TLD
                    tld = self.__domain_tld_mapping.get(provider, "com")
                    return f"{parts[0]}@{provider}.{tld}"

            return f"{parts[0]}@gmail.com"

        if len(parts) >= 2:
            # Find a domain part
            potential_formats = []

            # Try placing @ before the last part
            potential_formats.append(
                email.rsplit(".", 1)[0] + "@" + email.rsplit(".", 1)[1]
            )

            # Try placing @ before the second-to-last dot
            if len(parts) >= 3:
                domain_idx = len(parts) - 2
                reconstructed = ""
                for i, part in enumerate(parts):
                    if i == domain_idx:
                        reconstructed += "@" + part
                    elif i > 0:
                        reconstructed += "." + part
                    else:
                        reconstructed += part
                potential_formats.append(reconstructed)

            # Return the first format that passes validation
            for format in potential_formats:
                if self.__is_valid_email(format):
                    return format

        # If we can't determine where @ should go, make a best guess
        # by putting @ before the last dot
        if "." in email:
            name, domain = email.rsplit(".", 1)
            return f"{name}@{domain}"

        return email

    def __has_known_domain(self, email: str) -> bool:
        """Check if the email contains any of the known domains."""
        email_lower = email.lower()

        # Special case for exact matches of unknown domains
        if "." not in email_lower or "@" in email_lower:
            return False

        # Check if it's a domain pattern like user.gmail.com
        for provider in self.__popular_email_providers:
            # For exact matches like "gmail.com"
            if provider == email_lower:
                return True

            # For patterns like "user.gmail.com"
            if f".{provider}" in email_lower:
                return True

            # For incomplete domains like "user.gmail"
            provider_base = provider.split(".")[0]
            if email_lower.endswith(f".{provider_base}"):
                parts = email_lower.split(".")
                if len(parts) >= 2 and parts[-1] == provider_base:
                    return True

        # Check for common domains (.com, .org, etc.)
        for domain in self.__common_domains:
            if email_lower.endswith(domain):
                return True

        return False

    def __add_at_with_known_domain(self, email: str) -> str:
        """Try to find the right place to insert the @ symbol."""

        # Handle full email providers (like gmail.com, yahoo.com)
        providers = sorted(self.__popular_email_providers, key=len, reverse=True)
        for provider in providers:
            if provider in email:
                # Split at the provider
                split_index = email.find(provider)
                if split_index > 0:
                    username = email[:split_index].rstrip(".")
                    domain = provider
                    return f"{username}@{domain}"

        # Handle domain hosts (like gmail, yahoo)
        hosts = sorted(self.__popular_domain_hosts, key=len, reverse=True)
        for provider in hosts:
            # Look for patterns like "username.gmail"
            pattern = f".{provider}$"
            if re.search(pattern, email):
                # Extract username part
                parts = email.split(f".{provider}")
                if len(parts) == 1:
                    username = parts[0]
                    # Use the correct TLD
                    tld = self.__domain_tld_mapping.get(provider, "com")
                    return f"{username}@{provider}.{tld}"

            # Match patterns like "username.gmail.anything"
            pattern = f"\\.{provider}\\."
            if re.search(pattern, email):
                parts = re.split(pattern, email, 1)
                if len(parts) == 2:
                    username = parts[0]
                    tld = parts[1]
                    return f"{username}@{provider}.{tld}"

        # Look for complex forms like "username.firstname.lastname.gmail.com"
        for provider in self.__popular_email_providers:
            if f".{provider}" in email:
                split_index = email.rfind(f".{provider}")
                if split_index > 0:
                    username = email[:split_index]
                    return f"{username}@{provider}"

        # Fallback - try to find domain boundary based on common TLDs
        for domain in sorted(self.__common_domains, key=len, reverse=True):
            if email.endswith(domain):
                username_part = email[: -len(domain)]

                # Look for a provider part to complete the domain
                for provider in self.__popular_domain_hosts:
                    if username_part.endswith(f".{provider}"):
                        # Split at the provider
                        provider_index = username_part.rfind(f".{provider}")
                        if provider_index > 0:
                            real_username = username_part[:provider_index]
                            return f"{real_username}@{provider}{domain}"

                # If no provider is found, use the default pattern
                if "." in username_part:
                    # Take everything before the last dot as username
                    last_dot = username_part.rfind(".")
                    if last_dot > 0:
                        real_username = username_part[:last_dot]
                        domain_name = username_part[last_dot + 1 :] + domain
                        return f"{real_username}@{domain_name}"

        # Last resort - handle complex domain forms
        if "." in email:
            parts = email.split(".")
            if len(parts) >= 3:
                # Try to identify domain patterns in multi-part emails
                for i in range(len(parts) - 1):
                    for provider in self.__popular_domain_hosts:
                        if parts[i] == provider:
                            username = ".".join(parts[:i])
                            tld = self.__domain_tld_mapping.get(provider, "com")
                            remaining = ".".join(parts[i + 1 :])
                            if i < len(parts) - 1:
                                if remaining == tld:
                                    return f"{username}@{provider}.{tld}"
                                else:
                                    return f"{username}@{provider}.{tld}"
                            else:
                                return f"{username}@{provider}.{tld}"

            # Default case - put @ before the last component
            username = email.rsplit(".", 1)[0]
            domain = email.rsplit(".", 1)[1]
            return f"{username}@{domain}.com"

        return email
