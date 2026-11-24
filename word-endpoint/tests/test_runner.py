"""Size-aware job timeout and identity helpers."""

import unittest
from pathlib import Path

from word_endpoint.config import Settings
from word_endpoint.runner import JobError, _Lane, job_timeout_for


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



class LaneShutdownTests(unittest.TestCase):
    def test_a_stopped_lane_never_starts_another_worker(self):
        spawned = []
        lane = _Lane("convert", lambda kind: spawned.append(kind) or ["unused"], "winword.exe")
        lane.stop()
        # A warm-up thread (ensure) and a request that was queued on the lane
        # (run) both reach _spawn after stop() released the lane.
        for call in (lambda: lane.ensure(1), lambda: lane.run("convert", Path("unused"), 1)):
            with self.assertRaises(JobError) as caught:
                call()
            self.assertEqual(caught.exception.code, "busy")
        self.assertEqual(spawned, [])
        self.assertEqual(lane.health()["state"], "stopped")


if __name__ == "__main__":
    unittest.main()
