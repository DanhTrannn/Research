"""Humber Polytechnic: source URL and school-specific extraction rules."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import SchoolCrawler, run_school


class Crawler(SchoolCrawler):
    name = 'Humber Polytechnic'
    slug = 'humber_polytechnic'
    url = 'https://humber.ca/study-at-humber/pay-fees/scholarships-bursaries'


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
