# CLAUDE.md - Storm Forecasting Chatbot Project

**Last Updated**: March 8, 2026
**Target Completion**: March 20, 2026
**Current Phase**: Data Preprocessing ✅ COMPLETE

---

## Project Overview

A conversational storm-forecasting chatbot that predicts storm likelihood for any US location and future date based on NOAA historical data (2015-2025).

**User Experience**:
```
User: "Will there be a storm in Atlanta on August 18, 2028?"
Bot:  "Based on historical patterns, there is a 42% chance of storm activity
       in Atlanta on August 18, 2028. This represents a medium risk period.
       August is typically peak storm season in the Southeast."
```

**Core Innovation**: Combines BERT natural language understanding with machine learning on 10+ years of NOAA storm data.

---

## System Architecture

```
User Query
    ↓
BERT Query Parser (extract location + date)
    ↓
Geocoding Service (city → lat/lon)
    ↓
Feature Generator (temporal + spatial + historical features)
    ↓
XGBoost Prediction Model (probability: 0.0 - 1.0)
    ↓
Response Generator (format natural language answer)
    ↓
Gradio Web UI (display to user)
```

---

## Tech Stack

### Data & ML
- **pandas** (2.1.0) - Data processing
- **numpy** (1.24.3) - Numerical operations
- **pyarrow** (13.0.0) - Parquet file handling
- **scikit-learn** (1.3.0) - ML utilities, preprocessing
- **xgboost** (2.0.0) - Gradient boosting classifier
- **imbalanced-learn** (0.11.0) - Handling class imbalance

### NLP
- **transformers** (4.32.0) - BERT models from HuggingFace
- **torch** (2.0.1) - PyTorch backend for transformers
- **spacy** (3.6.1) - Alternative NLP pipeline
- **dateparser** (1.1.8) - Parse natural language dates

### Geocoding
- **geopy** (2.3.0) - Location services

### UI
- **gradio** (3.40.0) - Web interface (primary)
- **flask** (2.3.3) - REST API (alternative)

### Utilities
- **tqdm** (4.66.1) - Progress bars
- **joblib** (1.3.2) - Model serialization
- **loguru** (0.7.0) - Logging
- **matplotlib** (3.7.2), **seaborn** (0.12.2) - Visualization

---

## Project Structure

```
Conversational-storm-analysis-prediction-using-NOAA-data/
│
├── data/
│   ├── processed/
│   │   ├── storms_raw.parquet           ✅ 707,100 records (merged)
│   │   ├── storms_cleaned.parquet       ✅ 436,305 records (valid coords)
│   │   ├── storms_features.parquet      ✅ 1,308,915 records (ML-ready)
│   │   └── feature_metadata.pkl         ✅ Feature definitions
│   └── geocoding/
│       └── us_cities.json               🚧 To be created
│
├── dataset/
│   └── StormEvents_details-*.csv        ✅ 11 files (2015-2025)
│
├── models/
│   └── storm_predictor_v1.pkl           🚧 Trained model (next phase)
│
├── src/
│   ├── data/                            ✅ COMPLETE
│   │   ├── __init__.py
│   │   ├── loader.py                    ✅ Load & merge CSVs
│   │   ├── cleaner.py                   ✅ Data cleaning
│   │   └── feature_engineer.py          ✅ Feature extraction
│   │
│   ├── nlp/                             🚧 NEXT PHASE
│   │   ├── __init__.py
│   │   ├── geocoder.py                  🚧 City → coordinates
│   │   ├── query_parser.py              🚧 BERT NER extraction
│   │   └── entity_resolver.py           🚧 Entity linking
│   │
│   ├── models/                          🚧 NEXT PHASE
│   │   ├── __init__.py
│   │   ├── trainer.py                   🚧 Model training
│   │   └── predictor.py                 🚧 Inference pipeline
│   │
│   ├── chatbot/                         🚧 NEXT PHASE
│   │   ├── __init__.py
│   │   ├── orchestrator.py              🚧 End-to-end pipeline
│   │   └── response_generator.py        🚧 Format responses
│   │
│   ├── interfaces/                      🚧 NEXT PHASE
│   │   ├── __init__.py
│   │   └── gradio_app.py                🚧 Web UI
│   │
│   └── utils/
│       └── __init__.py
│
├── notebooks/
│   ├── 01_data_exploration.ipynb        📋 Optional EDA
│   └── 02_model_training.ipynb          📋 Optional experiments
│
├── tests/                               🚧 Testing phase
│
├── requirements.txt                     ✅ Dependencies defined
├── .gitignore                           ✅ Git ignore rules
├── README.md                            ✅ Project documentation
├── CLAUDE.md                            ✅ This file (for Claude context)
└── .claude/
    └── plans/
        └── delegated-sprouting-quill.md ✅ Implementation plan
```

