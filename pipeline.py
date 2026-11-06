"""Shared fetch, DOM extraction and normalization. School rules live in schools/*.py.

One public pipeline: SchoolCrawler.run() -> one self-contained JSON per school.
No network requests are made at import time. No intermediate exports or snapshots.
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'en-US,en;q=0.9',
}
NEGATIVE_RENEWAL = re.compile(r'\b(?:non[\s-]*renewable|not\s+renewable|not\s+be\s+renewed|cannot\s+be\s+renewed|one[\s-]*time|tenable for (?:1|one) year only|single payment|(?:first year|year 1) only)\b', re.I)
POSITIVE_RENEWAL = re.compile(r'\b(?:renewable|renewed|renewability|renewal requirements|renewal conditions)\b', re.I)


def now():
    return datetime.now(timezone.utc).isoformat()


def text(tag):
    return re.sub(r'\s+', ' ', tag.get_text(' ', strip=True)).strip()


# Text parsers: money, dates, grade bands and explicit source statements.
MONEY = re.compile(r'\$\s*(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?![\d,])')
NEGATION = re.compile(r'\b(?:non[ -]?renewable|not renewable|cannot be renewed|not be renewed|one[ -]time|(?:first year|year 1) only)\b', re.I)
POSITIVE = re.compile(r'\b(?:renewable|renewed)\b', re.I)
ADMIN = re.compile(r'^(?:type of award|bursary application|award recipient information|award applications|scholarship application help|search our)|\bdeadlines?\b', re.I)
MONTHS = r'January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec'
DATE = re.compile(r'\b(' + MONTHS + r')\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b', re.I)


def compact(value):
    return re.sub(r'\s+', ' ', str(value)).strip()


def key(value):
    return re.sub(r'[^a-z0-9]+', ' ', str(value).lower()).strip()


def stable_id(prefix, value):
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
    return f'{prefix}_{digest}'


def distinct(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def lines(candidate):
    evidence = candidate.get('evidence', [])
    return [compact(e) for e in (evidence if isinstance(evidence, list) else [evidence]) if compact(e)]


def source_ref(file, pointer):
    return {'file': file, 'json_pointer': pointer}


def grade(raw, system='academic_average_percent'):
    """Parse a single explicit grade band, not every number in prose."""
    value = compact(raw).replace('–', '-').replace('−', '-')
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*%?\s*(?:-\s*(\d+(?:\.\d+)?)\s*%?|(\+))?', value)
    if not match and system == 'academic_average_percent':
        # Preserve credential qualifiers while recognizing an explicit 80%+.
        match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:-\s*(\d+(?:\.\d+)?)\s*%?|(\+))', value)
    if match:
        lower = float(match[1])
        upper = float(match[2]) if match[2] else None
        ceiling = 45 if system == 'international_baccalaureate' else 100
        if lower > ceiling or (upper is not None and (upper > ceiling or lower > upper)):
            match = None
    return {'system': system, 'min': float(match[1]) if match else None,
            'max': float(match[2]) if match and match[2] else None,
            'minimum_inclusive': True if match else None, 'raw': raw}


def renewal(evidence):
    negatives = [s for s in evidence if NEGATION.search(s)]
    positives = [s for s in evidence if POSITIVE.search(NEGATION.sub(' ', s))]
    value = None if bool(negatives) == bool(positives) else bool(positives)
    return {'is_renewable': value, 'conditions_text': distinct(positives + negatives)}


def date_value(raw):
    raw = compact(raw)
    iso = None
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
        try:
            iso = datetime.strptime(raw, '%Y-%m-%d').date().isoformat()
        except ValueError:
            pass
    else:
        match = DATE.search(raw)
        if match and match[3]:
            for fmt in ('%B %d %Y', '%b %d %Y'):
                try:
                    month = 'Sep' if match[1].lower() == 'sept' else match[1]
                    iso = datetime.strptime(f'{month} {match[2]} {match[3]}', fmt).date().isoformat()
                    break
                except ValueError:
                    continue
    return {'raw': raw, 'date': iso}


def money_values(raw, header='', currency=None):
    """Recognize explicit value statements without computing missing totals."""
    raw = compact(raw)
    found = list(MONEY.finditer(raw))
    if not found:
        return []
    values = []
    def claim(amount, basis, fragment, maximum_only=False, minimum_only=False, payments=None):
        return {'kind': 'money', 'currency': currency,
                'min_amount': None if maximum_only else amount,
                'max_amount': None if minimum_only else amount,
                'payment_basis': basis, 'max_payments': payments, 'evidence_text': fragment}
    consumed = set()
    # Example: $40,000 ($10,000 x 4 years). Keep two distinct bases.
    schedule = re.search(r'\$\s*([\d,]+(?:\.\d+)?)\s*[x×]\s*(\d+)\s*years?', raw, re.I)
    if schedule:
        values.append(claim(float(schedule[1].replace(',', '')), 'per_year', schedule[0], payments=int(schedule[2])))
        consumed.update(m.start() for m in found if schedule.start() <= m.start() < schedule.end())
    ranged = re.search(r'\$\s*([\d,]+(?:\.\d+)?)\s*[-–]\s*\$\s*([\d,]+(?:\.\d+)?)', raw)
    if ranged and len(found) == 2:
        lower, upper = (float(ranged[i].replace(',', '')) for i in (1, 2))
        if lower <= upper:
            value = claim(lower, 'unknown', raw)
            value['max_amount'] = upper
            if re.search(r'\bper year\b|/\s*year', raw, re.I):
                value['payment_basis'] = 'per_year'
            elif re.search(r'\bper term\b|/\s*term', raw, re.I):
                value['payment_basis'] = 'per_term'
            elif re.search(r'\bone[ -]time\b', raw, re.I):
                value['payment_basis'] = 'one_time'
            return [value]
    for index, match in enumerate(found):
        if match.start() in consumed:
            continue
        # Only text up to the next amount belongs to this amount's basis.
        tail = raw[match.end():found[index + 1].start() if index + 1 < len(found) else len(raw)]
        head = raw[max(0, match.start() - 25):match.start()]
        basis = 'unknown'
        if re.search(r'\bper term\b|/\s*term', tail, re.I):
            basis = 'per_term'
        elif re.search(r'\bper year\b|/\s*year', tail, re.I):
            basis = 'per_year'
        elif re.search(r'\b(?:one[ -]time|year 1 only|first year only)\b', tail, re.I):
            basis = 'one_time'
        elif len(found) == 1 and re.search(r'\bone[ -]time\b', raw, re.I):
            basis = 'one_time'
        elif re.search(r'over (?:the course of )?(?:a )?(?:four[ -]year degree|\d+ years)|total', tail, re.I):
            basis = 'total_degree'
        elif index == 0 and re.search(r'scholarship total|maximum.*over.*years', header, re.I):
            basis = 'total_degree'
        value = claim(float(match[1].replace(',', '')), basis, raw,
                      maximum_only=bool(re.search(r'up to\s*(?:CAN\s*)?$', head, re.I)),
                      minimum_only=bool(re.search(r'from\s*$', head, re.I)))
        values.append(value)
    return distinct(values)


def explicit_currency(text):
    if re.search(r'\bCAD\b|Canadian dollars|CAN\s*\$', text, re.I):
        return 'CAD'
    if re.search(r'\bUSD\b|US\s*\$', text, re.I):
        return 'USD'
    return None


def columns(candidate):
    headers, values = candidate.get('column_headers', []), candidate.get('row_values', [])
    return {key(h): values[i] for i, h in enumerate(headers) if i < len(values)}


def first_column(mapping, pattern):
    return next((v for k, v in mapping.items() if re.search(pattern, k)), None)


def category(name, contexts, evidence, row):
    flag = first_column(row, r'open to international')
    international_eligible = {'yes': True, 'no': False}.get(key(flag)) if flag else None
    scope = ' '.join(contexts + [name])
    domestic = bool(re.search(r'\bdomestic\b|Canadian/domestic', scope, re.I))
    international = bool(re.search(r'\binternational\b', scope, re.I))
    if any(re.match(r'Be an international student\b', s, re.I) for s in evidence):
        international = True
    applicant = 'domestic' if domestic and not international else 'international' if international and not domestic else 'unknown'
    return applicant, international_eligible


def application(evidence, row):
    flag = first_column(row, r'^application required$')
    required = {'yes': True, 'no': False}.get(key(flag)) if flag else None
    method = 'unknown'
    combined = ' '.join(evidence)
    if re.search(r'\b(?:automatic scholarship|automatically (?:awarded|considered)|automatic consideration)\b', combined, re.I):
        method = 'automatic'
    instructions = first_column(row, r'application form')
    if instructions:
        # A "No" flag can coexist with instructions to use a common portal.
        method = 'unknown'
    deadlines = []
    for value in evidence:
        if (re.search(r'deadline|apply by|application (?:is )?required by', value, re.I)
                and not re.search(r'tuition|disbursement|SOLUS', value, re.I)):
            for match in DATE.finditer(value):
                deadlines.append(dict(date_value(match[0]), evidence_text=value))
    return {'method': method, 'application_required_flag': required,
            'instructions_text': instructions, 'deadlines': distinct(deadlines)}


# DOM extraction; reusable across all school pages.
class PageParser:
    @staticmethod
    def validate_html(status, body, content_type='text/html'):
        soup = BeautifulSoup(body, 'html.parser')
        title = text(soup.title).lower() if soup.title else ''
        raw = body.decode('utf-8', errors='replace') if isinstance(body, bytes) else body
        if status in (202, 401, 403, 429):
            return None, 'blocked'
        if status != 200:
            return None, 'http_error'
        if (title in {'just a moment...', 'access denied', 'attention required! | cloudflare'}
                or any(marker in raw.lower() for marker in (
                    'awswaf.setup', 'aws-waf-token', '_cf_chl_opt', 'id="challenge-form"', 'cf-chl-'))):
            return None, 'blocked'
        if 'html' not in content_type.lower() or not soup.find(['h1', 'h2', 'h3', 'table']):
            return None, 'invalid_content'
        if re.search(r'\b(?:404|page not found|page cannot be found)\b', title):
            return None, 'not_found'
        if not re.search(r'scholarship|award|bursar|financial aid', text(soup), re.I):
            return None, 'unexpected_content'
        return soup, None

    @staticmethod
    def content(soup):
        if soup is None:
            return None
        clean = BeautifulSoup(str(soup), 'html.parser')
        for tag in clean.select('script, style, nav, footer, aside, form, blockquote, [role=navigation], .testimonial'):
            tag.decompose()
        root = clean.find('main') or clean.find(id='content') or clean.find('article') or clean.body or clean
        # Remove elements preceding the page h1 in themes without a main landmark.
        h1 = root.find('h1')
        if h1:
            before = []
            for node in root.descendants:
                if node is h1:
                    break
                if getattr(node, 'name', None) and not node.find('h1'):
                    before.append(node)
            for node in reversed(before):
                node.decompose()
        return root

    def extract_title(self, soup):
        return text(soup.title) if soup and soup.title else None

    def extract_h1(self, soup):
        h = soup.find('h1') if soup else None
        return text(h) if h else None

    def extract_tables(self, soup):
        """Preserve all cells/spans and an expanded rectangular grid."""
        tables = []
        if not soup:
            return tables
        for index, table in enumerate(soup.find_all('table')):
            physical, occupied = [], {}
            own_rows = [tr for tr in table.find_all('tr') if tr.find_parent('table') is table]
            for row_index, tr in enumerate(own_rows):
                cells, column = [], 0
                for cell in tr.find_all(['td', 'th'], recursive=False):
                    while (row_index, column) in occupied:
                        column += 1
                    def span(key):
                        try:
                            value = int(cell.get(key, 1))
                            if key == 'rowspan':
                                return len(own_rows) - row_index if value == 0 else max(1, min(value, len(own_rows) - row_index))
                            return max(1, min(value, 1000))
                        except (TypeError, ValueError):
                            return 1
                    rowspan, colspan = span('rowspan'), span('colspan')
                    value = text(cell)
                    cells.append({'text': value, 'tag': cell.name, 'rowspan': rowspan, 'colspan': colspan,
                                  'rowspan_raw': cell.get('rowspan'), 'colspan_raw': cell.get('colspan'),
                                  'column_index': column})
                    for dr in range(rowspan):
                        for dc in range(colspan):
                            occupied[row_index + dr, column + dc] = value
                    column += colspan
                if cells:
                    physical.append({'row_index': row_index, 'cells': cells})
            height = max((r for r, _ in occupied), default=-1) + 1
            width = max((c for _, c in occupied), default=-1) + 1
            grid = [[occupied.get((r, c), '') for c in range(width)] for r in range(height)]
            header_rows = [r for r in physical if all(c['tag'] == 'th' for c in r['cells'])]
            rows = [[c['text'] for c in r['cells']] for r in physical if any(c['tag'] == 'td' for c in r['cells'])]
            heading = table.find_previous(re.compile(r'^h[1-6]$'))
            context, level = [], 7
            for h in table.find_all_previous(re.compile(r'^h[1-6]$')):
                if int(h.name[1]) < level:
                    context.append(text(h))
                    level = int(h.name[1])
            tables.append({'table_index': index, 'heading': text(heading) if heading else None,
                           'context_headings': context[::-1],
                           'headers': [c['text'] for c in header_rows[0]['cells']] if header_rows else [],
                           'rows_count': len(rows), 'rows': rows, 'cells': physical, 'grid': grid})
        return tables

    @staticmethod
    def blocks(soup):
        if soup is None:
            return []
        # Some schools put actual terms in standalone <sup> or <div><br> blocks.
        # Retain inline footnotes inside their containing paragraph/cell.
        block_tags = ['p', 'li', 'td', 'th', 'small', 'div', 'section']
        result, selected = [], set()
        for tag in soup.find_all(block_tags + ['sup']):
            if (not tag.find(block_tags) and text(tag)
                    and not any(id(parent) in selected for parent in tag.parents)):
                result.append(tag)
                selected.add(id(tag))
        return result

    def renewal_evidence(self, soup):
        positive, negative = [], []
        for tag in self.blocks(soup):
            value = text(tag)
            if re.search(r'\b(?:my scholarship|I felt|I was|testimonial)\b', value, re.I):
                continue
            if NEGATIVE_RENEWAL.search(value):
                negative.append(value)
            unnegated = NEGATIVE_RENEWAL.sub(' ', value)
            if POSITIVE_RENEWAL.search(unnegated) or re.search(
                r'(?:third semester|term 3).*(?:continue|minimum|GPA)|'
                r'(?:continue|minimum|GPA).*(?:third semester|term 3)', unnegated, re.I):
                positive.append(value)
        return list(dict.fromkeys(positive)), list(dict.fromkeys(negative))

    def _matching_blocks(self, soup, pattern):
        return list(dict.fromkeys(text(t) for t in self.blocks(soup) if re.search(pattern, text(t), re.I)))

    def extract_eligibility(self, soup):
        return self._matching_blocks(soup, r'admission average|admitted with|minimum (?:GPA|average)|'
                                     r'high school average|eligible|eligibility|study permit|citizen|resident')

    def scholarship_candidates(self, soup, tables):
        """Human review units, never automatically verified/publishable awards."""
        candidates = []
        for table in tables:
            headers = table['headers']
            named = bool(headers and re.fullmatch(r'award name|scholarship(?: name)?', headers[0], re.I))
            tiered = bool(headers and re.search(r'average|grade', headers[0], re.I)
                          and any(re.search(r'amount|value|scholarship total|year 1', h, re.I) for h in headers[1:]))
            if not (named or tiered):
                continue
            for row_index, row in enumerate(table['rows']):
                if not row or not row[0]:
                    continue
                name = row[0] if named else table['heading']
                candidates.append({'candidate_id': f"table-{table['table_index']}-row-{row_index}",
                                   'candidate_kind': 'named_table_row' if named else 'tier_table_row',
                                   'name_en': name, 'tier_text': row[0] if tiered else None,
                                   'context_headings': table['context_headings'],
                                   'evidence': ' | '.join(row), 'table_index': table['table_index'],
                                   'row_index': row_index, 'column_headers': headers,
                                   'row_values': row})
        headings = soup.find_all(re.compile(r'^h[2-6]$')) if soup else []
        block_ids = {id(t) for t in self.blocks(soup)}
        context_stack = []
        for heading in headings:
            name = text(heading)
            level = int(heading.name[1])
            while context_stack and context_stack[-1][0] >= level:
                context_stack.pop()
            context_headings = [value for _, value in context_stack]
            context_stack.append((level, name))
            if not re.search(r'\b(?:scholarships?|awards?|bursar(?:y|ies)|fellowships?)\b', name, re.I):
                continue
            if re.search(r'^(?:how|conditions|eligibility|deadline|renewal|criteria|can my)\b|\?', name, re.I):
                continue
            parts = []
            for node in heading.next_elements:
                if getattr(node, 'name', None) and re.fullmatch(r'h[1-6]', node.name) and int(node.name[1]) <= level:
                    break
                if id(node) in block_ids:
                    parts.append(text(node))
            if not parts:
                continue
            fragment = BeautifulSoup('<section></section>', 'html.parser')
            for part in parts:
                p = fragment.new_tag('p')
                p.string = part
                fragment.section.append(p)
            is_group = bool(re.search(r'\b(?:scholarships|awards|bursaries)\b', name, re.I))
            candidates.append({'candidate_id': f'heading-{len(candidates)}', 'name_en': name,
                               'candidate_kind': 'section_group' if is_group else 'heading_award',
                               'context_headings': context_headings,
                               'evidence': parts,
                               'eligibility_evidence': self.extract_eligibility(fragment)})
        return candidates

    def parse_html(self, soup):
        if soup is None:
            return {'error': 'No validated HTML available', 'scholarship_candidates': []}
        root = self.content(soup)
        if not re.search(r'scholarship|award|bursar|financial aid', text(root), re.I):
            return {'error': 'No scholarship content in the main document', 'scholarship_candidates': []}
        tables = self.extract_tables(root)
        positive, negative = self.renewal_evidence(root)
        return {'page_title': self.extract_title(soup), 'main_heading': self.extract_h1(root),
                'tables_data': tables,
                'renewal_evidence': {'positive': positive, 'negative': negative},
                'scholarship_candidates': self.scholarship_candidates(root, tables)}


# Normalization: named awards, tiers, schedules and costs remain separate.
def normalized_entry(candidate, slug, ref):
    name, evidence = compact(candidate.get('name_en') or ''), lines(candidate)
    context = candidate.get('context_headings', [])
    row = columns(candidate)
    applicant, international_eligible = category(name, context, evidence, row)
    description = first_column(row, r'^description$')
    criteria = first_column(row, r'^criteria$')
    value_text = first_column(row, r'^value$|^amount$|scholarship total')
    value_lines = [value_text] if value_text else [s for s in evidence if re.match(r'Value of award\s*:', s, re.I)]
    if not value_lines and not row:
        value_lines = [s for s in evidence if re.fullmatch(r'\$[^a-z]*.*entrance scholarship', s, re.I)
                       or re.search(r'one-time.*scholarship valued at', s, re.I)]
    values = []
    for line in value_lines:
        values.extend(money_values(line, currency=explicit_currency(line)))
    criteria_texts = [v for v in (description, criteria) if v] or candidate.get('eligibility_evidence', [])
    issue_codes = ['requires_human_review']
    if not values:
        issue_codes.append('award_value_not_structured')
    elif any(v['currency'] is None for v in values):
        issue_codes.append('currency_not_explicit')
    if any(v['payment_basis'] == 'unknown' for v in values):
        issue_codes.append('payment_basis_not_explicit')
    if any(re.search(r'12 instalments', s, re.I) for s in evidence) and len(values) > 1:
        issue_codes.append('payment_schedule_requires_terms_review')
    award_count = None
    unlimited = None
    for line in evidence:
        match = re.match(r'Number of awards:\s*(\d+|Unlimited)', line, re.I)
        if match:
            unlimited = match[1].lower() == 'unlimited'
            award_count = None if unlimited else int(match[1])
    level = next((s.split(':', 1)[1].strip() for s in evidence if s.startswith('Level or program of study:')), None)
    return {
        'id': stable_id('award', [slug, name, context, evidence]), 'name': name,
        'support_type': 'bursary' if re.search(r'bursary', name, re.I) else
                        'scholarship' if re.search(r'scholarship', name, re.I) else 'award',
        'context': {'headings': context, 'applicant_category': applicant, 'study_level': level,
                    'intake_texts': distinct([s for s in context + evidence if re.search(r'\b(?:20\d\d[-–]20\d\d|starting|newly admitted)\b', s, re.I)])},
        'eligibility': {'international_eligible': international_eligible,
                        'programs_text': first_column(row, r'eligible programs|^programs$'),
                        'criteria_texts': criteria_texts,
                        'campus_text': first_column(row, r'^campus$'),
                        'term_text': first_column(row, r'^term$')},
        'benefit': {'display_texts': value_lines, 'values': distinct(values),
                    'award_count': award_count, 'unlimited_awards': unlimited},
        'renewal': renewal(evidence), 'application': application(evidence, row),
        'verification': {'status': 'needs_review', 'publishable': False, 'issues': issue_codes},
        'evidence': {'texts': evidence, 'refs': [ref]},
    }


def table_headers(table):
    if table.get('headers'):
        return table['headers'], table['rows'], 0
    rows = table.get('rows', [])
    if rows and any(re.search(r'application (?:available|opens|closes)|deadline date', s, re.I) for s in rows[0]):
        return rows[0], rows[1:], 1
    return [], rows, 0


def application_windows(tables, file):
    windows = []
    for table_pos, table in enumerate(tables):
        headers, rows, offset = table_headers(table)
        opening = next((i for i, h in enumerate(headers) if re.search(r'application available|application opens|^open$', h, re.I)), None)
        closing = next((i for i, h in enumerate(headers) if re.search(r'deadline date|application closes|close/deadline', h, re.I)), None)
        if opening is None or closing is None:
            continue
        label_index = next((i for i, h in enumerate(headers) if re.search(r'^semester$|^ceremony$|^type of award$|^term$', h, re.I)), None)
        result_index = next((i for i, h in enumerate(headers) if re.search(r'results available|notified of award', h, re.I)), None)
        for position, row in enumerate(rows):
            if max(opening, closing) >= len(row):
                continue
            windows.append({'group': table.get('heading'), 'label': row[label_index] if label_index is not None else None,
                            'opens': date_value(row[opening]), 'deadline': date_value(row[closing]),
                            'results_text': row[result_index] if result_index is not None and result_index < len(row) else None,
                            'evidence_ref': source_ref(file, f'/extracted_data/tables_data/{table_pos}/rows/{position + offset}')})
    return windows


def tier_groups(record, file, policy=None):
    data, slug = record['extracted_data'], record['slug']
    groups, covered = [], set()
    for pos, table in enumerate(data.get('tables_data', [])):
        headers = table.get('headers', [])
        if not headers or not re.search(r'average|grade', headers[0], re.I):
            continue
        value_index = next((i for i, h in enumerate(headers) if re.search(r'amount|value|scholarship total', h, re.I)), None)
        if value_index is None:
            continue
        name = compact(table.get('heading') or data.get('main_heading') or '')
        group = {'id': stable_id('group', [slug, name, headers]), 'name': name,
                 'kind': 'tiered_award', 'context_headings': table.get('context_headings', []),
                 'tiers': [], 'verification': {'status': 'needs_review', 'publishable': False},
                 'evidence_refs': [source_ref(file, f'/extracted_data/tables_data/{pos}')]}
        for row_pos, row in enumerate(table['rows']):
            if len(row) <= value_index:
                continue
            value_text = row[value_index]
            criteria = [grade(row[0])]
            ib_index = next((i for i, h in enumerate(headers) if re.search(r'^IB average', h, re.I)), None)
            if ib_index is not None and len(row) > ib_index:
                criteria.append(grade(row[ib_index], 'international_baccalaureate'))
            evidence = [' | '.join(row)]
            footnote_refs = []
            if policy is not None:
                statements, footnote_refs = policy.renewal_footnotes(data, value_text, file)
                evidence.extend(statements)
            currency = explicit_currency(' '.join(headers) + ' ' + value_text)
            group['tiers'].append({'id': stable_id('tier', [slug, name, row]), 'criteria': criteria,
                                   'value_text': value_text, 'values': money_values(value_text, headers[value_index], currency),
                                   'renewal': renewal(evidence),
                                   'availability_text': next((row[i] for i, h in enumerate(headers) if re.search(r'scholarships available', h, re.I) and i < len(row)), None),
                                   'evidence_refs': [source_ref(file, f'/extracted_data/tables_data/{pos}/rows/{row_pos}')] + footnote_refs})
            covered.add((table['table_index'], row_pos))
        groups.append(group)
    return groups, covered


def normalize_school(record, file, file_hash=None, policy=None):
    meta, data, slug = record['crawl_metadata'], record['extracted_data'], record['slug']
    result = {'school': {'slug': slug, 'name': record['school_name']},
              'crawl': {'success': record['success'], 'status': meta.get('fetch_status'),
                        'http_status': meta.get('http_status'), 'error': data.get('error')},
              'source': {'page_url': record['source_url'], 'final_url': meta.get('final_url'),
                         'captured_at': meta.get('fetched_at'), 'attempted_at': meta.get('attempted_at'),
                         'html_sha256': meta.get('sha256'), 'json_file': file, 'json_sha256': file_hash},
              'scholarships': [], 'scholarship_groups': [], 'application_windows': [],
              'unresolved_sections': [], 'source_tables': [], 'cost_breakdowns': []}
    if not record['success']:
        return result
    groups, covered = tier_groups(record, file, policy)
    result['scholarship_groups'] = list(groups)
    result['application_windows'] = application_windows(data.get('tables_data', []), file)
    grouped_names = {key(g['name']) for g in groups}
    known_names = {compact(c.get('name_en') or '') for c in data.get('scholarship_candidates', [])}
    for index, candidate in enumerate(data.get('scholarship_candidates', [])):
        ref = source_ref(file, f'/extracted_data/scholarship_candidates/{index}')
        name, kind = compact(candidate.get('name_en') or ''), candidate.get('candidate_kind')
        reason = None
        if kind == 'tier_table_row' and (candidate.get('table_index'), candidate.get('row_index')) in covered:
            continue
        if key(name) in grouped_names:
            reason = 'represented_by_tier_group'
        elif ADMIN.search(name):
            reason = 'administrative_or_application_content'
        elif kind == 'section_group' and not (policy is not None and policy.keep_section(candidate)):
            reason = 'section_heading_is_not_an_individual_award'
        elif policy is not None and policy.candidate_issue(candidate):
            reason = policy.candidate_issue(candidate)
        elif kind == 'heading_award' and not any(
                s not in known_names and (MONEY.search(s) or len(s) > 80) for s in lines(candidate)):
            reason = 'insufficient_award_specific_evidence'
        if reason:
            result['unresolved_sections'].append({'name': name, 'reason': reason, 'evidence_ref': ref})
            continue
        if 'series' in name.lower() or kind == 'section_group':
            entry = normalized_entry(candidate, slug, ref)
            result['scholarship_groups'].append({'id': entry['id'], 'name': name, 'kind': 'section_group' if kind == 'section_group' else 'award_series',
                                                 'tiers': [], 'details': entry,
                                                 'verification': {'status': 'needs_review', 'publishable': False}})
        else:
            result['scholarships'].append(normalized_entry(candidate, slug, ref))
    represented_tables = {int(g['evidence_refs'][0]['json_pointer'].split('/')[-1]) for g in groups}
    for pos, table in enumerate(data.get('tables_data', [])):
        if pos in represented_tables:
            continue
        contents = ' '.join(' '.join(row) for row in table.get('rows', []))
        classification = ('cost_breakdown' if re.search(r'total tuition|less:.*scholarship', contents, re.I)
                          else 'application_schedule' if any(w['evidence_ref']['json_pointer'].startswith(f'/extracted_data/tables_data/{pos}/') for w in result['application_windows'])
                          else 'award_catalogue' if table.get('headers') and re.search(r'scholarship|award name', table['headers'][0], re.I)
                          else 'unclassified')
        ref = source_ref(file, f'/extracted_data/tables_data/{pos}')
        result['source_tables'].append({'heading': table.get('heading'), 'classification': classification,
                                       'row_count': table.get('rows_count', 0), 'evidence_ref': ref})
        if classification == 'cost_breakdown':
            components = []
            for row in table.get('rows', []):
                label = row[0] if row else ''
                component_kind = 'tuition_total' if re.search(r'total tuition', label, re.I) else 'discount' if re.search(r'^less:', label, re.I) else 'unclassified_cost'
                components.append({'label': label or None, 'kind': component_kind,
                                   'dollar_tokens': [float(value.replace(',', '')) for value in MONEY.findall(' '.join(row))],
                                   'raw': row})
            result['cost_breakdowns'].append({'components': components, 'currency': explicit_currency(contents),
                                             'award_association': 'unresolved', 'evidence_ref': ref})
    # Merge only identical evidence records. Different variants of a name remain separate.
    unique = {}
    for entry in result['scholarships']:
        if entry['id'] in unique:
            unique[entry['id']]['evidence']['refs'].extend(entry['evidence']['refs'])
        else:
            unique[entry['id']] = entry
    result['scholarships'] = list(unique.values())
    return result



# Public pipeline. Each school overrides only the rules that differ.
class SchoolCrawler(PageParser):
    name = ''
    slug = ''
    url = ''

    def keep_section(self, candidate):
        return False

    def candidate_issue(self, candidate):
        return None

    def renewal_footnotes(self, data, value_text, file):
        return [], []

    def from_record(self, record, output_dir, input_hash=None):
        """Normalize one fetched page (also used once to migrate existing data)."""
        path = Path(output_dir) / f'{self.slug}.json'
        try:
            file = path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            file = str(path.resolve())
        normalized = normalize_school(record, file, input_hash, policy=self)
        data = record['extracted_data']
        candidates = data.get('scholarship_candidates', [])
        targets = {}
        # Named awards already contain their own source text: point there directly.
        def remember(entry, prefix):
            for ref in entry['evidence']['refs']:
                targets[ref['json_pointer']] = prefix + '/evidence/texts'
        for index, entry in enumerate(normalized['scholarships']):
            remember(entry, f'/scholarships/{index}')
        for index, group in enumerate(normalized['scholarship_groups']):
            if 'details' in group:
                remember(group['details'], f'/scholarship_groups/{index}/details')
        for index, section in enumerate(normalized['unresolved_sections']):
            pointer = section['evidence_ref']['json_pointer']
            section['texts'] = lines(candidates[int(pointer.rsplit('/', 1)[1])])
            targets[pointer] = f'/unresolved_sections/{index}/texts'
        normalized['evidence'] = {
            'tables': [{key: table.get(key) for key in ('heading', 'headers', 'rows', 'rows_count')}
                       for table in data.get('tables_data', [])],
            'renewal': data.get('renewal_evidence', {'positive': [], 'negative': []}),
        }
        def localize(value):
            if isinstance(value, dict):
                if 'json_pointer' in value:
                    pointer = value['json_pointer']
                    value['json_pointer'] = targets.get(pointer, pointer.replace(
                        '/extracted_data/tables_data', '/evidence/tables', 1).replace(
                        '/extracted_data/renewal_evidence', '/evidence/renewal', 1))
                for child in value.values():
                    localize(child)
            elif isinstance(value, list):
                for child in value:
                    localize(child)
        localize(normalized)
        source = normalized['source']
        source.pop('json_file', None)
        source.pop('json_sha256', None)
        source['output_file'] = file
        source['input_kind'] = 'legacy_json_import' if input_hash else 'live_http'
        if input_hash:
            source['input_json_sha256'] = input_hash
        normalized['crawl']['attempts'] = record['crawl_metadata'].get('attempts', [])
        groups = normalized['scholarship_groups']
        return {'schema_version': 3, 'generated_at': now(), **normalized,
                'summary': {'named_award_entries': len(normalized['scholarships']),
                            'award_groups': len(groups), 'tiers': sum(len(g['tiers']) for g in groups),
                            'application_windows': len(normalized['application_windows']),
                            'unresolved_sections': len(normalized['unresolved_sections']),
                            'verified_scholarships': 0, 'total_scholarships': None}}

    def run(self, output_dir=None, timeout=12):
        output_dir = Path(output_dir) if output_dir is not None else ROOT / 'outputs'
        metadata, soup = fetch_html(self.url, timeout)
        try:
            extracted = self.parse_html(soup)
            success = soup is not None and 'error' not in extracted
            if not success and metadata['fetch_status'] == 'ok':
                metadata['fetch_status'] = 'parse_error'
            record = {'school_name': self.name, 'slug': self.slug, 'source_url': self.url,
                      'success': success, 'crawl_metadata': metadata, 'extracted_data': extracted}
            document = self.from_record(record, output_dir)
        except Exception as exc:
            metadata['fetch_status'] = 'processing_error'
            record = {'school_name': self.name, 'slug': self.slug, 'source_url': self.url,
                      'success': False, 'crawl_metadata': metadata,
                      'extracted_data': {'error': f'{type(exc).__name__}: {exc}', 'scholarship_candidates': []}}
            document = self.from_record(record, output_dir)
        write_json(output_dir / f'{self.slug}.json', document)
        return document


def fetch_html(url, timeout=12):
    """HTTP status is independent of process success. Blocked pages yield no DOM."""
    metadata = {'requested_url': url, 'attempted_at': now(), 'attempts': [],
                'http_status': None, 'fetch_status': 'unavailable'}
    for client in ('requests', 'curl'):
        try:
            if client == 'requests':
                response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
                status, body, final_url = response.status_code, response.content, response.url
                content_type = response.headers.get('Content-Type', '')
            else:
                marker = b'\n__SCHOLARSHIP_HTTP_META__'
                response = subprocess.run([
                    'curl', '--silent', '--show-error', '--location', '--max-time', str(timeout),
                    '--proto', '=https', '--proto-redir', '=https', '-A', DEFAULT_HEADERS['User-Agent'],
                    '--write-out', '\n__SCHOLARSHIP_HTTP_META__%{http_code}\t%{url_effective}\t%{content_type}', url,
                ], capture_output=True, timeout=timeout + 2)
                if response.returncode:
                    raise OSError(f'curl exit {response.returncode}')
                body, trailer = response.stdout.rsplit(marker, 1)
                code, final_url, content_type = trailer.decode('utf-8').split('\t', 2)
                status = int(code)
            soup, error = PageParser.validate_html(status, body, content_type)
            metadata.update(http_status=status, final_url=final_url, fetch_status=error or 'ok')
            metadata['attempts'].append({'client': client, 'http_status': status, 'error': error, 'final_url': final_url})
            if soup is not None:
                metadata.update(fetched_at=now(), sha256=hashlib.sha256(body).hexdigest())
                return metadata, soup
        except (requests.RequestException, subprocess.TimeoutExpired, OSError, ValueError) as exc:
            metadata['attempts'].append({'client': client, 'error': str(exc)})
            metadata['fetch_status'] = 'network_error'
    return metadata, None


def write_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and json.loads(path.read_text(encoding='utf-8')).get('schema_version') != 3:
        raise ValueError(f'{path}: refusing to overwrite an unrelated/legacy JSON')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as handle:
            temporary = handle.name
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)


def run_school(crawler):
    """Allow python schools/<school>.py using the same runner and flags."""
    from run_all import main
    import sys
    return main(['--school', crawler.slug, *sys.argv[1:]])
