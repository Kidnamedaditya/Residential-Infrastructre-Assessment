-- ═══════════════════════════════════════════════════════════════
-- DATABASE SCHEMA
-- ═══════════════════════════════════════════════════════════════

CREATE OR REPLACE DATABASE INSPECTION_DB;
USE DATABASE INSPECTION_DB;
CREATE OR REPLACE SCHEMA PUBLIC;

-- 1. USERS table
CREATE OR REPLACE TABLE USERS (
    user_id VARCHAR PRIMARY KEY,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    user_type VARCHAR, -- 'normal_user' or 'inspector'
    full_name VARCHAR,
    phone VARCHAR,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    last_login TIMESTAMP
);

-- 2. INSPECTOR_PROFILES table
CREATE OR REPLACE TABLE INSPECTOR_PROFILES (
    inspector_id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES USERS(user_id),
    license_number VARCHAR,
    certifications ARRAY,
    specialization ARRAY, -- structural, electrical, plumbing, etc.
    years_experience INT,
    rating DECIMAL(2, 1),
    total_inspections INT DEFAULT 0,
    verified_inspector BOOLEAN DEFAULT FALSE
);

-- 3. PROPERTIES table
CREATE OR REPLACE TABLE PROPERTIES (
    property_id VARCHAR PRIMARY KEY,
    house_number VARCHAR,
    property_name VARCHAR,
    address VARCHAR,
    property_type VARCHAR, -- apartment/villa/commercial
    construction_status VARCHAR, -- newly_built/under_construction/existing
    total_rooms INT,
    owner_user_id VARCHAR REFERENCES USERS(user_id),
    report_visibility VARCHAR DEFAULT 'private', -- private/public/shared_link
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Index for search
-- Note: Snowflake automatically manages micro-partitions, but clustering keys can be added if needed for large datasets.
-- ALTER TABLE PROPERTIES CLUSTER BY (house_number);

-- 4. ROOMS table
CREATE OR REPLACE TABLE ROOMS (
    room_id VARCHAR PRIMARY KEY,
    property_id VARCHAR REFERENCES PROPERTIES(property_id),
    room_name VARCHAR,
    room_type VARCHAR, -- bedroom/kitchen/bathroom/living_room/utility
    area_sqft DECIMAL(10, 2),
    floor_number INT
);

-- 5. INSPECTION_FINDINGS table
CREATE OR REPLACE TABLE INSPECTION_FINDINGS (
    finding_id VARCHAR PRIMARY KEY,
    room_id VARCHAR REFERENCES ROOMS(room_id),
    property_id VARCHAR REFERENCES PROPERTIES(property_id),
    finding_category VARCHAR, -- structural/electrical/moisture/plumbing/finishing
    finding_description TEXT,
    severity VARCHAR, -- critical/high/medium/low/ok
    inspector_notes TEXT,
    detected_by VARCHAR, -- 'ai' or 'inspector' or 'user'
    confidence_score DECIMAL(4, 3), -- 0-1
    finding_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- 6. INSPECTION_IMAGES table
CREATE OR REPLACE TABLE INSPECTION_IMAGES (
    image_id VARCHAR PRIMARY KEY,
    upload_session_id VARCHAR,
    user_id VARCHAR REFERENCES USERS(user_id),
    property_id VARCHAR REFERENCES PROPERTIES(property_id),
    room_id VARCHAR REFERENCES ROOMS(room_id),
    upload_scenario VARCHAR, -- single_wall/room_set/full_property
    image_url VARCHAR, -- S3/Azure path
    original_filename VARCHAR,
    ai_detected_defects ARRAY,
    ai_confidence_score DECIMAL(4, 3),
    ai_description TEXT,
    ai_severity VARCHAR,
    inspector_verified BOOLEAN DEFAULT FALSE,
    inspector_override_notes TEXT,
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- 7. UPLOAD_SESSIONS table
CREATE OR REPLACE TABLE UPLOAD_SESSIONS (
    session_id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES USERS(user_id),
    property_id VARCHAR REFERENCES PROPERTIES(property_id),
    upload_scenario VARCHAR, -- single_wall/room_set/full_property
    total_images INT,
    status VARCHAR, -- in_progress/completed/processing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    completed_at TIMESTAMP
);

-- 8. INSPECTOR_REPORTS table
CREATE OR REPLACE TABLE INSPECTOR_REPORTS (
    report_id VARCHAR PRIMARY KEY,
    property_id VARCHAR REFERENCES PROPERTIES(property_id),
    inspector_id VARCHAR REFERENCES INSPECTOR_PROFILES(inspector_id),
    inspection_date DATE,
    manual_risk_score DECIMAL(5, 2), -- 0-100
    ai_risk_score DECIMAL(5, 2), -- 0-100
    score_variance DECIMAL(5, 2),
    agreement_percentage DECIMAL(5, 2),
    final_approved_score DECIMAL(5, 2),
    inspector_summary TEXT,
    status VARCHAR DEFAULT 'draft' -- draft/submitted/approved/disputed
);

-- 9. REPORT_ACCESS table
CREATE OR REPLACE TABLE REPORT_ACCESS (
    access_id VARCHAR PRIMARY KEY,
    property_id VARCHAR REFERENCES PROPERTIES(property_id),
    user_id VARCHAR REFERENCES USERS(user_id),
    access_level VARCHAR, -- view/edit/full
    access_token VARCHAR, -- for shareable links
    granted_by VARCHAR REFERENCES USERS(user_id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    expires_at TIMESTAMP
);

-- 10. DEFECT_CLASSIFICATION_RULES table
CREATE OR REPLACE TABLE DEFECT_CLASSIFICATION_RULES (
    rule_id INT PRIMARY KEY,
    defect_keyword VARCHAR, -- crack, damp, leak, exposed_wiring, etc.
    defect_category VARCHAR, -- structural/electrical/moisture/plumbing/finishing
    severity_level VARCHAR, -- critical/high/medium/low
    risk_weight DECIMAL(3, 2), -- 0-1 for scoring
    description TEXT
);

-- 11. INSPECTION_ALERTS table
CREATE OR REPLACE TABLE INSPECTION_ALERTS (
    alert_id VARCHAR PRIMARY KEY,
    property_id VARCHAR REFERENCES PROPERTIES(property_id),
    room_id VARCHAR REFERENCES ROOMS(room_id),
    finding_id VARCHAR REFERENCES INSPECTION_FINDINGS(finding_id),
    alert_type VARCHAR, -- critical_finding/high_risk_property/electrical_hazard
    alert_severity VARCHAR, -- critical/high/medium
    alert_message TEXT,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR REFERENCES USERS(user_id),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- ═══════════════════════════════════════════════════════════════
-- RISK SCORING ALGORITHMS (VIEWS)
-- ═══════════════════════════════════════════════════════════════

-- ROOM-LEVEL RISK SCORE (0-100)
CREATE OR REPLACE VIEW ROOM_RISK_SCORES AS
SELECT 
    r.room_id,
    r.property_id,
    r.room_name,
    r.room_type,
    
    -- Count defects by severity
    COUNT(CASE WHEN f.severity = 'critical' THEN 1 END) AS critical_count,
    COUNT(CASE WHEN f.severity = 'high' THEN 1 END) AS high_count,
    COUNT(CASE WHEN f.severity = 'medium' THEN 1 END) AS medium_count,
    COUNT(CASE WHEN f.severity = 'low' THEN 1 END) AS low_count,
    
    -- Calculate weighted risk score
    LEAST(100, 
        (COUNT(CASE WHEN f.severity = 'critical' THEN 1 END) * 40) +
        (COUNT(CASE WHEN f.severity = 'high' THEN 1 END) * 25) +
        (COUNT(CASE WHEN f.severity = 'medium' THEN 1 END) * 15) +
        (COUNT(CASE WHEN f.severity = 'low' THEN 1 END) * 5)
    ) AS risk_score,
    
    -- Risk category
    CASE 
        WHEN COUNT(CASE WHEN f.severity = 'critical' THEN 1 END) > 0 THEN 'CRITICAL'
        WHEN LEAST(100, 
            (COUNT(CASE WHEN f.severity = 'critical' THEN 1 END) * 40) +
            (COUNT(CASE WHEN f.severity = 'high' THEN 1 END) * 25) +
            (COUNT(CASE WHEN f.severity = 'medium' THEN 1 END) * 15) +
            (COUNT(CASE WHEN f.severity = 'low' THEN 1 END) * 5)
        ) >= 60 THEN 'HIGH RISK'
        WHEN LEAST(100, 
            (COUNT(CASE WHEN f.severity = 'critical' THEN 1 END) * 40) +
            (COUNT(CASE WHEN f.severity = 'high' THEN 1 END) * 25) +
            (COUNT(CASE WHEN f.severity = 'medium' THEN 1 END) * 15) +
            (COUNT(CASE WHEN f.severity = 'low' THEN 1 END) * 5)
        ) >= 30 THEN 'MEDIUM RISK'
        WHEN COUNT(f.finding_id) > 0 THEN 'LOW RISK'
        ELSE 'NO ISSUES'
    END AS risk_category

FROM ROOMS r
LEFT JOIN INSPECTION_FINDINGS f ON r.room_id = f.room_id
GROUP BY r.room_id, r.property_id, r.room_name, r.room_type;


-- PROPERTY-LEVEL RISK SCORE (0-100)
CREATE OR REPLACE VIEW PROPERTY_RISK_SCORES AS
SELECT 
    p.property_id,
    p.property_name,
    p.address,
    
    -- Aggregate findings
    COUNT(DISTINCT f.finding_id) AS total_findings,
    COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) AS critical_findings,
    COUNT(DISTINCT CASE WHEN f.severity = 'high' THEN f.finding_id END) AS high_findings,
    COUNT(DISTINCT CASE WHEN f.severity = 'medium' THEN f.finding_id END) AS medium_findings,
    COUNT(DISTINCT CASE WHEN f.severity = 'low' THEN f.finding_id END) AS low_findings,
    
    -- Count high-risk rooms
    COUNT(DISTINCT CASE WHEN f.severity IN ('critical','high') THEN r.room_id END) AS high_risk_rooms,
    
    -- Calculate property risk score
    LEAST(100,
        (COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) * 35) +
        (COUNT(DISTINCT CASE WHEN f.severity = 'high' THEN f.finding_id END) * 20) +
        (COUNT(DISTINCT CASE WHEN f.severity = 'medium' THEN f.finding_id END) * 10) +
        (COUNT(DISTINCT CASE WHEN f.severity = 'low' THEN f.finding_id END) * 3) +
        (COUNT(DISTINCT CASE WHEN f.severity IN ('critical','high') THEN r.room_id END) * 5)
    ) AS property_risk_score,
    
    -- Risk rating
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) >= 2 
            THEN 'CRITICAL - Do Not Occupy'
        WHEN COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) >= 1 
            THEN 'CRITICAL - Immediate Action Required'
        WHEN LEAST(100,
            (COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) * 35) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'high' THEN f.finding_id END) * 20) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'medium' THEN f.finding_id END) * 10) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'low' THEN f.finding_id END) * 3) +
            (COUNT(DISTINCT CASE WHEN f.severity IN ('critical','high') THEN r.room_id END) * 5)
        ) >= 70 THEN 'HIGH RISK - Major Issues'
        WHEN LEAST(100,
            (COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) * 35) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'high' THEN f.finding_id END) * 20) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'medium' THEN f.finding_id END) * 10) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'low' THEN f.finding_id END) * 3) +
            (COUNT(DISTINCT CASE WHEN f.severity IN ('critical','high') THEN r.room_id END) * 5)
        ) >= 40 THEN 'MEDIUM RISK - Multiple Issues'
        WHEN COUNT(DISTINCT f.finding_id) > 0 THEN 'LOW RISK - Minor Issues'
        ELSE 'EXCELLENT - No Issues'
    END AS risk_rating,
    
    -- Recommendation
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) >= 2 THEN 'Reject property - Multiple critical safety issues'
        WHEN COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) >= 1 THEN 'Request immediate repairs before occupancy'
        WHEN LEAST(100,
            (COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) * 35) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'high' THEN f.finding_id END) * 20) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'medium' THEN f.finding_id END) * 10) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'low' THEN f.finding_id END) * 3) +
            (COUNT(DISTINCT CASE WHEN f.severity IN ('critical','high') THEN r.room_id END) * 5)
         ) >= 70 THEN 'Negotiate 15-25% price reduction'
        WHEN LEAST(100,
            (COUNT(DISTINCT CASE WHEN f.severity = 'critical' THEN f.finding_id END) * 35) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'high' THEN f.finding_id END) * 20) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'medium' THEN f.finding_id END) * 10) +
            (COUNT(DISTINCT CASE WHEN f.severity = 'low' THEN f.finding_id END) * 3) +
            (COUNT(DISTINCT CASE WHEN f.severity IN ('critical','high') THEN r.room_id END) * 5)
         ) >= 40 THEN 'Request repairs within 30 days'
        WHEN COUNT(DISTINCT f.finding_id) > 0 THEN 'Minor issues - acceptable with maintenance plan'
        ELSE 'Property cleared for occupancy'
    END AS recommendation

