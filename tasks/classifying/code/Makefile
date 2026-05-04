all: ../output/consensus_economics_inflation_expectations_panel.csv ../output/consensus_economics_inflation_expectations_panel.parquet ../output/consensus_economics_inflation_forecast_vintages.csv ../output/consensus_economics_series_metadata.csv ../output/consensus_economics_inflation_expectations_panel_codebook.txt ../output/consensus_economics_wrds_availability_audit.txt

../output/consensus_economics_inflation_expectations_panel.csv ../output/consensus_economics_inflation_expectations_panel.parquet ../output/consensus_economics_inflation_forecast_vintages.csv ../output/consensus_economics_series_metadata.csv ../output/consensus_economics_inflation_expectations_panel_codebook.txt ../output/consensus_economics_wrds_availability_audit.txt: build_consensus_economics_inflation_expectations.py ../config/params.yaml | ../output
	python3 build_consensus_economics_inflation_expectations.py

../output:
	mkdir -p ../output
