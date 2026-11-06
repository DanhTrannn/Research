"""University of Waterloo: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import fetch_html, export_school, run_school, main_content, selected_awards, table_records, values, application_info, clean


class Crawler:
    name = 'University of Waterloo'
    slug = 'university_of_waterloo'
    url = 'https://uwaterloo.ca/future-students/financing/scholarships'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        scholarships = selected_awards(soup, r"^(President.s Scholarship(?: of Distinction)?|Merit Scholarship) \(admission average", type='scholarship')
        # Named scholarship rows only; exclude programme bundles without a distinct award name.
        for table in main_content(soup).find_all('table'):
            for row in table_records(table):
                if not row.get('scholarship'):
                    continue
                scholarships.append(clean({'name': row['scholarship'], 'type': 'scholarship',
                    'programs': row.get('eligible programs'), 'value_text': row.get('value'),
                    'values': values(row.get('value', '')), 'eligibility': row.get('criteria'),
                    'application': application_info([row.get('criteria', '')])}))
        return {'scholarships': scholarships}

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
