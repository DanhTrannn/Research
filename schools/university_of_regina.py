"""University of Regina: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import fetch_html, export_school, run_school, schedule_tables


class Crawler:
    name = 'University of Regina'
    slug = 'university_of_regina'
    url = 'https://www.uregina.ca/cost-aid/funding/undergraduate-scholarships/index.html'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        # This URL is an overview: extract its award application schedules, not FAQ dollar totals.
        return {'scholarships': [], 'application_periods': schedule_tables(soup, r'Award Deadlines|Scholarship Deadlines'),
                'notes': ['Overview page: individual award amounts and eligibility require the linked SAMS catalogue.']}

    def export(self, metadata, data, output_dir=None):
        return export_school(self, metadata, data, output_dir)

    def run(self, output_dir=None, timeout=12):
        metadata, soup = self.crawl(timeout)
        data = {'scholarships': []}
        if soup is not None:
            try:
                data = self.extract(soup)
                if not data.get('scholarships') and not data.get('application_periods'):
                    metadata['fetch_status'] = 'no_data'
            except Exception as exc:
                metadata['fetch_status'] = 'extraction_error'
                data = {'scholarships': [], 'notes': [str(exc)]}
        return self.export(metadata, data, output_dir)


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