---

## Data Overview

### Source
- **NOAA Storm Events Database** (2015-2025)
- 11 CSV files: `StormEvents_details-ftp_v1.0_dYYYY_*.csv`
- Total raw records: **707,100 storm events**

### Key Columns Used
- **EVENT_ID** - Unique storm identifier
- **BEGIN_DATE_TIME** - Storm start time
- **BEGIN_LAT**, **BEGIN_LON** - Coordinates (already in details files!)
- **STATE** - US state/territory
- **EVENT_TYPE** - Type of storm (55 types)
- **DAMAGE_PROPERTY**, **DAMAGE_CROPS** - Economic impact
- **INJURIES_DIRECT**, **DEATHS_DIRECT** - Casualties

### Data Pipeline Results

| Stage | Records | Notes |
|-------|---------|-------|
| **Raw** | 707,100 | Merged 11 CSVs (2015-2025) |
| **Cleaned** | 436,305 | Removed 38.3% invalid coordinates |
| **Engineered** | 1,308,915 | Added 872k negative samples (no-storm days) |

### Geographic Coverage
- **69 US states/territories**
- **3,665 unique spatial grid cells** (0.5° × 0.5° ≈ 50 miles)
- **Lat range**: 15°N to 72°N (includes Alaska, Hawaii, Puerto Rico)
- **Lon range**: -180°W to -60°W

### Temporal Coverage
- **Date range**: April 1, 2015 - October 31, 2025 (10.5 years)
- **Challenge**: Predict future dates (2028) based on historical patterns

---

## Features Created (19 features + 1 target)

### Temporal Features (12)
- `month` (1-12)
- `day_of_year` (1-365)
- `week_of_year` (1-52)
- `day_of_week` (0-6)
- `season_encoded` (0=Winter, 1=Spring, 2=Summer, 3=Fall)
- `is_summer_peak` (Jun-Aug)
- `is_tornado_season` (Mar-Jun)
- `is_hurricane_season` (Jun-Nov)
- `month_sin`, `month_cos` (cyclic encoding)
- `day_of_year_sin`, `day_of_year_cos` (cyclic encoding)

**Why cyclic encoding?** Preserves the fact that December (12) is close to January (1).

### Spatial Features (4)
- `BEGIN_LAT`, `BEGIN_LON` (exact coordinates)
- `lat_rounded`, `lon_rounded` (0.5° grid)
- `grid_cell_id` (location identifier)

### Historical Features (3)
- `storms_location_month_avg_per_year` (frequency baseline)
- `historical_storm_probability` (simple probability)
- `most_common_event_encoded` (typical storm type for location-month)

### Target Variable (1)
- `storm_occurred` (1 = storm, 0 = no storm)
- **Class balance**: 33% positive, 67% negative (intentional 1:2 ratio)

---

## Model Details (Planned)

### Algorithm
- **XGBoost Classifier** (gradient boosting decision trees)
- Why? Best performance on tabular data, handles missing values, prevents overfitting

### Training Strategy
- **Temporal split** (no shuffling to avoid data leakage):
  - Train: 2015-2022 (8 years)
  - Validation: 2023 (1 year)
  - Test: 2024-2025 (2 years)

### Input Features
All 19 features listed above (temporal + spatial + historical)

### Output
- **Probability score**: 0.0 to 1.0 (e.g., 0.42 = 42% chance)
- **NOT** categorical ("Low", "Medium", "High") - that's done in response generator

### Evaluation Metrics
- **ROC-AUC** > 0.75 (target)
- Precision-Recall curve
- F1-Score
- Brier Score (calibration)

### Class Imbalance Handling
- `class_weight='balanced'` in XGBoost
- Already balanced via negative sampling (1:2 ratio)

---

## BERT Query Parser (Planned)

### Model Choice
- **Option 1** (recommended): `dslim/bert-base-NER` (pre-trained on named entities)
- **Option 2**: spaCy `en_core_web_trf` (faster inference)

