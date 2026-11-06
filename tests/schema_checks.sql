\set ON_ERROR_STOP on
INSERT INTO schools(name_en, slug) VALUES ('School A','a'), ('School B','b');
INSERT INTO programs(school_id,name_en) VALUES (1,'A1'), (1,'A2'), (2,'B1');
INSERT INTO scholarships(school_id,external_key,intake_key,name_en,source_url,evidence_json)
VALUES (1,'award','2026','Award A','https://a.test/scholarships','{"text":"source"}');

DO $$ BEGIN
    IF to_regclass('source_captures') IS NOT NULL THEN RAISE EXCEPTION 'removed source table still exists'; END IF;
    IF (SELECT source_fetched_at IS NOT NULL FROM scholarships WHERE id=1) THEN RAISE EXCEPTION 'unknown source time was invented'; END IF;
    IF (SELECT is_renewable IS NOT NULL OR program_scope <> 'unknown' OR published FROM scholarships WHERE id=1)
    THEN RAISE EXCEPTION 'unknown defaults lost'; END IF;
    BEGIN
        UPDATE scholarships SET published=TRUE WHERE id=1;
        RAISE EXCEPTION 'unverified publication accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        INSERT INTO scholarships(school_id,external_key,intake_key,name_en,source_url,evidence_json)
        VALUES (1,'empty-source','2026','A','   ','{"text":"source"}');
        RAISE EXCEPTION 'empty source URL accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        INSERT INTO scholarship_programs VALUES (1,3,1);
        RAISE EXCEPTION 'cross-school program accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL; END;
    BEGIN
        INSERT INTO scholarship_tiers(scholarship_id,tier_key,eligibility_text,value_kind,min_value,max_value,currency,value_display_text,evidence_text)
        VALUES (1,'bad','criteria','money',200,100,'CAD','$100','evidence');
        RAISE EXCEPTION 'inverted amount range accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        INSERT INTO scholarship_tiers(scholarship_id,tier_key,eligibility_text,value_kind,min_value,currency,value_display_text,evidence_text)
        VALUES (1,'bad','criteria','money',-1,'CAD','-$1','evidence');
        RAISE EXCEPTION 'negative amount accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        INSERT INTO scholarship_tiers(scholarship_id,tier_key,eligibility_text,value_kind,min_value,max_value,value_display_text,evidence_text)
        VALUES (1,'bad-percent','criteria','tuition_percentage',101,110,'110%','evidence');
        RAISE EXCEPTION 'percentage without valid rate/range accepted';
    EXCEPTION WHEN check_violation THEN NULL; END;
    BEGIN
        INSERT INTO scholarships(school_id,external_key,intake_key,name_en,source_url,evidence_json)
        VALUES (1,'award','2026','duplicate','https://a.test/scholarships','{"text":"source"}');
        RAISE EXCEPTION 'duplicate intake accepted';
    EXCEPTION WHEN unique_violation THEN NULL; END;
END $$;

UPDATE scholarships SET program_scope='school_wide',verification_status='verified',reviewed_by='test',reviewed_at=now(),published=TRUE WHERE id=1;
INSERT INTO scholarship_programs VALUES (1,1,1), (1,2,1);
INSERT INTO scholarship_tiers(scholarship_id,tier_key,eligibility_text,value_kind,min_value,max_value,currency,payment_basis,value_display_text,evidence_text)
VALUES (1,'cad','criteria','money',100,200,'CAD','per_year','$100-200/year','source');
INSERT INTO scholarship_tiers(scholarship_id,tier_key,eligibility_text,value_kind,tuition_rate_basis,value_display_text,evidence_text)
VALUES (1,'waiver','criteria','tuition_waiver','domestic','Domestic tuition waiver','source');

DO $$ DECLARE result_count INTEGER; old_stamp TIMESTAMPTZ; BEGIN
    SELECT count(*) INTO result_count FROM scholarships s
    WHERE s.school_id=1 AND s.published
      AND (s.valid_from IS NULL OR s.valid_from <= CURRENT_DATE)
      AND (s.valid_until IS NULL OR s.valid_until >= CURRENT_DATE)
      AND EXISTS (SELECT 1 FROM programs p WHERE p.id=1 AND p.school_id=s.school_id)
      AND (s.program_scope='school_wide' OR (s.program_scope='selected_programs' AND EXISTS (
        SELECT 1 FROM scholarship_programs sp WHERE sp.scholarship_id=s.id AND sp.program_id=1)));
    IF result_count <> 1 THEN RAISE EXCEPTION 'query duplicated or omitted result'; END IF;
    SELECT updated_at INTO old_stamp FROM scholarships WHERE id=1;
    PERFORM pg_sleep(0.01);
    UPDATE scholarships SET name_en='Updated' WHERE id=1;
    IF (SELECT updated_at <= old_stamp FROM scholarships WHERE id=1)
    THEN RAISE EXCEPTION 'updated_at did not change'; END IF;
END $$;
SELECT 'schema checks passed' AS result;
