import pytest
from src.app.landing_voicechat.email_formatting.email_formatter import EmailFormatter


class TestEmailFormatter:

    @pytest.fixture
    def formatter(self):
        return EmailFormatter()

    @pytest.mark.parametrize(
        "input_email,expected_output",
        [
            # Basic test cases
            ("test@example.com", "test@example.com"),
            ("TEST@EXAMPLE.COM", "test@example.com"),
            # Space removal
            ("test @ example.com", "test@example.com"),
            ("test@example . com", "test@example.com"),
            # Spoken pattern replacement
            ("test at example dot com", "test@example.com"),
            ("test arroba example punto com", "test@example.com"),
            ("john underscore doe at gmail dot com", "john_doe@gmail.com"),
            # Added new spoken symbols
            ("john underline doe point gmail period com", "john_doe@gmail.com"),
            ("user dash name at domain point io", "user-name@domain.io"),
            ("contact hyphen us at company dot co", "contact-us@company.co"),
            ("support guion tecnico at empresa punto es", "support-tecnico@empresa.es"),
            ("john subrayado doe arroba outlook punto com", "john_doe@outlook.com"),
            # Missing @ with only one dot (default to gmail.com)
            ("johndoe.com", "johndoe@gmail.com"),
            ("enelpunto.com", "enelpunto@gmail.com"),
            # Known domain handling
            ("example.mycompany.com", "example@mycompany.com"),
            ("john.gmail.com", "john@gmail.com"),
            ("john.yahoo.com", "john@yahoo.com"),
            ("user.domain.co.uk", "user@domain.co.uk"),
            # New email providers
            ("john.zoho.com", "john@zoho.com"),
            ("user.fastmail.com", "user@fastmail.com"),
            ("contact.tutanota.com", "contact@tutanota.com"),
            ("jane.hey.com", "jane@hey.com"),
            ("user.msn.com", "user@msn.com"),
            ("john.live.com", "john@live.com"),
            # Complex cases with multiple dots
            ("juad.david.gomez.gmail.com", "juad.david.gomez@gmail.com"),
            ("jane.doe.outlook.com", "jane.doe@outlook.com"),
            ("james.smith.mycompany.com", "james.smith@mycompany.com"),
            ("thomas.white.fastmail.com", "thomas.white@fastmail.com"),
            # Misspelled or speech-to-text errors
            ("Juan David gomez at gmail dot com", "juandavidgomez@gmail.com"),
            ("Juan David gomez arroba gmail punto com", "juandavidgomez@gmail.com"),
            ("info at my dash company dot co dot uk", "info@my-company.co.uk"),
            # New TLDs
            ("contact at our dash startup dot dev", "contact@our-startup.dev"),
            ("hello at myapp dot app", "hello@myapp.app"),
            ("info at business dot info", "info@business.info"),
            # New country domains
            ("user dot mydomain dot com dot mx", "user@mydomain.com.mx"),
            ("contact at company dot co dot nz", "contact@company.co.nz"),
            ("support at website dot com dot sg", "support@website.com.sg"),
            # Edge cases
            ("user.hotmail", "user@hotmail.com"),  # Incomplete domain
            ("just_a_username", "just_a_username"),  # No domain or dots
            (
                "user at protonmail",
                "user@protonmail.com",
            ),  # Incomplete domain with 'at'
            (
                "info at verizon",
                "info@verizon.net",
            ),  # New provider with incomplete domain
            (
                "contact at comcast",
                "contact@comcast.net",
            ),  # New provider with incomplete domain
        ],
    )
    def test_compute(self, formatter, input_email, expected_output):
        result = formatter.compute(input_email)
        assert result == expected_output, f"Failed for input: {input_email}"

    def test_replace_spoken_symbols(self, formatter):
        # Test the private method directly
        test_cases = [
            ("user at example dot com", "user@example.com"),
            ("jane underscore doe at gmail", "jane_doe@gmail"),
            ("info dash support at company punto es", "info-support@company.es"),
            # New test cases for added spoken symbols
            ("support hyphen desk at business period com", "support-desk@business.com"),
            ("john underline doe point domain", "john_doe.domain"),
            ("contact guion us at our subrayado company", "contact-us@our_company"),
        ]

        for input_text, expected in test_cases:
            result = formatter._EmailFormatter__replace_spoken_symbols(input_text)
            assert expected == result

    def test_is_valid_email(self, formatter):
        # Test the private method directly
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user-name@domain.com",
            "user123@domain.co",
            # Add new valid email formats
            "firstname.lastname@company.com.sg",
            "user_name@domain.dev",
            "info-support@business.app",
        ]

        invalid_emails = [
            "test.example.com",
            "test@example",
            "user name@domain.com",
            "@domain.com",
            # Add new invalid email formats
            "user@.com",
            "user@domain.",
            ".user@domain.com",
        ]

        for email in valid_emails:
            assert formatter._EmailFormatter__is_valid_email(email) is True

        for email in invalid_emails:
            assert formatter._EmailFormatter__is_valid_email(email) is False

    def test_has_known_domain(self, formatter):
        # Test the private method directly
        domains_present = [
            "user.gmail.com",
            "example.co.uk",
            "test.mysite.com",
            # New domains
            "contact.tutanota.com",
            "info.zoho.com",
            "user.domain.dev",
            "company.com.sg",
        ]

        domains_absent = [
            "usermail",
            "test.unknowndomain",
            "user@invalid",
            # New absent domains
            "user.nonexistent",
            "unknown.xyz",
        ]

        for email in domains_present:
            assert formatter._EmailFormatter__has_known_domain(email) is True

        for email in domains_absent:
            assert formatter._EmailFormatter__has_known_domain(email) is False
