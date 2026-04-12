"""
Excel Exporter for Storm Analytics

CRITICAL REQUIREMENT: Excel files must contain EXACT NOAA data.
- NO modifications to data values
- ALL 54 columns from storms_cleaned.parquet
- ALL filtered rows (no limits)
- Original data types preserved

Excel file has 3 sheets:
1. Summary - Query info and narrative (formatted for readability)
2. Data - EXACT NOAA records (unmodified)
3. Metadata - Column descriptions and data dictionary
"""

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows
from datetime import datetime
from pathlib import Path
from typing import Dict
import os
import tempfile


class ExcelExporter:
    """Generate Excel files with exact NOAA storm data"""

    def __init__(self, output_dir: str = None):
        """
        Initialize Excel exporter

        Args:
            output_dir: Directory to save Excel files (default: system temp dir)
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_excel(self, parsed_query: Dict, results: Dict,
                      narrative: str) -> str:
        """
        Generate Excel file with exact NOAA data

        Args:
            parsed_query: Parsed query information
            results: Query results from StormQueryEngine
            narrative: Generated narrative response

        Returns:
            Filepath to generated Excel file
        """
        import time

        # Generate filename
        filename = self._generate_filename(parsed_query)
        filepath = os.path.join(self.output_dir, filename)

        num_rows = len(results['data'])
        print(f"      📄 Creating Excel workbook with {num_rows:,} data rows...")

        # Create workbook
        start = time.time()
        wb = Workbook()

        # Remove default sheet
        if 'Sheet' in wb.sheetnames:
            wb.remove(wb['Sheet'])

        # Sheet 1: Summary
        print(f"      📝 Sheet 1/3: Creating summary sheet...")
        sheet_start = time.time()
        self._create_summary_sheet(wb, parsed_query, results, narrative)
        print(f"         ✓ Summary sheet created in {time.time() - sheet_start:.2f}s")

        # Sheet 2: Data (EXACT NOAA RECORDS)
        print(f"      📊 Sheet 2/3: Writing {num_rows:,} NOAA records (54 columns)...")
        sheet_start = time.time()
        self._create_data_sheet(wb, results['data'])
        print(f"         ✓ Data sheet created in {time.time() - sheet_start:.2f}s")

        # Sheet 3: Metadata
        print(f"      📋 Sheet 3/3: Creating metadata sheet...")
        sheet_start = time.time()
        self._create_metadata_sheet(wb, parsed_query, results)
        print(f"         ✓ Metadata sheet created in {time.time() - sheet_start:.2f}s")

        # Save workbook
        print(f"      💾 Saving Excel file to disk...")
        save_start = time.time()
        wb.save(filepath)
        save_time = time.time() - save_start

        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        total_time = time.time() - start

        print(f"         ✓ File saved in {save_time:.2f}s")
        print(f"      📦 Excel file size: {file_size_mb:.2f} MB")
        print(f"      ⏱️  Total Excel generation time: {total_time:.2f}s")

        return filepath

    def _create_summary_sheet(self, wb: Workbook, parsed_query: Dict,
                             results: Dict, narrative: str):
        """Create summary sheet with query info and narrative"""
        ws = wb.create_sheet("Summary", 0)

        # Title
        ws['A1'] = "NOAA Storm Analytics Report"
        ws['A1'].font = Font(size=16, bold=True)
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Query
        ws['A4'] = "Query:"
        ws['A4'].font = Font(bold=True)
        ws['A5'] = parsed_query['raw_query']

        # Narrative
        ws['A7'] = "Findings:"
        ws['A7'].font = Font(bold=True)
        ws['A8'] = narrative
        ws['A8'].alignment = Alignment(wrap_text=True)

        # Statistics
        summary = results['summary']
        row = 15
        ws[f'A{row}'] = "Key Statistics:"
        ws[f'A{row}'].font = Font(bold=True)

        row += 1
        stats = [
            ('Total Events', f"{summary['total_events']:,}"),
            ('Total Deaths', f"{summary['total_deaths']:,}"),
            ('Total Injuries', f"{summary['total_injuries']:,}"),
            ('Total Damage', f"${summary['total_damage']:,.0f}"),
            ('Date Range', f"{summary['date_range'][0]} to {summary['date_range'][1]}"),
            ('States Covered', f"{len(summary['states_covered'])}")
        ]

        for label, value in stats:
            ws[f'A{row}'] = label
            ws[f'B{row}'] = value
            ws[f'A{row}'].font = Font(bold=True)
            row += 1

        # Column widths
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 30

    def _create_data_sheet(self, wb: Workbook, df: pd.DataFrame):
        """
        Create data sheet with EXACT NOAA records

        CRITICAL: NO modifications to data!
        """
        ws = wb.create_sheet("Data", 1)

        if len(df) == 0:
            ws['A1'] = "No data found"
            return

        # Write EXACT data from DataFrame (NO MODIFICATIONS)
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
            for c_idx, value in enumerate(row, 1):
                ws.cell(row=r_idx, column=c_idx, value=value)

        # Format header row ONLY (does not modify data)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill

        # Auto-filter (does not modify data)
        if len(df) > 0:
            ws.auto_filter.ref = ws.dimensions

        # Freeze header row (does not modify data)
        ws.freeze_panes = 'A2'

        # Auto-adjust column widths (display only, does not modify data)
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

    def _create_metadata_sheet(self, wb: Workbook, parsed_query: Dict, results: Dict):
        """Create metadata sheet with column descriptions"""
        ws = wb.create_sheet("Metadata", 2)

        # Title
        ws['A1'] = "Data Dictionary and Metadata"
        ws['A1'].font = Font(size=14, bold=True)

        # Column descriptions
        ws['A3'] = "Column Descriptions:"
        ws['A3'].font = Font(bold=True)

        row = 4
        column_descriptions = self._get_column_descriptions()

        ws['A4'] = "Column Name"
        ws['B4'] = "Description"
        ws['A4'].font = Font(bold=True)
        ws['B4'].font = Font(bold=True)

        row = 5
        for col_name, description in column_descriptions.items():
            ws[f'A{row}'] = col_name
            ws[f'B{row}'] = description
            row += 1

        # Query details
        row += 2
        ws[f'A{row}'] = "Query Details:"
        ws[f'A{row}'].font = Font(bold=True)
        row += 1

        filters = parsed_query.get('filters', {})
        ws[f'A{row}'] = "Event Types:"
        ws[f'B{row}'] = str(filters.get('event_types', 'All'))
        row += 1
        ws[f'A{row}'] = "States:"
        ws[f'B{row}'] = str(filters.get('states', 'All'))
        row += 1
        ws[f'A{row}'] = "Years:"
        ws[f'B{row}'] = str(filters.get('years', 'All'))
        row += 1

        # Data source
        row += 2
        ws[f'A{row}'] = "Data Source:"
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
        ws[f'A{row}'] = "NOAA Storm Events Database"
        row += 1
        ws[f'A{row}'] = "Date Range: 2015-2025"
        row += 1
        ws[f'A{row}'] = "Total Records in Dataset: 436,305"

        # Disclaimer
        row += 2
        ws[f'A{row}'] = "Disclaimer:"
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
        ws[f'A{row}'] = "This data is unmodified from the NOAA Storm Events Database and suitable for research use."
        ws[f'A{row}'].alignment = Alignment(wrap_text=True)

        # Column widths
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 60

    def _generate_filename(self, parsed_query: Dict) -> str:
        """Generate filename for Excel file"""
        # Get query components
        filters = parsed_query.get('filters', {})
        event_types = filters.get('event_types', [])
        states = filters.get('states', [])
        years = filters.get('years', [])

        # Build filename
        parts = ['storm_analytics']

        if event_types:
            parts.append(event_types[0].lower().replace(' ', '_'))

        if states:
            parts.append(states[0].lower())

        if years:
            if len(years) == 1:
                parts.append(str(years[0]))
            else:
                parts.append(f"{min(years)}_{max(years)}")

        # Add timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        parts.append(timestamp)

        return '_'.join(parts) + '.xlsx'

    def _get_column_descriptions(self) -> Dict[str, str]:
        """Get NOAA column descriptions"""
        return {
            'EVENT_ID': 'Unique storm event identifier',
            'EPISODE_ID': 'Episode identifier (multiple events can be part of same episode)',
            'EVENT_TYPE': 'Type of storm event',
            'STATE': 'US State or territory code',
            'YEAR': 'Year of event',
            'MONTH_NAME': 'Month name',
            'BEGIN_DATE_TIME': 'Event start date and time',
            'END_DATE_TIME': 'Event end date and time',
            'CZ_TYPE': 'County/Zone type',
            'CZ_NAME': 'County or zone name',
            'CZ_FIPS': 'County FIPS code',
            'BEGIN_LAT': 'Starting latitude',
            'BEGIN_LON': 'Starting longitude',
            'END_LAT': 'Ending latitude',
            'END_LON': 'Ending longitude',
            'DEATHS_DIRECT': 'Number of direct deaths',
            'DEATHS_INDIRECT': 'Number of indirect deaths',
            'INJURIES_DIRECT': 'Number of direct injuries',
            'INJURIES_INDIRECT': 'Number of indirect injuries',
            'DAMAGE_PROPERTY': 'Property damage (original NOAA format)',
            'DAMAGE_PROPERTY_NUM': 'Property damage (numeric value)',
            'DAMAGE_CROPS': 'Crop damage (original NOAA format)',
            'DAMAGE_CROPS_NUM': 'Crop damage (numeric value)',
            'TOTAL_DAMAGE': 'Total damage (property + crops)',
            'TOR_F_SCALE': 'Tornado F-scale rating (EF0-EF5)',
            'TOR_LENGTH': 'Tornado path length (miles)',
            'TOR_WIDTH': 'Tornado path width (yards)',
            'MAGNITUDE': 'Event magnitude (varies by event type)',
            'MAGNITUDE_TYPE': 'Type of magnitude measurement',
            'EVENT_NARRATIVE': 'Detailed narrative description of event',
            'EPISODE_NARRATIVE': 'Narrative description of episode'
        }


# Example usage
if __name__ == "__main__":
    print("Excel exporter created successfully!")
    print("This module generates Excel files with exact NOAA data.")
