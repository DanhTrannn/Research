"""University of Waterloo: source URL and school-specific extraction rules."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import SchoolCrawler, run_school


class Crawler(SchoolCrawler):
    name = 'University of Waterloo'
    slug = 'university_of_waterloo'
    url = 'https://uwaterloo.ca/future-students/financing/scholarships'


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
