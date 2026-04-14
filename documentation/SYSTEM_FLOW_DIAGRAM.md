# System Flow Diagrams - NOAA Storm Analytics

Visual representations of how the system works.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER                                       │
│                    (Asks natural language questions)                    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         GRADIO WEB UI                                   │
│                    http://localhost:7860                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Natural Language Input Box                                      │  │
│  │  "Show me all places where hurricane deaths occurred in 2020"    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  [🔍 Analyze Button]                                                    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   ANALYTICS ORCHESTRATOR                                │
│              (analytics_orchestrator.py)                                │
│                                                                         │
│  Coordinates 5 components in sequence:                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │  Parse  │→ │  Query  │→ │Response │→ │ Format  │→ │  Excel  │    │
│  │  Query  │  │Database │  │Generate │  │  Table  │  │  Export │    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │
└────────────────────────────────────────────────────────────────────────┘
                    │              │              │
                    ▼              ▼              ▼
        ┌───────────────┐  ┌─────────────┐  ┌───────────────┐
        │   Groq AI     │  │ PostgreSQL  │  │   Groq AI     │
        │   (Parse)     │  │  Database   │  │  (Narrate)    │
        │               │  │             │  │               │
        │ LLaMA 3.3 70B │  │ 1.7M records│  │ LLaMA 3.3 70B │
        └───────────────┘  └─────────────┘  └───────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  PostgreSQL 17          │
                    │  + PostGIS 3.6          │
                    │                         │
                    │  storm_events table     │
                    │  1,776,003 rows         │
                    │  54 columns             │
                    │  11 indexes             │
                    │  ~1.4GB storage         │
                    └─────────────────────────┘
```

---

## 2. Data Flow (Step-by-Step)

```
STEP 1: USER INPUT
┌──────────────────────────────────────────────────────────────┐
│ User types: "Show me hurricane deaths in 2020"              │
│ Clicks: [Analyze] button                                    │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
STEP 2: GROQ AI PARSING
┌──────────────────────────────────────────────────────────────┐
│ query_parser_gemini.py                                       │
│ ────────────────────────────────────────────────────────────│
│ Sends to Groq API: "Extract filters from: Show me..."       │
│                                                              │
│ Groq understands:                                            │
│   - "hurricane" → event_type = Hurricane                    │
│   - "deaths" → has_deaths = true                            │
│   - "2020" → year = 2020                                    │
│                                                              │
│ Returns JSON:                                                │
│ {                                                            │
│   "event_types": ["Hurricane"],                             │
│   "years": [2020],                                           │
│   "has_deaths": true,                                        │
│   "output_mode": "locations"                                 │
│ }                                                            │
└──────────────────────┬───────────────────────────────────────┘
                       │ [1-2 seconds]
                       ▼
STEP 3: POSTGRESQL QUERY
┌──────────────────────────────────────────────────────────────┐
│ query_engine_postgres.py                                     │
│ ────────────────────────────────────────────────────────────│
│ Builds SQL:                                                  │
│   SELECT * FROM storm_events                                 │
│   WHERE event_type = 'Hurricane'                             │
│     AND year = 2020                                          │
│     AND (deaths_direct > 0 OR deaths_indirect > 0)           │
│                                                              │
│ PostgreSQL executes:                                         │
│   1. Index scan on event_type → 2,456 hurricanes           │
│   2. Index scan on year → 128 in 2020                       │
│   3. Filter deaths > 0 → 23 events                          │
│                                                              │
│ Returns: DataFrame with 23 rows × 54 columns                │
└──────────────────────┬───────────────────────────────────────┘
                       │ [0.01-0.1 seconds]
                       ▼
STEP 4: CALCULATE STATISTICS
┌──────────────────────────────────────────────────────────────┐
│ Python/Pandas processing                                     │
│ ────────────────────────────────────────────────────────────│
│ Summary statistics:                                          │
│   - Total events: 23                                         │
│   - Total deaths: 47 (32 direct + 15 indirect)              │
│   - Total damage: $1,234,567,890                            │
│   - States: LA, TX, FL, MS, AL... (12 states)               │
│                                                              │
│ Aggregation by state:                                        │
│   - Louisiana: 12 events, 18 deaths, $450M                  │
│   - Texas: 7 events, 12 deaths, $320M                       │
│   - Florida: 3 events, 9 deaths, $280M                      │
└──────────────────────┬───────────────────────────────────────┘
                       │ [0.05 seconds]
                       ▼
