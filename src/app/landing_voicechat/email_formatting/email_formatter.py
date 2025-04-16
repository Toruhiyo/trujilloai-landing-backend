from src.utils.metaclasses import DynamicSingleton
import re
import json
from pathlib import Path


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
                    return f"{username}@{provider}.com"

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
        # Remove spaces around punctuation first
        email = re.sub(r"\s*([.,;:])\s*", r"\1", email)

        # Process each replacement
        for word, symbol in self.__spoken_symbols.items():
            pattern = rf"(^|\s){re.escape(word)}(\s|$)"
            email = re.sub(pattern, rf"\1{symbol}\2", email)

        # Do a final cleanup to ensure all punctuation has no spaces
        email = re.sub(r"\s*@\s*", "@", email)
        email = re.sub(r"\s*\.\s*", ".", email)
        email = re.sub(r"\s*_\s*", "_", email)
        email = re.sub(r"\s*-\s*", "-", email)

        return email

    def __is_valid_email(self, email: str) -> bool:
        # Simple regex to check if email has basic valid format
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    def __fix_incomplete_domain(self, email: str) -> str:
        """Add .com to incomplete domains like hotmail, gmail, etc."""
        if "@" not in email:
            return email

        username, domain = email.split("@", 1)

        # Check if domain is incomplete
        for incomplete in self.__popular_domain_hosts:
            if domain == incomplete:
                return f"{username}@{domain}.com"

        # Check if domain has no TLD
        if "." not in domain:
            return f"{username}@{domain}.com"

        return email

    def __fix_missing_at_symbol(self, email: str) -> str:
        # First special case: domain-only with dot
        if "." in email and email.count(".") == 1:
            # Handle specific domains
            for provider in self.__popular_domain_hosts:
                if email.startswith(f"{provider}."):
                    return f"user@{email}"
                elif email == f"{provider}":
                    return f"user@{provider}.com"

            # Default domain logic (from above is handled first so we don't duplicate)
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
            if parts[1] in [
                d.strip(".") for d in self.__common_domains if len(d.strip(".")) <= 3
            ]:
                return f"{parts[0]}@gmail.{parts[1]}"

            # Handle specific providers in domain part
            for provider in self.__popular_domain_hosts:
                if parts[1].startswith(provider):
                    return f"{parts[0]}@{parts[1]}.com"

            return f"{parts[0]}@gmail.com"

        if len(parts) >= 2:
            # Find a domain part (typically after the last dot or second-to-last dot)
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
        # Check if the email contains any of the known domains
        for domain in self.__common_domains:
            if domain in email:
                return True

        # Check for popular email providers
        for provider in self.__popular_email_providers:
            if provider in email:
                return True

        return False

    def __add_at_with_known_domain(self, email: str) -> str:
        # Try to find the right place to insert the @ symbol based on known domains

        # First check for known email providers
        for provider in self.__popular_email_providers:
            if provider in email:
                # Split at the provider
                parts = email.split(provider)
                if len(parts) == 2:
                    username = parts[0].rstrip(".")
                    return f"{username}@{provider}{parts[1]}"
                else:
                    # This might be username.gmail.com
                    username = email[: email.find(provider)].rstrip(".")
                    domain = provider + email[email.find(provider) + len(provider) :]
                    return f"{username}@{domain}"

        # Check for more specific domains first - handle partial names
        for provider in self.__popular_domain_hosts:
            if f".{provider}." in email or email.endswith(f".{provider}"):
                parts = email.split(f".{provider}")
                if len(parts) >= 1:
                    return f"{parts[0]}@{provider}.com"

        # Try to identify domain pattern with TLDs
        for domain in sorted(self.__common_domains, key=len, reverse=True):
            if domain in email:
                # Find potential domain boundaries
                domain_index = email.find(domain)

                # Find the starting point of the domain
                # We need to go backwards from the TLD to find where the domain starts
                start_index = email.rfind(".", 0, domain_index)
                if start_index == -1:  # No dot before the domain
                    # Try to find the boundary between username and domain
                    # Common separators might be underscores or dots
                    for separator in ["_", "."]:
                        separator_index = email.rfind(separator, 0, domain_index)
                        if separator_index != -1 and separator_index < domain_index - 1:
                            start_index = separator_index
                            break

                if start_index == -1:
                    # Couldn't find a natural boundary, use heuristics
                    # Try to detect patterns like "username.domain.com"
                    parts = email.split(".")
                    if len(parts) >= 3:
                        return f"{parts[0]}@{'.'.join(parts[1:])}"
                    elif len(parts) == 2:
                        domain_part = parts[1]
                        # Check if domain starts with common domain name
                        for common_domain in self.__popular_domain_hosts:
                            if domain_part.startswith(common_domain):
                                return f"{parts[0]}@{domain_part}"

                # If we found a separator
                if start_index != -1:
                    username = email[:start_index]
                    domain = email[start_index + 1 :]
                    return f"{username}@{domain}"

        # Fallback to the best guess
        # Try to split at the second-to-last dot
        parts = email.split(".")
        if len(parts) >= 3:
            # Assume format username.domain.tld
            return f"{parts[0]}@{'.'.join(parts[1:])}"

        return email
