# Storm Forecasting Chatbot with NOAA Data

A conversational AI system that predicts storm likelihood for any US location and future date based on historical NOAA storm data (2015-2025).

## Project Overview

This chatbot combines:
- **BERT-based NLP** for understanding natural language queries
- **Machine Learning** (XGBoost) for predicting storm probability based on historical patterns
- **NOAA Storm Events Database** (2015-2025, 707k+ events)

### Example Usage
```
User: "Will there be a storm in Atlanta on August 18, 2028?"
Bot:  "Based on historical patterns, there is a 42% chance of storm activity
       in Atlanta on August 18, 2028. This represents a medium risk period.
       August is typically peak storm season in the Southeast."
```

## Project Status

### ✅ Completed: Data Preprocessing (Phase 1)

The data preprocessing pipeline is fully implemented and tested:

1. **Data Loading** - Merged 11 years of NOAA CSV files (707,100 events)
2. **Data Cleaning** - Validated coordinates, parsed damage values, handled missing data
3. **Feature Engineering** - Created temporal, spatial, and historical features

#### Data Pipeline Results

| Stage | Records | Description |
|-------|---------|-------------|
| Raw Data | 707,100 | 11 CSV files (2015-2025) loaded and merged |
| After Cleaning | 436,305 | Removed 38.3% with invalid coordinates |
| After Feature Engineering | 1,308,915 | Added 872,610 negative samples (no-storm days) |

#### Features Created

- **Temporal (12 features)**: month, day_of_year, season, cyclic encodings, peak season indicators
- **Spatial (4 features)**: lat/lon coordinates, 0.5° grid cells (3,665 unique locations)
- **Historical (3 features)**: storm frequency per location-month, baseline probability
- **Target**: storm_occurred (binary: 0 or 1)

#### Data Insights

- **Date Range**: April 2015 - October 2025 (10.5 years)
- **Geographic Coverage**: 69 US states/territories, 3,665 grid cells
- **Event Types**: 55 different storm types (Thunderstorm Wind, Hail, Flash Flood most common)
- **Total Damage**: $128 billion
- **Casualties**: 2,860 deaths, 10,196 injuries

### 🚧 Next Steps: Model Training & Chatbot (Phases 2-8)

Remaining work (see [implementation plan](/Users/pavanbobba/.claude/plans/delegated-sprouting-quill.md)):

2. **Geocoding Service** - Map city names to coordinates
3. **NLP Query Parser** - BERT-based entity extraction
4. **Model Training** - XGBoost classifier on historical patterns
5. **Prediction Service** - Inference pipeline
6. **Chatbot Orchestrator** - End-to-end query processing
7. **Gradio Web UI** - User interface
8. **Testing & Deployment**

## Project Structure

```
Conversational-storm-analysis-prediction-using-NOAA-data/
├── data/
│   ├── processed/
│   │   ├── storms_raw.parquet           (707,100 records)
│   │   ├── storms_cleaned.parquet       (436,305 records)
│   │   ├── storms_features.parquet      (1,308,915 records)
│   │   └── feature_metadata.pkl
│   └── geocoding/
├── dataset/
│   └── StormEvents_details-*.csv        (11 CSV files, 2015-2025)
├── models/                               (trained models will go here)
├── src/
│   ├── data/
│   │   ├── loader.py              ✅ Load and merge CSVs
│   │   ├── cleaner.py             ✅ Data cleaning
│   │   └── feature_engineer.py    ✅ Feature extraction
│   ├── nlp/                       🚧 (to be implemented)
│   ├── models/                    🚧 (to be implemented)
│   ├── chatbot/                   🚧 (to be implemented)
│   └── interfaces/                🚧 (to be implemented)
├── notebooks/                     (for data exploration)
├── tests/                         (unit and integration tests)
├── requirements.txt               ✅ Python dependencies
├── .gitignore                     ✅ Git ignore rules
└── README.md                      ✅ This file
```

## Setup Instructions

### Prerequisites
- Python 3.9+
- Virtual environment (already set up in `venv/`)

### Installation

1. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Data Pipeline

The data preprocessing pipeline has already been run, but you can re-run it:

1. **Load raw data**:
   ```bash
   python src/data/loader.py
   ```
   Output: `data/processed/storms_raw.parquet`

2. **Clean data**:
   ```bash
   python src/data/cleaner.py
   ```
   Output: `data/processed/storms_cleaned.parquet`

3. **Engineer features**:
   ```bash
   python src/data/feature_engineer.py
   ```
   Output: `data/processed/storms_features.parquet`

## Data Sources

- **NOAA Storm Events Database**: https://www.ncdc.noaa.gov/stormevents/
- Coverage: 2015-2025
- Data includes: Event type, location, time, damages, casualties, narratives

## Technical Details

### Data Cleaning
- Removes records with invalid coordinates (outside US bounds or placeholder values)
- Parses damage values from strings ("10K", "5.0M") to numeric
- Converts dates to datetime objects
- Handles missing values (fills numeric with 0, imputes MAGNITUDE by event type)

### Feature Engineering
- **Spatial Grid**: 0.5° × 0.5° cells (~50 miles) for location-based features
- **Temporal Features**: Cyclic encoding for month/day (preserves Dec→Jan continuity)
- **Historical Aggregation**: Storm frequency per location-month across all years
- **Negative Sampling**: Generates 2× negative samples (no-storm days) for balanced training

### Modeling Approach (Planned)
- **Algorithm**: XGBoost classifier
- **Training Split**: 2015-2022 (train), 2023 (validation), 2024-2025 (test)
- **Target Metric**: ROC-AUC > 0.75
- **Key Challenge**: Predicting future dates (2028) based on historical patterns (2015-2025)

## Dependencies

Core libraries:
- **Data**: pandas, numpy, pyarrow
- **ML**: scikit-learn, xgboost (to be installed)
- **NLP**: transformers, torch, spacy (to be installed)
- **UI**: gradio (to be installed)
- **Utilities**: tqdm, joblib, loguru

See [requirements.txt](requirements.txt) for complete list.

## Known Limitations

1. **Future Extrapolation**: Predictions for future years assume historical patterns continue
2. **Granularity**: Predictions are at ~50-mile grid cell level, not street-level
3. **Not Real-Time**: Based on historical patterns, not real-time meteorological data
4. **Class Imbalance**: Many more no-storm days than storm days (handled via sampling/weighting)

## Contributing

This is a master's project. For questions or issues, please contact the project maintainer.

## License

Educational use only.

## Acknowledgments

- NOAA National Centers for Environmental Information for Storm Events Database
- HuggingFace for BERT models
- XGBoost developers for the gradient boosting framework
