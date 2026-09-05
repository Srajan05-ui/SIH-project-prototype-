$ErrorActionPreference = "Stop"
Write-Host "Activating venv..."
.\.venv\Scripts\Activate.ps1

Write-Host "Running Tier 1 (Google Flights)..."
python collector_tier1.py

Write-Host "Running Tier 0 (DGCA Mock)..."
python collector_tier0_dgca.py

Write-Host "Running Tier 2 (Airline Direct Mock)..."
python collector_tier2_airline.py

Write-Host "Running Stage 3 (Cleaning)..."
python cleaning.py

Write-Host "Running Stage 4 (Index Calc)..."
python index_calc.py

Write-Host "Running Stage 5 (Anomaly Detection) - testing injection..."
python anomaly.py --inject-test-anomaly

Write-Host "All batch jobs finished."
