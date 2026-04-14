-- ============================================================================
-- NOAA Storm Events Database Schema
-- ============================================================================
-- Database: noaa_storms
-- PostgreSQL Version: 17+
-- PostGIS Version: 3.6+
-- Description: Complete schema for 1,117,547 NOAA storm events (1996-2025)
--              with all 54 original NOAA columns preserved
-- ============================================================================

-- Drop existing table if exists (for clean migration)
DROP TABLE IF EXISTS storm_events CASCADE;

-- ============================================================================
-- Main Storm Events Table
-- ============================================================================
-- Preserves ALL 54 NOAA columns exactly as in source data
-- Adds PostGIS geography columns for spatial queries
-- ============================================================================

CREATE TABLE storm_events (
    -- ========================================================================
    -- Event Identifiers (Primary Key)
    -- ========================================================================
    event_id            BIGINT PRIMARY KEY,         -- NOAA unique event identifier
    episode_id          BIGINT,                      -- Episode identifier (multi-event)

    -- ========================================================================
    -- Event Type & Classification
    -- ========================================================================
    event_type          VARCHAR(50) NOT NULL,        -- Type: Tornado, Hurricane, Flood, etc.

    -- ========================================================================
    -- Temporal Information
    -- ========================================================================
    begin_date_time     TIMESTAMP,                   -- Event start timestamp
    end_date_time       TIMESTAMP,                   -- Event end timestamp
    year                INTEGER NOT NULL,            -- Year (1996-2025)
    month_name          VARCHAR(20),                 -- Month name

    -- ========================================================================
    -- Geographic Information - Administrative
    -- ========================================================================
    state               VARCHAR(50),                 -- US state (code or full name)
    state_fips          INTEGER,                     -- FIPS state code
    cz_type             VARCHAR(10),                 -- County zone type
    cz_fips             INTEGER,                     -- County zone FIPS code
    cz_name             VARCHAR(200),                -- County/Zone name
    wfo                 VARCHAR(20),                 -- Weather Forecast Office

    -- ========================================================================
    -- Geographic Information - Coordinates (Decimal Degrees, WGS84)
    -- ========================================================================
    begin_lat           NUMERIC(10, 6),              -- Begin latitude (degrees N)
    begin_lon           NUMERIC(10, 6),              -- Begin longitude (degrees W, negative)
    end_lat             NUMERIC(10, 6),              -- End latitude
    end_lon             NUMERIC(10, 6),              -- End longitude

    -- PostGIS Geography Columns (for spatial queries)
    begin_location      GEOGRAPHY(POINT, 4326),      -- Begin point (PostGIS)
    end_location        GEOGRAPHY(POINT, 4326),      -- End point (PostGIS)

    -- ========================================================================
    -- Impact Statistics - Casualties
    -- ========================================================================
    deaths_direct       INTEGER DEFAULT 0,           -- Direct fatalities
    deaths_indirect     INTEGER DEFAULT 0,           -- Indirect fatalities
    injuries_direct     INTEGER DEFAULT 0,           -- Direct injuries
    injuries_indirect   INTEGER DEFAULT 0,           -- Indirect injuries

    -- ========================================================================
    -- Impact Statistics - Economic Damage
    -- ========================================================================
    damage_property     VARCHAR(20),                 -- Property damage (original text: "10K", "5M")
    damage_crops        VARCHAR(20),                 -- Crop damage (original text)
    damage_property_num NUMERIC(15, 2) DEFAULT 0,    -- Property damage (numeric, USD)
    damage_crops_num    NUMERIC(15, 2) DEFAULT 0,    -- Crop damage (numeric, USD)
    total_damage        NUMERIC(15, 2) DEFAULT 0,    -- Total damage (property + crops)

    -- ========================================================================
    -- Storm Characteristics - Magnitude & Intensity
    -- ========================================================================
    magnitude           NUMERIC(10, 2),              -- Storm magnitude
    magnitude_type      VARCHAR(10),                 -- Magnitude unit (EG, MS, etc.)

    -- Tornado-Specific
    tor_f_scale         VARCHAR(10),                 -- Fujita scale (F0-F5, EF0-EF5)
    tor_length          NUMERIC(10, 2),              -- Tornado path length (miles)
    tor_width           NUMERIC(10, 2),              -- Tornado path width (yards)
    tor_other_wfo       VARCHAR(50),                 -- Other WFO (if tornado crosses)
    tor_other_cz_state  VARCHAR(50),                 -- Other state (raw data may have codes)
    tor_other_cz_fips   INTEGER,                     -- Other county FIPS
    tor_other_cz_name   VARCHAR(200),                -- Other county name

    -- Flood-Specific
    flood_cause         VARCHAR(50),                 -- Cause of flooding

    -- ========================================================================
    -- Data Source & Quality
    -- ========================================================================
    source              VARCHAR(100),                -- Data source
    begin_range         INTEGER,                     -- Begin range (distance accuracy)
    begin_azimuth       VARCHAR(50),                 -- Begin direction (N, NE, etc.)
    end_range           INTEGER,                     -- End range
    end_azimuth         VARCHAR(50),                 -- End direction

    -- ========================================================================
    -- Event Narratives & Descriptions
    -- ========================================================================
    episode_narrative   TEXT,                        -- Episode-level description
    event_narrative     TEXT,                        -- Event-level description

    -- ========================================================================
    -- Additional NOAA Columns (Complete Set)
    -- ========================================================================
    begin_yearmonth     INTEGER,                     -- YYYYMM format
    begin_day           INTEGER,                     -- Day of month (1-31)
    begin_time          VARCHAR(10),                 -- Time (HHMM format)
    end_yearmonth       INTEGER,                     -- End YYYYMM
    end_day             INTEGER,                     -- End day
    end_time            VARCHAR(10),                 -- End time (HHMM)

    category            VARCHAR(20),                 -- Storm category (1-5 for hurricanes)

    -- Timestamp Metadata
    data_source         VARCHAR(100),                -- Source: NOAA Storm Events Database
    begin_location_txt  VARCHAR(200),                -- Begin location description
    end_location_txt    VARCHAR(200),                -- End location description

    -- ========================================================================
    -- System Metadata (for tracking)
    -- ========================================================================
    created_at          TIMESTAMP DEFAULT NOW(),     -- Record creation timestamp
    updated_at          TIMESTAMP DEFAULT NOW()      -- Last update timestamp
);