STEP 5: GROQ AI NARRATIVE
┌──────────────────────────────────────────────────────────────┐
│ response_generator.py                                        │
│ ────────────────────────────────────────────────────────────│
│ Sends to Groq API:                                           │
│   "Generate analysis. Query: 'Show me...'                   │
│    Results: 23 events, 47 deaths, $1.2B damage..."          │
│                                                              │
│ Groq generates:                                              │
│   "Based on NOAA records from 2020, there were **23         │
│    hurricane events with fatalities** across **12           │
│    locations**...                                            │
│                                                              │
│    Louisiana experienced the highest impact with **18       │
│    deaths**... [full narrative with markdown]"              │
└──────────────────────┬───────────────────────────────────────┘
                       │ [1-2 seconds]
                       ▼
STEP 6: FORMAT TABLE
┌──────────────────────────────────────────────────────────────┐
│ table_formatter.py                                           │
│ ────────────────────────────────────────────────────────────│
│ Selects columns for display:                                 │
│   - Location                                                 │
│   - Event Count                                              │
│   - Total Deaths                                             │
│   - Total Damage                                             │
│                                                              │
│ Formats values:                                              │
│   - 1500000 → "$1,500,000"                                  │
│   - Combines direct + indirect deaths                        │
│                                                              │
│ Limits to first 100 rows (for performance)                   │
└──────────────────────┬───────────────────────────────────────┘
                       │ [0.02 seconds]
                       ▼
STEP 7: EXCEL EXPORT
┌──────────────────────────────────────────────────────────────┐
│ excel_exporter.py                                            │
│ ────────────────────────────────────────────────────────────│
│ Creates Excel file:                                          │
│   Sheet 1: Summary                                           │
│     - User query                                             │
│     - AI narrative                                           │
│     - Key statistics                                         │
│                                                              │
│   Sheet 2: Complete Data                                     │
│     - ALL 23 events (not just 100)                          │
│     - ALL 54 NOAA columns                                    │
│     - Unmodified research data                               │
│                                                              │
│   Sheet 3: Metadata                                          │
│     - Column descriptions                                    │
│     - Data source info                                       │
│                                                              │
│ Saves to: /tmp/storm_analytics_hurricane_2020_*.xlsx        │
└──────────────────────┬───────────────────────────────────────┘
                       │ [0.8 seconds]
                       ▼
STEP 8: DISPLAY RESULTS
┌──────────────────────────────────────────────────────────────┐
│ Gradio UI shows:                                             │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 📝 Analysis                                            │  │
│ │ Based on NOAA records from 2020, there were **23      │  │
│ │ hurricane events with fatalities**... [full narrative] │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 📋 Data Table                                          │  │
│ │ Location     | Events | Deaths | Damage                │  │
│ │ ──────────────────────────────────────────────────────│  │
│ │ Louisiana    |   12   |   18   | $450,000,000         │  │
│ │ Texas        |    7   |   12   | $320,000,000         │  │
│ │ Florida      |    3   |    9   | $280,000,000         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 📥 Download Complete Data (Excel)                      │  │
│ │ [storm_analytics_hurricane_2020_*.xlsx]                │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Query Type: Locations                                        │
│ Results Found: 23 events                                     │
│ Date Range: 2020-01-15 to 2020-12-28                        │
└──────────────────────────────────────────────────────────────┘

