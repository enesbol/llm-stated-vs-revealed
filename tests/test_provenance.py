"""Acceptance criterion: every vendored file passes its recorded SHA-256."""

from stated_vs_revealed.provenance import verify


def test_all_vendor_files_pass_checksum():
    ok, fail, problems = verify()
    assert fail == 0, "MANIFEST.sha256 verification failed:\n" + "\n".join(problems)
    assert ok > 0