FROM PROPERTIES p
LEFT JOIN ROOMS r ON p.property_id = r.property_id
LEFT JOIN INSPECTION_FINDINGS f ON r.room_id = f.room_id
GROUP BY p.property_id, p.property_name, p.address;

-- ═══════════════════════════════════════════════════════════════
-- AI INTEGRATION VIEWS
-- ═══════════════════════════════════════════════════════════════

-- 1. TEXT CLASSIFICATION (using Snowflake Cortex)
CREATE OR REPLACE VIEW AI_CLASSIFIED_DEFECTS AS
SELECT 
    f.finding_id,
    f.property_id,
    r.room_name,
    f.finding_description,
    f.severity AS original_severity,
    f.confidence_score,
    
    -- AI classification
    SNOWFLAKE.CORTEX.CLASSIFY_TEXT(
        f.finding_description || '. ' || COALESCE(f.inspector_notes, ''),
        ['critical', 'high', 'medium', 'low', 'ok']
    ) AS ai_predicted_severity,
    
    -- Sentiment analysis
    SNOWFLAKE.CORTEX.SENTIMENT(
        f.finding_description || '. ' || COALESCE(f.inspector_notes, '')
    ) AS urgency_score,
    
    -- Generate summary
    SNOWFLAKE.CORTEX.SUMMARIZE(
        f.finding_description || '. ' || COALESCE(f.inspector_notes, '')
    ) AS defect_summary

