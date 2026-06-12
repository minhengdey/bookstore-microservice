import re
import unittest
from pathlib import Path


class RecommenderComposeConfigTest(unittest.TestCase):
    def test_recommender_service_mounts_common_package(self):
        lines = Path("docker-compose.yml").read_text(encoding="utf-8").splitlines()

        start = next(i for i, line in enumerate(lines) if line.strip() == "recommender-ai-service:")
        end = next(
            (
                i
                for i in range(start + 1, len(lines))
                if re.match(r"^  [A-Za-z0-9_-]+:", lines[i]) and not lines[i].startswith("    ")
            ),
            len(lines),
        )

        block = "\n".join(lines[start:end])

        self.assertIn("recommender-ai-service:", block)
        self.assertIn("      - ./common:/app/common", block)


if __name__ == "__main__":
    unittest.main()
