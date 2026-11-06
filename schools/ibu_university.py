"""International Business University (IBU): source URL and school-specific extraction rules."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re
from pipeline import SchoolCrawler, run_school


class Crawler(SchoolCrawler):
    name = 'International Business University (IBU)'
    slug = 'ibu_university'
    url = 'https://ibu.ca/admission/undergraduate-admissions/undergraduate-tuition-fees/entrance-scholarships/'

    def keep_section(self, candidate):
        """Domestic award families have explicit terms; retain them as groups."""
        return 'Domestic' in candidate.get('context_headings', [])

    def candidate_issue(self, candidate):
        """Regional tabs share content; don't assign their tuition to one award."""
        if re.search(r'bursary', candidate.get('name_en', ''), re.I):
            return 'regional_tab_boundaries_not_reliable'
        return None


if __name__ == '__main__':
    raise SystemExit(run_school(Crawler()))
