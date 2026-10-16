from aipc01_core import BaseFetcher, Target, run_cli


class OneDoc(BaseFetcher):
    source = "one"

    def discover(self):
        return [Target("https://example.com/a")]

    def fetch(self, target):
        raise RuntimeError("nope")


def test_cli_exit_code_reflects_failures(tmp_path):
    argv = ["--out", str(tmp_path), "--cache-dir", str(tmp_path / "c"), "--min-interval", "0"]
    assert run_cli("one", lambda a, c, s: OneDoc(c, s), argv) == 1
    assert run_cli("one", lambda a, c, s: OneDoc(c, s), [*argv, "--allow-failures"]) == 0
    assert (tmp_path / "_reports" / "one.json").exists()