FROM INSPECTION_FINDINGS f
LEFT JOIN ROOMS r ON f.room_id = r.room_id;


-- 2. PLAIN-LANGUAGE REPORT GENERATION
CREATE OR REPLACE VIEW PROPERTY_INSPECTION_SUMMARY AS
SELECT 
    p.property_id,
    p.property_name,
    prs.property_risk_score,
    prs.risk_rating,
    
    -- Generate executive summary
    CASE 
        WHEN prs.critical_findings >= 2 THEN
            '⛔ CRITICAL ALERT: Property has ' || prs.critical_findings || 
            ' critical safety hazards detected across ' || prs.high_risk_rooms || 
            ' rooms. DO NOT OCCUPY until all critical issues are resolved.'
        
        WHEN prs.critical_findings = 1 THEN
            '🔴 HIGH PRIORITY: One critical safety issue detected. ' ||
            'Additionally, ' || prs.high_findings || ' high-priority issues found. ' ||
            'Property requires immediate repairs before occupancy.'
        
        WHEN prs.property_risk_score >= 70 THEN
            '🟠 HIGH RISK: Significant issues detected across ' || prs.high_risk_rooms || 
            ' rooms. Recommend extensive repairs and re-inspection.'
        
        WHEN prs.property_risk_score >= 40 THEN
            '🟡 MEDIUM RISK: Multiple issues identified requiring attention. ' ||
            'Property is habitable but requires repairs within 30-60 days.'
        
        WHEN prs.total_findings > 0 THEN
            '🟢 LOW RISK: Property is in generally good condition with ' || 
            prs.total_findings || ' minor issues noted.'
        
        ELSE
            '✅ EXCELLENT: No issues detected during inspection.'
    END AS executive_summary,
    
    -- Critical details
    (SELECT LISTAGG(r.room_name || ': ' || f.finding_description, '; ')
     FROM INSPECTION_FINDINGS f 
     JOIN ROOMS r ON f.room_id = r.room_id
     WHERE f.property_id = p.property_id AND f.severity = 'critical') AS critical_details,
    
    -- Recommended actions
    CASE 
        WHEN prs.critical_findings > 0 THEN
            '1. DO NOT PROCEED with purchase/rental. ' ||
            '2. Request seller to resolve all critical safety issues. ' ||
            '3. Schedule re-inspection after repairs.'
        WHEN prs.property_risk_score >= 70 THEN
            '1. Negotiate 15-25% price reduction. ' ||
            '2. Obtain detailed repair quotes. ' ||
            '3. Set repair deadline before closing.'
        WHEN prs.property_risk_score >= 40 THEN
            '1. Request repairs for high-priority items. ' ||
            '2. Negotiate 5-10% price adjustment. ' ||
            '3. Set 30-day repair timeline.'
        ELSE
            '1. Property approved for occupancy. ' ||
            '2. Establish routine maintenance schedule.'
    END AS recommended_actions

