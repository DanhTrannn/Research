"""Queen's University: crawl -> extract selected scholarship data -> JSON."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import (award, clean, export_school, fetch_html, main_content, run_school,
                      scope_filter, sections, table_records, text, values)

DETAIL_LABELS = ('Program of Study', 'Criteria', 'Duration', 'Annual Value',
                 'Number available', 'Deadline to apply')


def split_details(raw):
    pattern = r'(?:^|\s)(' + '|'.join(map(re.escape, DETAIL_LABELS)) + r'):\s*'
    matches = list(re.finditer(pattern, raw, re.I))
    fields = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        fields[match.group(1).lower()] = raw[match.end():end].strip()
    return fields


def add_values(item, field, basis):
    value_text = field or ''
    item['value_text'] = value_text or None
    item['values'] = values(value_text) if value_text else []
    for value in item['values']:
        value['payment_basis'] = basis
    return item


def section_paragraphs(soup, pattern):
    return dict(sections(soup, pattern))


class Crawler:
    name = "Queen's University"
    slug = 'queens_university'
    url = 'https://www.queensu.ca/registrar/financial-aid/specific-students/international'

    def crawl(self, timeout=12):
        return fetch_html(self.url, timeout)

    def extract(self, soup):
        root = main_content(soup)
        scholarships = []

        for table in root.find_all('table'):
            records = table_records(table)
            if not records:
                continue
            keys = set(records[0])

            # Dean's International Award Program: one row per faculty award.
            if {'award', 'details'} <= keys:
                for row in records:
                    name = row.get('award', '')
                    if 'International Admission Award' not in name:
                        continue
                    fields = split_details(row.get('details', ''))
                    item = clean({
                        'name': name,
                        'type': 'scholarship',
                        'applicant_category': 'international',
                        'international_eligible': True,
                        'eligible_stages': ['entrance'],
                        'programs': fields.get('program of study'),
                        'eligibility': fields.get('criteria'),
                        'duration': fields.get('duration'),
                        'renewable': True,
                        'application': {'method': 'automatic'},
                        'source_url': self.url,
                    })
                    add_values(item, fields.get('annual value'), 'per_year')
                    scholarships.append(item)
                continue

            # Individual award tables use Category / Details rows.
            if {'category', 'details'} <= keys:
                heading = table.find_previous(re.compile(r'^h[1-6]$'))
                name = text(heading) if heading is not None else ''
                if name not in ("Principal's Scholarship",
                                'Mehran Bibi Sheikh Memorial Entrance Scholarship',
                                'Killam American Scholarship'):
                    continue
                fields = {row.get('category', '').lower(): row.get('details', '')
                          for row in records}
                item = clean({
                    'name': name,
                    'type': 'scholarship',
                    'applicant_category': 'all' if name == "Principal's Scholarship" else 'international',
                    'international_eligible': True,
                    'eligible_stages': ['entrance'],
                    'programs': fields.get('program of study'),
                    'eligibility': fields.get('criteria'),
                    'duration': fields.get('duration'),
                    'number_of_awards': int(m.group(1)) if (
                        m := re.match(r'\s*(\d+)', fields.get('number available', ''))) else None,
                    'application': {'method': 'automatic'},
                    'source_url': self.url,
                })
                add_values(item, fields.get('annual value'), 'one_time')
                if name == "Principal's Scholarship":
                    paragraphs = section_paragraphs(soup, r'^Principal.s Scholarship$').get(name, [])
                    description = next((p for p in paragraphs if 'top 3%' in p), None)
                    if description:
                        item['description'] = description
                scholarships.append(item)

        # Principal's Global Scholars Undergraduate Award is prose, not a table.
        name = "Principal's Global Scholars Undergraduate Award"
        paragraphs = next(iter(section_paragraphs(
            soup, r'^Principal.s Global Scholars Undergraduate Award$').values()), [])
        if paragraphs:
            scholarships.append(award(
                name, paragraphs, type='scholarship', applicant_category='international',
                international_eligible=True, eligible_stages=['entrance'],
                application={'method': 'automatic'}, source_url=self.url))

        return {'scholarships': scope_filter(scholarships),
                'notes': ['Only first-entry international admission scholarships are exported; '
                          'visiting-student awards, loans and other financial-aid options are excluded.']}

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
