import sqlite3
import pandas as pd
import streamlit as st
import os

DB_FILE = "local_db.sqlite"

def get_db_connection():
    """Get or create SQLite connection."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database with tables and views."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. USERS
    c.execute("""
        CREATE TABLE IF NOT EXISTS USERS (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            email TEXT UNIQUE,
            password TEXT,
            user_type TEXT,
            full_name TEXT,
            phone TEXT,
            verified BOOLEAN,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
    """)
    
    # 2. INSPECTOR_PROFILES
    c.execute("""
        CREATE TABLE IF NOT EXISTS INSPECTOR_PROFILES (
            inspector_id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES USERS(user_id),
            license_number TEXT,
            certifications TEXT, -- Stored as JSON string
            specialization TEXT, -- Stored as JSON string
            years_experience INTEGER,
            rating REAL,
            total_inspections INTEGER DEFAULT 0,
            verified_inspector BOOLEAN
        )
    """)
    
    # 3. PROPERTIES
    c.execute("""
        CREATE TABLE IF NOT EXISTS PROPERTIES (
            property_id TEXT PRIMARY KEY,
            house_number TEXT,
            property_name TEXT,
            address TEXT,
            property_type TEXT,
            construction_status TEXT,
            total_rooms INTEGER,
            owner_user_id TEXT REFERENCES USERS(user_id),
            report_visibility TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 4. ROOMS
    c.execute("""
        CREATE TABLE IF NOT EXISTS ROOMS (
            room_id TEXT PRIMARY KEY,
            property_id TEXT REFERENCES PROPERTIES(property_id),
            room_name TEXT,
            room_type TEXT,
            area_sqft REAL,
            floor_number INTEGER
        )
    """)
    
    # 5. INSPECTION_FINDINGS
    c.execute("""
        CREATE TABLE IF NOT EXISTS INSPECTION_FINDINGS (
            finding_id TEXT PRIMARY KEY,
            room_id TEXT REFERENCES ROOMS(room_id),
            property_id TEXT REFERENCES PROPERTIES(property_id),
            finding_category TEXT,
            finding_description TEXT,
            severity TEXT,
            inspector_notes TEXT,
            detected_by TEXT,
            confidence_score REAL,
            finding_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 6. INSPECTION_IMAGES
    c.execute("""
        CREATE TABLE IF NOT EXISTS INSPECTION_IMAGES (
            image_id TEXT PRIMARY KEY,
            upload_session_id TEXT,
            user_id TEXT REFERENCES USERS(user_id),
            property_id TEXT REFERENCES PROPERTIES(property_id),
            room_id TEXT REFERENCES ROOMS(room_id),
            upload_scenario TEXT,
            image_url TEXT,
            original_filename TEXT,
            ai_detected_defects TEXT,
            ai_confidence_score REAL,
            ai_description TEXT,
            ai_severity TEXT,
            inspector_verified BOOLEAN,
            inspector_override_notes TEXT,
            upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 7. INSPECTOR_REPORTS
    c.execute("""
        CREATE TABLE IF NOT EXISTS INSPECTOR_REPORTS (
            report_id TEXT PRIMARY KEY,
            property_id TEXT REFERENCES PROPERTIES(property_id),
            inspector_id TEXT REFERENCES INSPECTOR_PROFILES(inspector_id),
            inspection_date DATETIME,
            manual_risk_score REAL,
            ai_risk_score REAL,
            score_variance REAL,
            agreement_percentage REAL,
            final_approved_score REAL,
            inspector_summary TEXT,
            status TEXT
        )
    """)
    
    
    # 8. INSPECTION_DOCUMENTS
    c.execute("""
    CREATE TABLE IF NOT EXISTS INSPECTION_DOCUMENTS (
        doc_id TEXT PRIMARY KEY,
        property_id TEXT,
        user_id TEXT,
        filename TEXT,
        file_url TEXT,
        extracted_text TEXT,
        ai_summary TEXT,
        ai_suggestions TEXT,
        upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES PROPERTIES(property_id),
        FOREIGN KEY (user_id) REFERENCES USERS(user_id)
    )
    """)
    
    # 9. INSPECTION_RATINGS
    c.execute("""
    CREATE TABLE IF NOT EXISTS INSPECTION_RATINGS (
        rating_id TEXT PRIMARY KEY,
        report_id TEXT REFERENCES INSPECTOR_REPORTS(report_id),
        user_id TEXT REFERENCES USERS(user_id),
        inspector_id TEXT REFERENCES INSPECTOR_PROFILES(inspector_id),
        rating_score INTEGER,
        feedback TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)


    
    # 10. ACCESS_REQUESTS
    c.execute("""
    CREATE TABLE IF NOT EXISTS ACCESS_REQUESTS (
        request_id TEXT PRIMARY KEY,
        property_id TEXT REFERENCES PROPERTIES(property_id),
        requester_user_id TEXT REFERENCES USERS(user_id),
        owner_user_id TEXT REFERENCES USERS(user_id),
        status TEXT, -- 'pending', 'approved', 'rejected'
        request_date DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)



    # 11. INSPECTION_SERVICE_REQUESTS
    c.execute("""
    CREATE TABLE IF NOT EXISTS INSPECTION_SERVICE_REQUESTS (
        service_id TEXT PRIMARY KEY,
        property_id TEXT REFERENCES PROPERTIES(property_id),
        requester_user_id TEXT REFERENCES USERS(user_id),
        status TEXT, -- 'requested', 'in_progress', 'completed'
        request_date DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # VIEWS (Simulated as Tables for SQLite simpler handling or Real Views)
    # SQLite supports views, let's try creating them.
    
    # ROOM_RISK_SCORES View
    c.execute("DROP VIEW IF EXISTS ROOM_RISK_SCORES")
    c.execute("""
    CREATE VIEW ROOM_RISK_SCORES AS
    SELECT 
        r.room_id,
        r.property_id,
        r.room_name,
        r.room_type,
        
        SUM(CASE WHEN f.severity = 'critical' THEN 1 ELSE 0 END) AS critical_count,
        SUM(CASE WHEN f.severity = 'high' THEN 1 ELSE 0 END) AS high_count,
        SUM(CASE WHEN f.severity = 'medium' THEN 1 ELSE 0 END) AS medium_count,
        SUM(CASE WHEN f.severity = 'low' THEN 1 ELSE 0 END) AS low_count,
        
        MIN(100, 
            (SUM(CASE WHEN f.severity = 'critical' THEN 1 ELSE 0 END) * 40) +
            (SUM(CASE WHEN f.severity = 'high' THEN 1 ELSE 0 END) * 25) +
            (SUM(CASE WHEN f.severity = 'medium' THEN 1 ELSE 0 END) * 15) +
            (SUM(CASE WHEN f.severity = 'low' THEN 1 ELSE 0 END) * 5)
        ) AS risk_score,
        
        CASE 
            WHEN SUM(CASE WHEN f.severity = 'critical' THEN 1 ELSE 0 END) > 0 THEN 'CRITICAL'
            WHEN SUM(CASE WHEN f.severity = 'high' THEN 1 ELSE 0 END) > 0 THEN 'HIGH RISK'
            WHEN SUM(CASE WHEN f.severity = 'medium' THEN 1 ELSE 0 END) > 1 THEN 'MEDIUM RISK'
            WHEN COUNT(f.finding_id) > 0 THEN 'LOW RISK'
            ELSE 'NO ISSUES'
        END AS risk_category

    FROM ROOMS r
    LEFT JOIN INSPECTION_FINDINGS f ON r.room_id = f.room_id
    GROUP BY r.room_id, r.property_id, r.room_name, r.room_type
    """)

    # PROPERTY_RISK_SCORES View
    c.execute("DROP VIEW IF EXISTS PROPERTY_RISK_SCORES")
    c.execute("""
    CREATE VIEW PROPERTY_RISK_SCORES AS
    SELECT 
        p.property_id,
        p.property_name,
        p.address,
        COUNT(DISTINCT f.finding_id) AS total_findings,
        SUM(CASE WHEN f.severity = 'critical' THEN 1 ELSE 0 END) AS critical_findings,
        SUM(CASE WHEN f.severity = 'high' THEN 1 ELSE 0 END) AS high_findings,
        
        MIN(100, 
            (SUM(CASE WHEN f.severity = 'critical' THEN 1 ELSE 0 END) * 40) + 
            (SUM(CASE WHEN f.severity = 'high' THEN 1 ELSE 0 END) * 20) + 
            (SUM(CASE WHEN f.severity = 'medium' THEN 1 ELSE 0 END) * 10) + 
            (SUM(CASE WHEN f.severity = 'low' THEN 1 ELSE 0 END) * 2)
        ) AS property_risk_score,
        
        CASE 
            WHEN SUM(CASE WHEN f.severity = 'critical' THEN 1 ELSE 0 END) >= 1 THEN 'CRITICAL'
            WHEN SUM(CASE WHEN f.severity = 'high' THEN 1 ELSE 0 END) >= 1 THEN 'HIGH RISK'
            WHEN SUM(CASE WHEN f.severity = 'medium' THEN 1 ELSE 0 END) >= 2 THEN 'MEDIUM RISK'
            WHEN COUNT(f.finding_id) > 0 THEN 'LOW RISK'
            ELSE 'NO ISSUES'
        END AS risk_rating,
        
        'Check actionable findings' AS recommendation

    FROM PROPERTIES p
    LEFT JOIN ROOMS r ON p.property_id = r.property_id
    LEFT JOIN INSPECTION_FINDINGS f ON r.room_id = f.room_id
    GROUP BY p.property_id, p.property_name, p.address
    """)

    # PROPERTY_INSPECTION_SUMMARY View
    c.execute("DROP VIEW IF EXISTS PROPERTY_INSPECTION_SUMMARY")
    c.execute("""
    CREATE VIEW PROPERTY_INSPECTION_SUMMARY AS
    SELECT 
        p.property_id,
        p.property_name,
        prs.property_risk_score,
        prs.risk_rating,
        'Executive Summary: Risk level is ' || prs.risk_rating AS executive_summary,
        'Action Required' AS recommended_actions
    FROM PROPERTIES p
    JOIN PROPERTY_RISK_SCORES prs ON p.property_id = prs.property_id
    """)

    # AI_CLASSIFIED_DEFECTS (Mock View)
    c.execute("DROP VIEW IF EXISTS AI_CLASSIFIED_DEFECTS")
    c.execute("""
    CREATE VIEW AI_CLASSIFIED_DEFECTS AS
    SELECT 
        f.finding_id,
        f.property_id,
        r.room_name,
        f.finding_category,
        f.finding_description,
        f.severity AS original_severity,
        f.confidence_score,
        
        f.severity AS ai_predicted_severity,
        'Urgent' AS urgency_score,
        f.finding_description AS defect_summary
    FROM INSPECTION_FINDINGS f
    LEFT JOIN ROOMS r ON f.room_id = r.room_id
    """)

    conn.commit()

# Init DB on first import
if not os.path.exists(DB_FILE):
    init_db()

# Re-run init to ensure views exist if code changed
init_db()

# Auto-migration for existing DBs
def migrate_db():
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE USERS ADD COLUMN password TEXT")
        conn.commit()
    except Exception:
        # Column likely exists
        pass

migrate_db()

def run_query(query):
    """Run SQL query on SQLite"""
    conn = get_db_connection()
    try:
        # Simple fix for ILIKE which is standard in Snowflake/Postgres but LIKE in SQLite (case insensitive by default for ASCII)
        query = query.replace("ILIKE", "LIKE")
        return pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"Query failed: {query}\nError: {e}")
        return pd.DataFrame()

def execute_statement(statement):
    """Execute SQL statement"""
    conn = get_db_connection()
    try:
        # Fix for Snowflake ARRAY_CONSTRUCT
        statement = statement.replace("ARRAY_CONSTRUCT", "")
        cursor = conn.cursor()
        cursor.execute(statement)
        conn.commit()
    except Exception as e:
        print(f"Exec failed: {statement}\nError: {e}")
