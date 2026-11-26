"""Size-aware job timeout and identity helpers."""

import unittest

from word_endpoint.config import Settings
from word_endpoint.runner import job_timeout_for


def settings(job_timeout_s: int = 120) -> Settings:
    return Settings(token="t" * 40, job_timeout_s=job_timeout_s)


class JobTimeoutTests(unittest.TestCase):
    MB = 1024 * 1024

    def test_small_uploads_get_the_base_budget(self):
        self.assertEqual(job_timeout_for(settings(), 0), 120)
        self.assertEqual(job_timeout_for(settings(), 2 * self.MB), 120)

    def test_large_uploads_get_scaled_extra_time(self):
        # 10 MB: 8 MB over the free allowance, 20 s per MB -> +160 s.
        self.assertEqual(job_timeout_for(settings(), 10 * self.MB), 280)

    def test_extra_time_is_capped(self):
        self.assertEqual(job_timeout_for(settings(), 500 * self.MB), 300)

    def test_base_budget_is_respected(self):
        self.assertEqual(job_timeout_for(settings(60), 10 * self.MB), 220)


if __name__ == "__main__":
    unittest.main()