TOTAL TIME: ~3.5 seconds (from user click to display)
```

---

## 3. Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    GRADIO WEB UI                                │
│                 (User Interface Layer)                          │
│                                                                 │
│  User Input → process_query() → Display Results                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│             ANALYTICS ORCHESTRATOR                              │
│          (Business Logic Coordinator)                           │
│                                                                 │
│  orchestrator.process_query(query)                              │
│     ├─→ parser.parse(query)                                     │
│     ├─→ engine.execute_query(parsed)                            │
│     ├─→ generator.generate_response(results)                    │
│     ├─→ formatter.format_for_display(data)                      │
│     └─→ exporter.generate_excel(data)                           │
└──┬────────┬────────┬────────┬────────┬─────────────────────────┘
   │        │        │        │        │
   ▼        ▼        ▼        ▼        ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│Query ││Query ││Resp. ││Table ││Excel │
│Parser││Engine││Gen.  ││Format││Export│
└──┬───┘└──┬───┘└──┬───┘└──────┘└──────┘
   │       │       │
   │       │       │
   ▼       ▼       ▼
┌─────┐┌─────────────────────┐┌─────┐
│Groq ││   PostgreSQL DB     ││Groq │
│ API ││   ┌──────────────┐  ││ API │
│     ││   │storm_events  │  ││     │
│     ││   │table         │  ││     │
│     ││   │              │  ││     │
│     ││   │1,776,003 rows│  ││     │
│     ││   │54 columns    │  ││     │
│     ││   │11 indexes    │  ││     │
│     ││   └──────────────┘  ││     │
└─────┘└─────────────────────┘└─────┘

EXTERNAL SERVICES:
- Groq API: LLM inference (query parsing & narrative generation)
- PostgreSQL: Data storage and querying

INTERNAL COMPONENTS:
- Orchestrator: Workflow coordination
- Parser: NL → Structured filters
- Engine: Filters → SQL → Results
- Generator: Results → Natural language
- Formatter: Data presentation
- Exporter: Excel file generation
```

---

## 4. Database Query Execution Flow

```
USER FILTER
┌──────────────────────────────────┐
│ event_types: ["Hurricane"]      │
│ years: [2020]                    │
│ has_deaths: true                 │
└────────────┬─────────────────────┘
             │
             ▼
SQL GENERATION (query_engine_postgres.py)
┌──────────────────────────────────────────────────────────┐
│ sql_parts = ["SELECT * FROM storm_events WHERE 1=1"]    │
│                                                          │
│ IF event_types:                                          │
│   sql_parts.append("AND event_type IN (:event_type_0)") │
│   params['event_type_0'] = 'Hurricane'                  │
│                                                          │
│ IF years:                                                │
│   sql_parts.append("AND year IN (:year_0)")             │
│   params['year_0'] = 2020                               │
│                                                          │
│ IF has_deaths:                                           │
│   sql_parts.append("AND (deaths_direct > 0 OR           │
│                          deaths_indirect > 0)")          │
│                                                          │
│ Final SQL:                                               │
│ SELECT * FROM storm_events                               │
│ WHERE 1=1                                                │
│   AND event_type IN ('Hurricane')                       │
│   AND year IN (2020)                                     │
│   AND (deaths_direct > 0 OR deaths_indirect > 0)         │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
POSTGRESQL EXECUTION
┌──────────────────────────────────────────────────────────┐
│ Query Planner Analyzes Query:                            │
│                                                          │
│ Step 1: Scan idx_event_type                             │
│   Filter: event_type = 'Hurricane'                      │
│   Result: 2,456 rows                                     │
│                                                          │
│ Step 2: Scan idx_year                                    │
│   Filter: year = 2020                                    │
│   Result: 128 rows                                       │
│                                                          │
│ Step 3: Scan idx_has_deaths (partial index)             │
│   Filter: (deaths_direct + deaths_indirect) > 0         │
│   Result: 23 rows                                        │
│                                                          │
│ Step 4: Fetch full rows from table                       │
│   Load all 54 columns for 23 events                      │
│                                                          │
│ Execution time: ~0.018 seconds                           │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
RESULT SET (Pandas DataFrame)
┌──────────────────────────────────────────────────────────┐
│ 23 rows × 54 columns                                     │
│                                                          │
│ Columns include:                                         │
│ - event_id, event_type, state, cz_name                  │
│ - begin_date_time, end_date_time                        │
│ - begin_lat, begin_lon, begin_location (PostGIS)        │
│ - deaths_direct, deaths_indirect                         │
│ - injuries_direct, injuries_indirect                     │
│ - damage_property_num, damage_crops_num, total_damage   │
│ - magnitude, tor_f_scale, tor_length, tor_width         │
│ - event_narrative, episode_narrative                     │
│ - ... (44 more NOAA columns)                            │
└──────────────────────────────────────────────────────────┘
```

---

## 5. PostgreSQL Index Strategy

