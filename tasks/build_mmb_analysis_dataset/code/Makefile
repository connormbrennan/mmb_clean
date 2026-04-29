SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

OUTPUTS = ../output/MMB_IRF_format.dta \
	../output/MMB_IRF_format.csv \
	../output/MMB_IRF_format_codebook.txt \
	../output/MMB_IRF_format_full.dta \
	../output/MMB_IRF_format_full_codebook.txt \
	../output/MMB_reg_format.dta \
	../output/MMB_reg_format.xlsx \
	../output/MMB_reg_format_codebook.txt \
	../output/parity_report.txt

all: $(OUTPUTS)

../input ../output:
	mkdir -p $@

../input/responses: ../../import_mmb_legacy_data/output/responses | ../input
	ln -s ../../import_mmb_legacy_data/output/responses $@

../input/sacratios_csv: ../../import_mmb_legacy_data/output/sacratios_csv | ../input
	ln -s ../../import_mmb_legacy_data/output/sacratios_csv $@

../input/model_characteristics.xlsx: ../../import_mmb_legacy_data/output/model_characteristics.xlsx | ../input
	ln -s ../../import_mmb_legacy_data/output/model_characteristics.xlsx $@

../input/bob_var_irfs.csv: ../../import_mmb_legacy_data/output/bob_var_irfs.csv | ../input
	ln -s ../../import_mmb_legacy_data/output/bob_var_irfs.csv $@

$(OUTPUTS): build_analysis_dataset.py ../input/responses ../input/sacratios_csv ../input/model_characteristics.xlsx ../input/bob_var_irfs.csv ../../../config/params.yaml | ../output
	$(PYTHON) build_analysis_dataset.py

clean:
	rm -f $(OUTPUTS)
	rm -f ../output/rhs.dta ../output/lhs_*.dta ../output/sacratios_*.dta
	find ../input -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
