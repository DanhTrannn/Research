"""University of Ottawa: source URL and school-specific extraction rules."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import SchoolCrawler, run_school


class Crawler(SchoolCrawler):
    name = 'University of Ottawa'
    slug = 'university_of_ottawa'
    url = 'https://www.uottawa.ca/study/fees-financial-support/international-english-scholarship'


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