```
STORM_EVENTS TABLE (1,776,003 rows)
│
├─ PRIMARY KEY: event_id
│
├─ SINGLE-COLUMN INDEXES (Fast single-filter queries)
│  ├─ idx_event_type → event_type
│  ├─ idx_state → state
│  ├─ idx_year → year
│  └─ idx_begin_date → begin_date_time
│
├─ COMPOSITE INDEX (Multi-filter queries)
│  └─ idx_event_state_year → (event_type, state, year)
│
├─ PARTIAL INDEXES (Only index relevant subset)
│  ├─ idx_has_deaths → (deaths_direct + deaths_indirect)
│  │   WHERE (deaths_direct + deaths_indirect) > 0
│  │   [Only ~5% of rows have deaths]
│  │
│  └─ idx_has_damage → total_damage
│      WHERE total_damage > 0
│      [Only ~60% of rows have damage]
│
├─ SPATIAL INDEX (PostGIS geographic queries)
│  └─ idx_begin_location_gist → begin_location (GIST index)
│
└─ LOCATION AGGREGATION INDEX
   └─ idx_state_county → (state, cz_name)

QUERY OPTIMIZATION EXAMPLES:

Query: "Hurricanes in 2020 with deaths"
  Uses: idx_event_type + idx_year + idx_has_deaths
  Scan: 2,456 → 128 → 23 rows
  Time: 0.018s

Query: "All tornadoes in Oklahoma in 2021"
  Uses: idx_event_state_year (composite)
  Scan: Direct to 456 matching rows
  Time: 0.008s

Query: "Events within 50 miles of Dallas, TX"
  Uses: idx_begin_location_gist (PostGIS)
  Spatial query: ST_DWithin(begin_location, point, 80467)
  Time: 0.025s
```

---

## 6. Dual Backend Architecture

```
APPLICATION STARTUP
│
├─ Load .env configuration
│  └─ QUERY_BACKEND = "postgresql"  (or "pandas")
│
└─ Analytics Orchestrator Initialization
   │
   ├─ IF QUERY_BACKEND == "postgresql":
   │  │
   │  ├─ Import: PostgreSQLQueryEngine
   │  ├─ Connect to PostgreSQL database
   │  ├─ Test connection (get row count, date range)
   │  └─ Initialize engine
   │     │
   │     └─ Ready: PostgreSQL backend
   │        - 1,776,003 records
   │        - SQLAlchemy queries
   │        - Connection pooling
   │
   └─ ELSE (QUERY_BACKEND == "pandas"):
      │
      ├─ Import: StormQueryEngine
      ├─ Load parquet file into memory
      ├─ Validate DataFrame
      └─ Initialize engine
         │
         └─ Ready: Pandas backend
            - 1,117,547 records
            - In-memory operations
            - Single process

QUERY EXECUTION (Same interface for both backends)
│
├─ execute_query(parsed_query)
│  │
│  ├─ PostgreSQL Engine:
│  │  └─ Converts filters → SQL WHERE clauses
│  │     Executes: pd.read_sql(query, connection)
│  │     Returns: Pandas DataFrame
│  │
│  └─ Pandas Engine:
│     └─ Converts filters → DataFrame operations
│        Executes: df[df['column'] == value]
│        Returns: Pandas DataFrame
│
└─ Both return identical structure:
   {
     'success': True,
     'data': pd.DataFrame,
     'summary': {...},
     'aggregated': pd.DataFrame | None
   }

BENEFITS:
✓ Same code works with both backends
✓ Zero-downtime migration (switch via config)
✓ Easy testing (compare pandas vs postgres results)
✓ Instant rollback if issues
```

---

## 7. Excel Export Structure

