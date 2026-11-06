-- PostgreSQL 16+. Standalone reference schema; adapt schools/programs to the portal
-- before applying to an existing database. No automatic ingestion of crawler candidates.
BEGIN;

CREATE TABLE schools (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name_en TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE
);
CREATE TABLE programs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES schools(id),
    name_en TEXT NOT NULL,
    UNIQUE (id, school_id)
);
-- One offering for a named award and intake/version; never a whole school page.
CREATE TABLE scholarships (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    school_id BIGINT NOT NULL REFERENCES schools(id),
    external_key TEXT NOT NULL,
    intake_key TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_vi TEXT,
    source_url TEXT NOT NULL CHECK (length(trim(source_url)) > 0),
    source_fetched_at TIMESTAMPTZ, -- NULL when the collection time is unknown.
    is_renewable BOOLEAN, -- NULL means unknown; never defaults to FALSE.
    duration_note_en TEXT,
    duration_note_vi TEXT,
    program_scope TEXT NOT NULL DEFAULT 'unknown'
        CHECK (program_scope IN ('unknown', 'school_wide', 'selected_programs')),
    applicant_category TEXT NOT NULL DEFAULT 'unknown'
        CHECK (applicant_category IN ('unknown', 'domestic', 'international', 'both')),
    study_level TEXT,
    eligibility_criteria TEXT,
    application_method TEXT NOT NULL DEFAULT 'unknown'
        CHECK (application_method IN ('unknown', 'automatic', 'application_required', 'nomination')),
    deadline_text TEXT,
    deadline_at TIMESTAMPTZ,
    valid_from DATE,
    valid_until DATE,
    evidence_json JSONB NOT NULL CHECK (jsonb_typeof(evidence_json) = 'object' AND evidence_json <> '{}'::jsonb),
    raw_tables_json JSONB,
    verification_status TEXT NOT NULL DEFAULT 'needs_review'
        CHECK (verification_status IN ('needs_review', 'verified', 'rejected')),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (school_id, external_key, intake_key),
    UNIQUE (id, school_id),
    CHECK (valid_from IS NULL OR valid_until IS NULL OR valid_from <= valid_until),
    CHECK (verification_status <> 'verified' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)),
    CHECK (NOT published OR (verification_status = 'verified' AND program_scope <> 'unknown'))
);
-- Tier values have an explicit basis. Never compare a per-term value with a
-- full-degree value. Percentage/free-tuition benefits need a rate basis as well.
CREATE TABLE scholarship_tiers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scholarship_id BIGINT NOT NULL REFERENCES scholarships(id) ON DELETE CASCADE,
    tier_key TEXT NOT NULL,
    eligibility_text TEXT NOT NULL,
    is_renewable BOOLEAN,
    renewal_conditions TEXT,
    value_kind TEXT NOT NULL CHECK (value_kind IN ('money', 'tuition_percentage', 'tuition_waiver', 'unknown')),
    min_value NUMERIC(14,2),
    max_value NUMERIC(14,2),
    currency CHAR(3) CHECK (currency ~ '^[A-Z]{3}$'),
    payment_basis TEXT NOT NULL DEFAULT 'unknown'
        CHECK (payment_basis IN ('unknown', 'one_time', 'per_term', 'per_year', 'total_degree')),
    max_instalments INTEGER CHECK (max_instalments > 0),
    tuition_rate_basis TEXT CHECK (tuition_rate_basis IN ('domestic', 'international', 'unknown')),
    value_display_text TEXT NOT NULL,
    evidence_text TEXT NOT NULL CHECK (length(trim(evidence_text)) > 0),
    UNIQUE (scholarship_id, tier_key),
    CHECK (min_value IS NULL OR min_value >= 0),
    CHECK (max_value IS NULL OR max_value >= 0),
    CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value),
    CHECK (value_kind <> 'money' OR currency IS NOT NULL),
    CHECK (value_kind <> 'tuition_percentage' OR
        (min_value IS NOT NULL AND max_value IS NOT NULL AND max_value <= 100)),
    CHECK (value_kind NOT IN ('tuition_percentage', 'tuition_waiver') OR tuition_rate_basis IS NOT NULL),
    CHECK (value_kind <> 'tuition_waiver' OR (min_value IS NULL AND max_value IS NULL))
);
-- school_id is carried to enforce both endpoints belonging to the same school.
CREATE TABLE scholarship_programs (
    scholarship_id BIGINT NOT NULL,
    program_id BIGINT NOT NULL,
    school_id BIGINT NOT NULL,
    PRIMARY KEY (scholarship_id, program_id),
    FOREIGN KEY (scholarship_id, school_id) REFERENCES scholarships(id, school_id) ON DELETE CASCADE,
    FOREIGN KEY (program_id, school_id) REFERENCES programs(id, school_id) ON DELETE CASCADE
);
CREATE INDEX idx_scholarships_school_published ON scholarships(school_id) WHERE published;
CREATE INDEX idx_scholarship_programs_program ON scholarship_programs(program_id);
CREATE INDEX idx_tiers_scholarship ON scholarship_tiers(scholarship_id);

CREATE FUNCTION touch_scholarship_updated_at() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END;
$$;
CREATE TRIGGER scholarships_updated_at BEFORE UPDATE ON scholarships
    FOR EACH ROW EXECUTE FUNCTION touch_scholarship_updated_at();
COMMIT;

-- Example query (bind :school_id / :program_id in the application):
-- SELECT s.* FROM scholarships s
-- WHERE s.school_id = :school_id AND s.published
--   AND (s.valid_from IS NULL OR s.valid_from <= CURRENT_DATE)
--   AND (s.valid_until IS NULL OR s.valid_until >= CURRENT_DATE)
--   AND EXISTS (SELECT 1 FROM programs p WHERE p.id = :program_id AND p.school_id = s.school_id)
--   AND (s.program_scope = 'school_wide'
--        OR (s.program_scope = 'selected_programs' AND EXISTS (
--            SELECT 1 FROM scholarship_programs sp
--            WHERE sp.scholarship_id = s.id AND sp.program_id = :program_id)));
-- Also filter applicant eligibility/intake/level; being visible is not proof of eligibility.
