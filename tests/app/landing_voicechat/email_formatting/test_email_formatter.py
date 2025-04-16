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
            # Missing @ with only one dot (default to gmail.com)
            ("johndoe.com", "johndoe@gmail.com"),
            ("enelpunto.com", "enelpunto@gmail.com"),
            # Known domain handling
            ("example.mycompany.com", "example@mycompany.com"),
            ("john.gmail.com", "john@gmail.com"),
            ("john.yahoo.com", "john@yahoo.com"),
            ("user.domain.co.uk", "user@domain.co.uk"),
            # Complex cases with multiple dots
            ("juad.david.gomez.gmail.com", "juad.david.gomez@gmail.com"),
            ("jane.doe.outlook.com", "jane.doe@outlook.com"),
            ("james.smith.mycompany.com", "james.smith@mycompany.com"),
            # Misspelled or speech-to-text errors
            ("Juan David gomez at gmail dot com", "juandavidgomez@gmail.com"),
            ("Juan David gomez arroba gmail punto com", "juandavidgomez@gmail.com"),
            ("info at my dash company dot co dot uk", "info@my-company.co.uk"),
            # Edge cases
            ("user.hotmail", "user@hotmail.com"),  # Incomplete domain
            ("just_a_username", "just_a_username"),  # No domain or dots
            (
                "user at protonmail",
                "user@protonmail.com",
            ),  # Incomplete domain with 'at'
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
        ]

        invalid_emails = [
            "test.example.com",
            "test@example",
            "user name@domain.com",
            "@domain.com",
        ]

        for email in valid_emails:
            assert formatter._EmailFormatter__is_valid_email(email) is True

        for email in invalid_emails:
            assert formatter._EmailFormatter__is_valid_email(email) is False

    def test_has_known_domain(self, formatter):
        # Test the private method directly
        domains_present = ["user.gmail.com", "example.co.uk", "test.mysite.com"]

        domains_absent = ["usermail", "test.unknowndomain", "user@invalid"]

        for email in domains_present:
            assert formatter._EmailFormatter__has_known_domain(email) is True

        for email in domains_absent:
            assert formatter._EmailFormatter__has_known_domain(email) is False