```
EXCEL FILE: storm_analytics_hurricane_2020_20260413_215535.xlsx
│
├─ SHEET 1: Summary
│  ├─ User Query
│  │  "Show me all places where hurricane deaths occurred in 2020"
│  │
│  ├─ AI Narrative
│  │  "Based on NOAA records from 2020, there were **23 hurricane
│  │   events with fatalities** across **12 locations**..."
│  │
│  └─ Key Statistics Table
│     ┌─────────────────────┬──────────┐
│     │ Metric              │ Value    │
│     ├─────────────────────┼──────────┤
│     │ Total Events        │ 23       │
│     │ Total Deaths        │ 47       │
│     │ Total Injuries      │ 89       │
│     │ Total Damage        │ $1.23B   │
│     │ Date Range          │ 2020     │
│     │ States Covered      │ 12       │
│     └─────────────────────┴──────────┘
│
├─ SHEET 2: Complete Data (RESEARCH-READY)
│  │
│  │ ALL 23 matching events
│  │ ALL 54 NOAA columns (unmodified)
│  │
│  ┌────────┬──────────┬───────┬─────────┬────────────┬─────┐
│  │event_id│event_type│ state │ cz_name │ begin_date │ ... │
│  ├────────┼──────────┼───────┼─────────┼────────────┼─────┤
│  │1234567 │Hurricane │  LA   │Orleans  │2020-08-29  │ ... │
│  │1234568 │Hurricane │  LA   │Jefferson│2020-08-29  │ ... │
│  │1234569 │Hurricane │  TX   │ Harris  │2020-09-15  │ ... │
│  │  ...   │   ...    │  ...  │   ...   │    ...     │ ... │
│  └────────┴──────────┴───────┴─────────┴────────────┴─────┘
│  │
│  └─ [50 more columns: deaths, injuries, damage, magnitude,
│      tor_f_scale, narratives, etc.]
│
└─ SHEET 3: Metadata
   │
   ├─ Column Descriptions
   │  - event_id: Unique NOAA event identifier
   │  - event_type: Type of storm event
   │  - deaths_direct: Direct fatalities
   │  - ... (all 54 columns documented)
   │
   ├─ Data Source
   │  - Database: NOAA Storm Events Database
   │  - URL: https://www.ncdc.noaa.gov/stormevents/
   │  - Years: 1996-2025
   │  - Total Records: 1,776,003
   │
   └─ Query Info
      - User Query: "Show me all places..."
      - Filters Applied: event_type=Hurricane, year=2020, deaths>0
      - Results Count: 23 events
      - Date Generated: 2026-04-13 21:55:35
```

---

## 8. Technology Integration Map

```
┌────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                     │
├────────────────────────────────────────────────────────────┤
│  Gradio 6.12                                               │
│  - Web UI framework                                        │
│  - Input/Output components                                 │
│  - File downloads                                          │
│  - Public URL sharing                                      │
└──────────────────────┬─────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                        │
├────────────────────────────────────────────────────────────┤
│  Python 3.14                                               │
│  - Analytics orchestrator                                  │
│  - Query processing logic                                  │
│  - Data formatting                                         │
│  - Excel generation (openpyxl)                             │
└──┬──────────┬──────────┬──────────────────────────────────┘
   │          │          │
   │          │          │
   ▼          ▼          ▼
┌─────┐  ┌─────────┐  ┌─────┐
│Groq │  │PostgreSQL│ │Pandas│
│ API │  │  Layer   │ │      │
└─────┘  └─────────┘  └─────┘
   │          │          │
   │          │          │
   ▼          ▼          ▼
┌────────────────────────────────────────────────────────────┐
│                      DATA LAYER                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  AI/LLM (External Service)                                 │
│  ├─ Groq Cloud API                                         │
│  ├─ Model: LLaMA 3.3 70B Versatile                        │
│  ├─ Purpose: Query parsing + Narrative generation          │
│  └─ Latency: 1-2 seconds per call                         │
│                                                            │
│  Database (Local Service)                                  │
│  ├─ PostgreSQL 17                                          │
│  ├─ Extension: PostGIS 3.6                                 │
│  ├─ ORM: SQLAlchemy 2.0.23                                 │
│  ├─ Adapter: psycopg2-binary 2.9.9                         │
│  ├─ Storage: 1,776,003 records (~1.4GB)                   │
│  └─ Query time: 0.01-0.1 seconds                          │
│                                                            │
│  Data Processing (In-Memory)                               │
│  ├─ Pandas 3.0+ (DataFrames)                              │
│  ├─ NumPy 2.0+ (Numerical ops)                            │
│  └─ PyArrow 13.0+ (Parquet handling)                      │
│                                                            │
└────────────────────────────────────────────────────────────┘

COMMUNICATION PROTOCOLS:
- HTTP/REST: Gradio ↔ Groq API
- PostgreSQL Wire Protocol: Python ↔ PostgreSQL
- Local function calls: Python components
```

---

## End of System Flow Diagrams

These diagrams show how the NOAA Storm Analytics System processes user queries from input to output, demonstrating the integration of AI, databases, and web technologies.

**For Questions During Presentation:**
- Show specific diagram based on professor's question
- Walk through data flow step-by-step
- Highlight PostgreSQL performance vs pandas
- Demonstrate AI integration points
