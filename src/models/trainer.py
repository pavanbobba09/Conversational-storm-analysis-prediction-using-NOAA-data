"""
Model Trainer Module
Trains XGBoost classifier on historical storm patterns
"""
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from loguru import logger
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    f1_score,
    classification_report,
    confusion_matrix,
    brier_score_loss
)
from sklearn.calibration import CalibratedClassifierCV
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns


class StormModelTrainer:
    """
    Trains and evaluates storm prediction model
    """

    def __init__(self, data_path: str):
        """
        Initialize trainer

        Args:
            data_path: Path to feature-engineered parquet file
        """
        self.data_path = Path(data_path)
        self.model = None
        self.calibrated_model = None
        self.feature_columns = None
        self.train_data = None
        self.val_data = None
        self.test_data = None

        logger.info(f"Initialized StormModelTrainer with data: {self.data_path}")

    def load_data(self):
        """
        Load feature-engineered data
        """
        logger.info("Loading feature-engineered data...")
        df = pd.read_parquet(self.data_path)
        logger.info(f"Loaded {len(df):,} samples with {len(df.columns)} columns")

        return df

    def temporal_split(self, df: pd.DataFrame):
        """
        Split data temporally to avoid data leakage

        Args:
            df: Full dataset

        Returns:
            Train, validation, test splits
        """
        logger.info("Splitting data temporally...")

        # Ensure we have year column
        if 'year' not in df.columns and 'BEGIN_DATE_TIME' in df.columns:
            df['year'] = pd.to_datetime(df['BEGIN_DATE_TIME']).dt.year

        # Temporal split: 2015-2022 (train), 2023 (val), 2024-2025 (test)
        train_df = df[df['year'] <= 2022].copy()
        val_df = df[df['year'] == 2023].copy()
        test_df = df[df['year'] >= 2024].copy()

        logger.info(f"Train: {len(train_df):,} samples (2015-2022)")
        logger.info(f"Validation: {len(val_df):,} samples (2023)")
        logger.info(f"Test: {len(test_df):,} samples (2024-2025)")

        # Check class distribution
        logger.info(f"Train positive class: {(train_df['storm_occurred']==1).sum():,} ({(train_df['storm_occurred']==1).sum()/len(train_df)*100:.1f}%)")
        logger.info(f"Val positive class: {(val_df['storm_occurred']==1).sum():,} ({(val_df['storm_occurred']==1).sum()/len(val_df)*100:.1f}%)")
        logger.info(f"Test positive class: {(test_df['storm_occurred']==1).sum():,} ({(test_df['storm_occurred']==1).sum()/len(test_df)*100:.1f}%)")

        self.train_data = train_df
        self.val_data = val_df
        self.test_data = test_df

        return train_df, val_df, test_df

    def select_features(self, df: pd.DataFrame):
        """
        Select features for model training

        Args:
            df: DataFrame with all columns

        Returns:
            List of feature column names
        """
        # Features to use (temporal + spatial + historical)
        feature_cols = [
            # Temporal features
            'month', 'day_of_year', 'week_of_year', 'day_of_week',
            'season_encoded', 'is_summer_peak', 'is_tornado_season', 'is_hurricane_season',
            'month_sin', 'month_cos', 'day_of_year_sin', 'day_of_year_cos',

            # Spatial features
            'lat_rounded', 'lon_rounded',

            # Historical features
            'storms_location_month_avg_per_year', 'historical_storm_probability',
            'most_common_event_encoded'
        ]

        # Filter to only include columns that exist in dataframe
        available_features = [col for col in feature_cols if col in df.columns]

        logger.info(f"Selected {len(available_features)} features for training:")
        logger.info(f"  {', '.join(available_features)}")

        self.feature_columns = available_features
        return available_features

    def train_model(self, train_df: pd.DataFrame, val_df: pd.DataFrame):
        """
        Train XGBoost model

        Args:
            train_df: Training data
            val_df: Validation data

        Returns:
            Trained model
        """
        logger.info("Training XGBoost model...")

        # Prepare data
        X_train = train_df[self.feature_columns]
        y_train = train_df['storm_occurred']
        X_val = val_df[self.feature_columns]
        y_val = val_df['storm_occurred']

        # Calculate scale_pos_weight for class imbalance
        n_negative = (y_train == 0).sum()
        n_positive = (y_train == 1).sum()
        scale_pos_weight = n_negative / n_positive

        logger.info(f"Class imbalance ratio: {scale_pos_weight:.2f}")

        # Initialize XGBoost model
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            eval_metric='logloss',
            random_state=42,
            n_jobs=-1,
            verbosity=1
        )

        # Train model with early stopping
        logger.info("Training with early stopping...")
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=10
        )

        logger.info(f"Training complete. Best iteration: {model.best_iteration}")

        self.model = model
        return model

    def evaluate_model(self, model, X, y, dataset_name="Test"):
        """
        Evaluate model performance

        Args:
            model: Trained model
            X: Features
            y: True labels
            dataset_name: Name of dataset (for logging)

        Returns:
            Dictionary of metrics
        """
        logger.info(f"\n=== Evaluating on {dataset_name} Set ===")

        # Predictions
        y_pred_proba = model.predict_proba(X)[:, 1]
        y_pred = (y_pred_proba >= 0.5).astype(int)

        # Calculate metrics
        roc_auc = roc_auc_score(y, y_pred_proba)
        f1 = f1_score(y, y_pred)
        brier = brier_score_loss(y, y_pred_proba)

        logger.info(f"ROC-AUC Score: {roc_auc:.4f}")
        logger.info(f"F1 Score: {f1:.4f}")
        logger.info(f"Brier Score: {brier:.4f}")

        # Classification report
        logger.info("\nClassification Report:")
        logger.info(f"\n{classification_report(y, y_pred, target_names=['No Storm', 'Storm'])}")

        # Confusion matrix
        cm = confusion_matrix(y, y_pred)
        logger.info("\nConfusion Matrix:")
        logger.info(f"  True Negatives: {cm[0,0]:,}")
        logger.info(f"  False Positives: {cm[0,1]:,}")
        logger.info(f"  False Negatives: {cm[1,0]:,}")
        logger.info(f"  True Positives: {cm[1,1]:,}")

        metrics = {
            'roc_auc': roc_auc,
            'f1_score': f1,
            'brier_score': brier,
            'confusion_matrix': cm
        }

        return metrics

    def calibrate_model(self, model, X_val, y_val):
        """
        Calibrate model probabilities

        Args:
            model: Trained model
            X_val: Validation features
            y_val: Validation labels

        Returns:
            Calibrated model
        """
        logger.info("Calibrating model probabilities...")

        calibrated = CalibratedClassifierCV(
            model,
            method='sigmoid',
            cv='prefit'
        )

        calibrated.fit(X_val, y_val)

        logger.info("Calibration complete")

        self.calibrated_model = calibrated
        return calibrated

    def plot_feature_importance(self, model, output_path: str = None):
        """
        Plot feature importance

        Args:
            model: Trained XGBoost model
            output_path: Optional path to save plot
        """
        logger.info("Generating feature importance plot...")

        # Get feature importance
        importance = model.feature_importances_
        feature_names = self.feature_columns

        # Create dataframe
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        # Plot
        plt.figure(figsize=(10, 8))
        sns.barplot(data=importance_df.head(15), x='importance', y='feature')
        plt.title('Top 15 Feature Importances')
        plt.xlabel('Importance')
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved feature importance plot to: {output_path}")
        else:
            plt.show()

        plt.close()

        # Log top features
        logger.info("\nTop 10 Most Important Features:")
        for idx, row in importance_df.head(10).iterrows():
            logger.info(f"  {row['feature']:40s}: {row['importance']:.4f}")

    def save_model(self, output_path: str):
        """
        Save trained model and metadata

        Args:
            output_path: Path to save model
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Package model with metadata
        model_package = {
            'model': self.calibrated_model if self.calibrated_model else self.model,
            'feature_columns': self.feature_columns,
            'is_calibrated': self.calibrated_model is not None
        }

        joblib.dump(model_package, output_path)
        logger.info(f"Saved model to: {output_path}")


def main():
    """
    Train storm prediction model
    """
    logger.info("=== STORM PREDICTION MODEL TRAINING ===\n")

    # Paths
    data_path = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/data/processed/storms_features.parquet"
    model_output = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/models/storm_predictor_v1.pkl"

    # Initialize trainer
    trainer = StormModelTrainer(data_path)

    # Load data
    df = trainer.load_data()

    # Temporal split
    train_df, val_df, test_df = trainer.temporal_split(df)

    # Select features
    trainer.select_features(train_df)

    # Train model
    model = trainer.train_model(train_df, val_df)

    # Evaluate on validation set
    val_metrics = trainer.evaluate_model(
        model,
        val_df[trainer.feature_columns],
        val_df['storm_occurred'],
        dataset_name="Validation"
    )

    # Evaluate on test set
    test_metrics = trainer.evaluate_model(
        model,
        test_df[trainer.feature_columns],
        test_df['storm_occurred'],
        dataset_name="Test"
    )

    # Calibrate model
    calibrated_model = trainer.calibrate_model(
        model,
        val_df[trainer.feature_columns],
        val_df['storm_occurred']
    )

    # Evaluate calibrated model on test set
    logger.info("\n=== Calibrated Model Performance ===")
    calibrated_metrics = trainer.evaluate_model(
        calibrated_model,
        test_df[trainer.feature_columns],
        test_df['storm_occurred'],
        dataset_name="Test (Calibrated)"
    )

    # Plot feature importance
    plot_output = "/Users/pavanbobba/Documents/master's_Project/Conversational-storm-analysis-prediction-using-NOAA-data/models/feature_importance.png"
    trainer.plot_feature_importance(model, output_path=plot_output)

    # Save model
    trainer.save_model(model_output)

    # Final summary
    logger.info("\n=== TRAINING COMPLETE ===")
    logger.info(f"Test ROC-AUC: {test_metrics['roc_auc']:.4f}")
    logger.info(f"Test F1-Score: {test_metrics['f1_score']:.4f}")
    logger.info(f"Calibrated Test ROC-AUC: {calibrated_metrics['roc_auc']:.4f}")
    logger.info(f"Model saved to: {model_output}")

    return trainer


if __name__ == "__main__":
    main()