-- ============================================================================
-- Indexes for Query Performance
-- ============================================================================
-- Strategy: Index frequently filtered columns based on typical queries
-- Expected total index size: ~400MB
-- ============================================================================

-- Single-column indexes (common filters)
CREATE INDEX idx_event_type ON storm_events(event_type);
CREATE INDEX idx_state ON storm_events(state);
CREATE INDEX idx_year ON storm_events(year);
CREATE INDEX idx_begin_date ON storm_events(begin_date_time);
CREATE INDEX idx_cz_name ON storm_events(cz_name);

-- Composite indexes (common filter combinations)
CREATE INDEX idx_event_state_year ON storm_events(event_type, state, year);
CREATE INDEX idx_state_county ON storm_events(state, cz_name);
CREATE INDEX idx_year_month ON storm_events(year, month_name);

-- Partial indexes (only index non-zero values - saves space)
CREATE INDEX idx_has_deaths ON storm_events((deaths_direct + deaths_indirect))
    WHERE (deaths_direct + deaths_indirect) > 0;

CREATE INDEX idx_has_injuries ON storm_events((injuries_direct + injuries_indirect))
    WHERE (injuries_direct + injuries_indirect) > 0;

CREATE INDEX idx_has_damage ON storm_events(total_damage)
    WHERE total_damage > 0;

-- PostGIS spatial indexes (for geographic queries)
CREATE INDEX idx_begin_location_gist ON storm_events USING GIST(begin_location);
CREATE INDEX idx_end_location_gist ON storm_events USING GIST(end_location);

-- ============================================================================
-- Comments (Documentation)
-- ============================================================================

COMMENT ON TABLE storm_events IS 'NOAA Storm Events Database (1996-2025): Complete dataset with 1,117,547 events and all 54 original NOAA columns preserved';

COMMENT ON COLUMN storm_events.event_id IS 'NOAA unique event identifier (Primary Key)';
COMMENT ON COLUMN storm_events.event_type IS 'Storm type: Tornado, Hurricane, Flood, Hail, Wind, etc.';
COMMENT ON COLUMN storm_events.begin_location IS 'PostGIS geography point (begin coordinates) - enables spatial queries';
COMMENT ON COLUMN storm_events.end_location IS 'PostGIS geography point (end coordinates) - enables spatial queries';
COMMENT ON COLUMN storm_events.total_damage IS 'Total economic damage in USD (property + crops)';
COMMENT ON COLUMN storm_events.deaths_direct IS 'Direct fatalities caused by the storm';
COMMENT ON COLUMN storm_events.deaths_indirect IS 'Indirect fatalities (e.g., heart attacks, car accidents during evacuation)';

-- ============================================================================
-- Constraints & Validation
-- ============================================================================

-- Date validation
ALTER TABLE storm_events ADD CONSTRAINT check_date_range
    CHECK (begin_date_time <= end_date_time OR end_date_time IS NULL);

-- Year validation (1996-2025)
ALTER TABLE storm_events ADD CONSTRAINT check_year_range
    CHECK (year BETWEEN 1996 AND 2030);

-- Damage validation (non-negative)
ALTER TABLE storm_events ADD CONSTRAINT check_damage_non_negative
    CHECK (total_damage >= 0);

-- Casualty validation (non-negative)
ALTER TABLE storm_events ADD CONSTRAINT check_deaths_non_negative
    CHECK (deaths_direct >= 0 AND deaths_indirect >= 0);