### Extraction Tasks
1. **Location** (GPE entities): "Atlanta", "Miami, FL", "New York"
2. **Date** (DATE entities): "August 18, 2028", "next summer", "December 2027"
3. **Intent** (implicit): Storm prediction query

### Post-Processing
- **Date parsing**: Use `dateparser` for flexible formats ("next week" → actual date)
- **Location resolution**: Link to geocoder (city name → lat/lon)

### Example Flow
```
Input: "Will there be a storm in Atlanta on August 18, 2028?"
         ↓
BERT NER: {location: "Atlanta", date: "August 18, 2028"}
         ↓
Geocoder: {lat: 33.75, lon: -84.39}
         ↓
Date Parser: {datetime: 2028-08-18}
         ↓
Feature Gen: {month: 8, day_of_year: 231, grid_cell_id: "33.5_-84.5", ...}
         ↓
Model: {probability: 0.42}
         ↓
Response: "42% chance of storm activity in Atlanta on August 18, 2028..."
```

---

## Progress Tracker

### ✅ Phase 1: Data Preprocessing (COMPLETE - March 8)
- [x] Project structure created
- [x] Dependencies installed (pandas, numpy, pyarrow, etc.)
- [x] Data loader (`src/data/loader.py`)
- [x] Data cleaner (`src/data/cleaner.py`)
- [x] Feature engineer (`src/data/feature_engineer.py`)
- [x] End-to-end pipeline tested
- [x] Final dataset: 1.3M samples ready for training

**Deliverables**:
- `data/processed/storms_features.parquet` (1,308,915 records)
- `data/processed/feature_metadata.pkl`

---

### 🚧 Phase 2: Geocoding & NLP (NEXT - March 9-11)
- [ ] Install NLP dependencies (transformers, torch, spacy, dateparser)
- [ ] Build geocoding service (`src/nlp/geocoder.py`)
  - Extract unique locations from NOAA data
  - Create city → coordinates mapping
  - Add fuzzy matching for misspellings
- [ ] Implement BERT query parser (`src/nlp/query_parser.py`)
  - Load BERT NER model
  - Extract location and date entities
  - Handle edge cases (ambiguous locations)
- [ ] Create entity resolver (`src/nlp/entity_resolver.py`)
  - Link extracted entities to geocoder
  - Normalize dates to standard format

**Estimated Time**: 2-3 days
**Deliverables**:
- `data/geocoding/us_cities.json`
- Working query parser with 90%+ accuracy on test queries

---

### 🚧 Phase 3: Model Training (March 12-14)
- [ ] Install ML dependencies (scikit-learn, xgboost)
- [ ] Implement trainer (`src/models/trainer.py`)
  - Load feature-engineered data
  - Temporal train/val/test split
  - Train XGBoost classifier
  - Hyperparameter tuning (GridSearchCV)
  - Model evaluation (ROC-AUC, F1, Brier Score)
  - Probability calibration
- [ ] Implement predictor (`src/models/predictor.py`)
  - Load trained model
  - Feature validation
  - Inference pipeline
- [ ] Create training notebook (`notebooks/02_model_training.ipynb`)
  - Experiments and feature importance analysis

**Estimated Time**: 2-3 days
**Deliverables**:
- `models/storm_predictor_v1.pkl` (trained model with ROC-AUC > 0.75)
- Model performance report

---

### 🚧 Phase 4: Chatbot Integration (March 15-17)
- [ ] Implement orchestrator (`src/chatbot/orchestrator.py`)
  - `process_query()` function
  - Connect all components (parser → geocoder → predictor)
  - Error handling (unknown cities, invalid dates)
- [ ] Implement response generator (`src/chatbot/response_generator.py`)
  - Convert probability to risk level
  - Natural language templates
  - Add explanations (seasonal context)
- [ ] Integration testing

**Estimated Time**: 2-3 days
**Deliverables**:
- Working end-to-end pipeline from query to response

---

### 🚧 Phase 5: User Interface (March 18-19)
- [ ] Install UI dependencies (gradio)
- [ ] Implement Gradio app (`src/interfaces/gradio_app.py`)
  - Input: Text query
  - Output: Probability + Explanation
  - Add examples and instructions
- [ ] Optional: CLI tool (`src/interfaces/cli.py`)
- [ ] Local testing

