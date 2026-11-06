"""Queen's University: source URL and school-specific extraction rules."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import SchoolCrawler, run_school


class Crawler(SchoolCrawler):
    name = "Queen's University"
    slug = 'queens_university'
    url = 'https://www.queensu.ca/registrar/financial-aid'


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