FROM PROPERTIES p
JOIN PROPERTY_RISK_SCORES prs ON p.property_id = prs.property_id;

-- ═══════════════════════════════════════════════════════════════
-- REAL-TIME MONITORING (STREAMS & TASKS)
-- ═══════════════════════════════════════════════════════════════

-- 1. CREATE STREAMS
CREATE OR REPLACE STREAM FINDINGS_STREAM ON TABLE INSPECTION_FINDINGS;
CREATE OR REPLACE STREAM IMAGES_STREAM ON TABLE INSPECTION_IMAGES;


-- 2. CREATE TASKS
-- Note: Requires ACCOUNTADMIN or CREATE TASK privilege

-- Task 1: Detect critical alerts (every 1 minute)
CREATE OR REPLACE TASK DETECT_CRITICAL_ALERTS
    WAREHOUSE = COMPUTE_WH
    SCHEDULE = '1 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('FINDINGS_STREAM')
AS
    INSERT INTO INSPECTION_ALERTS (
        alert_id, property_id, room_id, finding_id,
        alert_type, alert_severity, alert_message
    )
    SELECT 
        UUID_STRING(),
        f.property_id,
        f.room_id,
        f.finding_id,
        'critical_finding',
        'critical',
        '⛔ CRITICAL: ' || f.finding_description || ' in ' || r.room_name
    FROM FINDINGS_STREAM f
    JOIN ROOMS r ON f.room_id = r.room_id
    WHERE f.severity = 'critical'
      AND METADATA$ACTION = 'INSERT';

