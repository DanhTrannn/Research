"""MacEwan University: source URL and school-specific extraction rules."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import SchoolCrawler, run_school


class Crawler(SchoolCrawler):
    name = 'MacEwan University'
    slug = 'macewan_university'
    url = 'https://www.macewan.ca/apply-enrol/fees-finances/scholarships-awards-bursaries/entrance-scholarships/'


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
