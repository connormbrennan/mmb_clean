SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

all: ../output/responses ../output/sacratios_csv ../output/sacratios_json ../output/model_characteristics.xlsx ../output/model_characteristics_codebook.txt ../output/bob_var_irfs.csv ../output/stationary_var_data.csv ../output/classifications.csv ../output/models ../output/models_of_interest ../output/user_defined_rules ../output/source_inventory.txt

../output ../input:
	mkdir -p $@

../output/responses: ../../../../legacy/mmb_upgraded/data/raw/responses | ../output
	ln -s ../../../../legacy/mmb_upgraded/data/raw/responses $@

../output/sacratios_csv: ../../../../legacy/mmb_upgraded/data/raw/sacratios/csv | ../output
	ln -s ../../../../legacy/mmb_upgraded/data/raw/sacratios/csv $@

../output/sacratios_json: ../../../../legacy/mmb_upgraded/data/raw/sacratios/json | ../output
	ln -s ../../../../legacy/mmb_upgraded/data/raw/sacratios/json $@

../output/model_characteristics.xlsx: ../../../../legacy/mmb_upgraded/data/raw/Model_Characteristics_corrections.xlsx | ../output
	ln -s ../../../../legacy/mmb_upgraded/data/raw/Model_Characteristics_corrections.xlsx $@

../output/bob_var_irfs.csv: ../../../../legacy/mmb_upgraded/data/raw/Bob_IRFS_63Q1_07Q4.csv | ../output
	ln -s ../../../../legacy/mmb_upgraded/data/raw/Bob_IRFS_63Q1_07Q4.csv $@

../output/stationary_var_data.csv: ../../../../legacy/mmb_upgraded/data/raw/stationaryvardata.csv | ../output
	ln -s ../../../../legacy/mmb_upgraded/data/raw/stationaryvardata.csv $@

../output/classifications.csv: ../../../../legacy/mmb_upgraded/data/classifications.csv | ../output
	ln -s ../../../../legacy/mmb_upgraded/data/classifications.csv $@

../output/models: ../../../../legacy/mmb_upgraded/models | ../output
	ln -s ../../../../legacy/mmb_upgraded/models $@

../output/models_of_interest: ../../../../legacy/mmb_upgraded/models-of-interest | ../output
	ln -s ../../../../legacy/mmb_upgraded/models-of-interest $@

../output/user_defined_rules: ../../../../legacy/mmb_upgraded/user_defined_rules | ../output
	ln -s ../../../../legacy/mmb_upgraded/user_defined_rules $@

../output/model_characteristics_codebook.txt ../output/source_inventory.txt: write_source_metadata.py ../output/model_characteristics.xlsx ../output/responses ../output/sacratios_csv ../output/sacratios_json ../output/bob_var_irfs.csv ../output/stationary_var_data.csv ../output/classifications.csv
	$(PYTHON) write_source_metadata.py

clean:
	find ../output -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
	rm -f ../output/model_characteristics_codebook.txt ../output/source_inventory.txt
