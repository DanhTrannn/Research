"""Lakehead University: source URL and school-specific extraction rules."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import SchoolCrawler, run_school, source_ref


class Crawler(SchoolCrawler):
    name = 'Lakehead University'
    slug = 'lakehead_university'
    url = 'https://www.lakeheadu.ca/international/future/scholarships-awards'

    def renewal_footnotes(self, data, value_text, file):
        """Attach only explicitly numbered footnotes from the single tier table."""
        statements, refs = [], []
        marker = re.search(r'\)\s*(\d+)\s*$', value_text)
        if marker and len(data.get('tables_data', [])) == 1:
            for polarity in ('positive', 'negative'):
                for index, statement in enumerate(data.get('renewal_evidence', {}).get(polarity, [])):
                    if re.match(r'^' + re.escape(marker[1]) + r'\s', statement):
                        statements.append(statement)
                        refs.append(source_ref(file, f'/extracted_data/renewal_evidence/{polarity}/{index}'))
        return statements, refs


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
