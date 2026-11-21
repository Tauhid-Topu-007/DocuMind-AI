import pytest

from app.services.web_scraper import ScrapeError, assert_public_url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "file:///etc/passwd",
        "http://127.0.0.1/",
        "http://localhost:8000/",
        "http://[::1]/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://user:pass@93.184.216.34/",
        "http://93.184.216.34:22/",
    ],
)
def test_blocked(url):
    with pytest.raises(ScrapeError):
        assert_public_url(url)


def test_public_ip_allowed():
    assert_public_url("https://93.184.216.34/")