-- Task 2: Recalculate risk scores (every 5 minutes)
-- Ideally this would refresh a materialized view or dynamic table. 
-- For now, this is just a placeholder as our scores are VIEWS (calculated on fly).
-- If we were using tables for scores, we would update them here.
CREATE OR REPLACE TASK RECALCULATE_RISK_SCORES
    SCHEDULE = '5 MINUTE'
AS
    SELECT 1; -- Placeholder action

-- Activate tasks
-- ALTER TASK DETECT_CRITICAL_ALERTS RESUME;
-- ALTER TASK RECALCULATE_RISK_SCORES RESUME;


-- ═══════════════════════════════════════════════════════════════
-- SAMPLE DATA - INSERT FOR TESTING
-- ═══════════════════════════════════════════════════════════════

-- Insert test users
INSERT INTO USERS VALUES
    ('USER001', 'john_buyer', 'john@example.com', 'normal_user', 'John Doe', '+91-9876543210', TRUE, CURRENT_TIMESTAMP(), NULL),
    ('USER002', 'inspector_raj', 'raj@example.com', 'inspector', 'Rajesh Kumar', '+91-9876543211', TRUE, CURRENT_TIMESTAMP(), NULL);

-- Insert inspector profile
INSERT INTO INSPECTOR_PROFILES VALUES
    ('INSP001', 'USER002', 'LIC12345', ARRAY_CONSTRUCT('Certified Inspector'), 
     ARRAY_CONSTRUCT('structural', 'electrical'), 15, 4.8, 523, TRUE);

-- Insert test properties
INSERT INTO PROPERTIES VALUES
    ('PROP001', '301', 'Skyline Apartments Unit 301', '123 Marine Drive, Kochi', 
     'apartment', 'newly_built', 5, 'USER001', 'private', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
    ('PROP002', '202', 'Green Valley Villa', '45 Hill Road, Trivandrum',
     'villa', 'under_construction', 8, 'USER001', 'public', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

-- Insert rooms
INSERT INTO ROOMS VALUES
    ('RM001', 'PROP001', 'Master Bedroom', 'bedroom', 180.5, 3),
    ('RM002', 'PROP001', 'Kitchen', 'kitchen', 120.0, 3),
    ('RM003', 'PROP001', 'Bathroom 1', 'bathroom', 65.0, 3),
    ('RM004', 'PROP001', 'Living Room', 'living_room', 250.0, 3),
    ('RM005', 'PROP001', 'Balcony', 'utility', 80.0, 3);

-- Insert test findings
INSERT INTO INSPECTION_FINDINGS VALUES
    ('FND001', 'RM001', 'PROP001', 'moisture', 'Visible damp patches on north wall', 'high', 
     'Water seepage from external wall, needs waterproofing', 'ai', 0.89, CURRENT_TIMESTAMP()),
    ('FND002', 'RM002', 'PROP001', 'electrical', 'Exposed wiring near sink area', 'critical',
     'Major safety hazard, immediate action required', 'ai', 0.95, CURRENT_TIMESTAMP()),
    ('FND003', 'RM003', 'PROP001', 'plumbing', 'Minor leak under washbasin', 'medium',
     'Pipe fitting needs tightening', 'ai', 0.82, CURRENT_TIMESTAMP());

-- Insert defect classification rules
INSERT INTO DEFECT_CLASSIFICATION_RULES VALUES
    (1, 'crack', 'structural', 'high', 0.85, 'Structural integrity compromised'),
    (2, 'exposed_wiring', 'electrical', 'critical', 1.00, 'Immediate safety hazard'),
    (3, 'damp', 'moisture', 'high', 0.80, 'Water ingress issues'),
    (4, 'leak', 'plumbing', 'medium', 0.60, 'Active water leakage'),
    (5, 'poor_finish', 'finishing', 'low', 0.30, 'Cosmetic issues');