**Estimated Time**: 1-2 days
**Deliverables**:
- Working Gradio web UI accessible at `http://localhost:7860`

---

### 🚧 Phase 6: Testing & Documentation (March 20)
- [ ] Create test suite (`tests/`)
  - Unit tests for each module
  - Integration tests
  - End-to-end tests
- [ ] Update documentation
  - Final README.md
  - Model card (`docs/MODEL.md`)
  - Usage examples
- [ ] Final demo and polish

**Estimated Time**: 1 day
**Deliverables**:
- Complete, tested, documented project ready for presentation

---

## Timeline to March 20

| Date | Phase | Focus |
|------|-------|-------|
| **March 8** ✅ | 1 | Data preprocessing (DONE) |
| **March 9-11** 🚧 | 2 | Geocoding + NLP parser |
| **March 12-14** 🚧 | 3 | Model training |
| **March 15-17** 🚧 | 4 | Chatbot orchestrator |
| **March 18-19** 🚧 | 5 | Gradio UI |
| **March 20** 🎯 | 6 | Testing & final polish |

**Status**: On track! 📅

---

## Daily Workflow

When you start each day:

1. **Read this CLAUDE.md** - I'll understand where we are
2. **Check the Progress Tracker** - See what's next
3. **Pick up from the current phase** - Continue building
4. **Update this file** - Mark tasks complete as we finish them

---

## Important Notes

### Data Characteristics
- **No separate locations files needed** - BEGIN_LAT/BEGIN_LON already in details CSVs
- **Large files** - Each CSV is 50-70 MB, use chunked reading if needed
- **Missing coordinates** - 38% of records have invalid (0,0) or out-of-bounds coords (already filtered)

### Model Assumptions
- **Future extrapolation** - We assume historical patterns continue to 2028
- **Granularity** - Predictions are ~50-mile grid level, not street-level
- **Not real-time** - Based on historical patterns, not current weather conditions

### Technical Decisions
- **Grid size**: 0.5° (balance between granularity and data sparsity)
- **Negative sampling ratio**: 1:2 (more realistic than 1:1)
- **No year feature** - Use cyclic month/day features to enable future prediction
- **XGBoost over Random Forest** - Better performance, prevents overfitting

---

## Coding Conventions

1. **Clear function names and docstrings** - Every function should explain what it does
2. **Logging** - Use `loguru` to print progress messages
3. **Modularity** - Each script should be runnable independently
4. **Save intermediates** - Don't re-run expensive operations (save to parquet/pkl)
5. **Error handling** - Graceful handling of NaN, missing data, edge cases
6. **Type hints** - Use Python type annotations where helpful

---

## Known Limitations

1. **Future extrapolation** - Predicting 2028 based on 2015-2025 assumes climate patterns remain stable
2. **County-level granularity** - Predictions are regional, not street-address specific
3. **Not a weather forecast** - Shows historical risk, not real-time meteorological prediction
4. **Class imbalance** - More no-storm days than storm days (handled via sampling/weighting)
5. **Cold start problem** - New locations with no historical data will get poor predictions

---

## Success Criteria

### Technical
- [x] Data pipeline processes 700k+ records successfully
- [ ] Model achieves ROC-AUC > 0.75 on test set
- [ ] Query parser extracts location/date with 90%+ accuracy
- [ ] End-to-end response time < 2 seconds
- [ ] Graceful error handling for edge cases

### User Experience
- [ ] User can type natural language queries
- [ ] System returns clear probability + explanation
- [ ] Web UI is intuitive and responsive
- [ ] System works for major US cities

---

## Resources

- **Plan file**: `/Users/pavanbobba/.claude/plans/delegated-sprouting-quill.md`
- **NOAA Data**: https://www.ncdc.noaa.gov/stormevents/
- **BERT Models**: https://huggingface.co/dslim/bert-base-NER
- **XGBoost Docs**: https://xgboost.readthedocs.io/

---

## Questions for Next Session?

When you come back tomorrow (or next session), you can ask:
- "What should we work on today?" (I'll check this file and suggest next steps)
- "Let's continue with Phase 2" (I'll start geocoding/NLP work)
- "Show me the project status" (I'll read this file and summarize)

---

**Last Updated**: March 8, 2026 by Claude
**Next Update**: After completing Phase 2 (Geocoding + NLP)