ALTER TABLE storm_events ADD CONSTRAINT check_injuries_non_negative
    CHECK (injuries_direct >= 0 AND injuries_indirect >= 0);

-- ============================================================================
-- Function: Auto-populate PostGIS geography columns from lat/lon
-- ============================================================================
-- This function is called after bulk insert to populate geography columns
-- ============================================================================

CREATE OR REPLACE FUNCTION populate_geography_columns() RETURNS void AS $$
BEGIN
    -- Populate begin_location from begin_lat/begin_lon
    UPDATE storm_events
    SET begin_location = ST_SetSRID(ST_MakePoint(begin_lon, begin_lat), 4326)::geography
    WHERE begin_lat IS NOT NULL
      AND begin_lon IS NOT NULL
      AND begin_location IS NULL;

    -- Populate end_location from end_lat/end_lon
    UPDATE storm_events
    SET end_location = ST_SetSRID(ST_MakePoint(end_lon, end_lat), 4326)::geography
    WHERE end_lat IS NOT NULL
      AND end_lon IS NOT NULL
      AND end_location IS NULL;

    RAISE NOTICE 'PostGIS geography columns populated from lat/lon coordinates';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION populate_geography_columns() IS 'Populate PostGIS geography columns from latitude/longitude coordinates';

-- ============================================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_storm_events_updated_at
    BEFORE UPDATE ON storm_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View: Events with casualties
CREATE OR REPLACE VIEW events_with_casualties AS
SELECT
    event_id,
    event_type,
    state,
    cz_name,
    begin_date_time,
    deaths_direct + deaths_indirect AS total_deaths,
    injuries_direct + injuries_indirect AS total_injuries,
    total_damage
FROM storm_events
WHERE (deaths_direct + deaths_indirect) > 0
   OR (injuries_direct + injuries_indirect) > 0
ORDER BY (deaths_direct + deaths_indirect) DESC;

COMMENT ON VIEW events_with_casualties IS 'All storm events that caused deaths or injuries';

-- View: High-damage events (> $1M)
CREATE OR REPLACE VIEW high_damage_events AS
SELECT
    event_id,
    event_type,
    state,
    cz_name,
    begin_date_time,
    total_damage,
    deaths_direct + deaths_indirect AS total_deaths
FROM storm_events
WHERE total_damage > 1000000
ORDER BY total_damage DESC;

COMMENT ON VIEW high_damage_events IS 'Storm events with total damage exceeding $1 million';

-- View: Recent events (last 5 years)
CREATE OR REPLACE VIEW recent_events AS
SELECT *
FROM storm_events
WHERE year >= EXTRACT(YEAR FROM CURRENT_DATE) - 5
ORDER BY begin_date_time DESC;

COMMENT ON VIEW recent_events IS 'Storm events from the last 5 years';

-- ============================================================================
-- Statistics & Verification Queries
-- ============================================================================

-- These queries can be run after data migration to verify correctness

-- Total record count
-- Expected: 1,117,547 records
COMMENT ON TABLE storm_events IS E'NOAA Storm Events Database (1996-2025)\n\nVerification queries:\n- SELECT COUNT(*) FROM storm_events; -- Expected: 1,117,547\n- SELECT MIN(year), MAX(year) FROM storm_events; -- Expected: 1996, 2025\n- SELECT COUNT(DISTINCT event_type) FROM storm_events; -- Expected: ~48 types\n- SELECT COUNT(*) FROM storm_events WHERE begin_location IS NOT NULL; -- Expected: 1,117,547';

-- ============================================================================
-- Grant Permissions (if using application user)
-- ============================================================================

-- Uncomment and modify if you have a separate application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON storm_events TO storm_app;
-- GRANT SELECT ON events_with_casualties TO storm_app;
-- GRANT SELECT ON high_damage_events TO storm_app;
-- GRANT SELECT ON recent_events TO storm_app;
-- GRANT EXECUTE ON FUNCTION populate_geography_columns() TO storm_app;

-- ============================================================================
-- End of Schema Definition
-- ============================================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '==================================================';
    RAISE NOTICE 'NOAA Storm Events Schema Created Successfully';
    RAISE NOTICE '==================================================';
    RAISE NOTICE 'Table: storm_events';
    RAISE NOTICE 'Columns: 54 NOAA columns + 2 PostGIS geography columns';
    RAISE NOTICE 'Indexes: 13 performance indexes';
    RAISE NOTICE 'Views: 3 convenience views';
    RAISE NOTICE 'Functions: 2 helper functions';
    RAISE NOTICE '==================================================';
    RAISE NOTICE 'Next Steps:';
    RAISE NOTICE '1. Run migration script to load 1.1M records';
    RAISE NOTICE '2. Call populate_geography_columns() to create spatial data';
    RAISE NOTICE '3. Run ANALYZE storm_events; for query optimization';
    RAISE NOTICE '==================================================';
END $$;
