import pytest

from src.domains.normalize import build_display_url, is_known_giant, normalize_domain


class TestNormalizeDomain:
    def test_plain_domain(self):
        assert normalize_domain("example.com") == "example.com"

    def test_uppercase(self):
        assert normalize_domain("EXAMPLE.COM") == "example.com"

    def test_with_https(self):
        assert normalize_domain("https://example.com") == "example.com"

    def test_with_http(self):
        assert normalize_domain("http://example.com") == "example.com"

    def test_with_www(self):
        assert normalize_domain("https://www.example.com") == "example.com"

    def test_with_path_and_query(self):
        assert normalize_domain("https://www.Example.com/path?x=1&y=2") == "example.com"

    def test_with_subdomain(self):
        assert normalize_domain("https://app.example.com") == "example.com"

    def test_with_mobile_subdomain(self):
        assert normalize_domain("http://m.example.com") == "example.com"

    def test_co_uk_domain(self):
        assert normalize_domain("https://www.example.co.uk") == "example.co.uk"

    def test_com_br_domain(self):
        assert normalize_domain("https://www.example.com.br") == "example.com.br"

    def test_with_trailing_slash(self):
        assert normalize_domain("example.com/") == "example.com"

    def test_with_whitespace(self):
        assert normalize_domain("  example.com  ") == "example.com"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Empty domain string"):
            normalize_domain("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="Empty domain string"):
            normalize_domain("   ")

    def test_invalid_domain_raises(self):
        with pytest.raises(ValueError):
            normalize_domain("not-a-valid-domain-xyz")


class TestBuildDisplayUrl:
    def test_adds_https(self):
        assert build_display_url("example.com") == "https://example.com"

    def test_already_has_no_prefix(self):
        assert build_display_url("sub.example.com") == "https://sub.example.com"


class TestIsKnownGiant:
    def test_google_is_giant(self):
        assert is_known_giant("google.com") is True

    def test_youtube_is_giant(self):
        assert is_known_giant("youtube.com") is True

    def test_random_domain_not_giant(self):
        assert is_known_giant("some-random-startup.io") is False

    def test_case_sensitive_match(self):
        assert is_known_giant("Google.com") is False
