SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean FORCE
.NOTPARALLEL:

PRIMARY_OUTPUT = ../output/MMB_reg_format.dta

SECONDARY_OUTPUTS = ../output/MMB_IRF_format.dta \
	../output/MMB_IRF_format.csv \
	../output/MMB_IRF_format_codebook.txt \
	../output/MMB_IRF_format_full.dta \
	../output/MMB_IRF_format_full_codebook.txt \
	../output/MMB_reg_format.xlsx \
	../output/MMB_reg_format_codebook.txt \
	../output/rhs.dta \
	../output/lhs_20.dta \
	../output/lhs_40.dta \
	../output/lhs_60.dta \
	../output/sacratios_20.dta \
	../output/sacratios_40.dta \
	../output/sacratios_60.dta \
	../output/parity_report.txt

OUTPUTS = $(PRIMARY_OUTPUT) $(SECONDARY_OUTPUTS)

all: $(OUTPUTS)

../input ../output:
	mkdir -p $@

FORCE:

../../import_mmb_legacy_data/output/responses: FORCE
	$(MAKE) --no-print-directory -C ../../import_mmb_legacy_data/code ../output/responses
	test -e $@

../../import_mmb_legacy_data/output/sacratios_csv: FORCE
	$(MAKE) --no-print-directory -C ../../import_mmb_legacy_data/code ../output/sacratios_csv
	test -e $@

../../import_mmb_legacy_data/output/bob_var_irfs.csv: FORCE
	$(MAKE) --no-print-directory -C ../../import_mmb_legacy_data/code ../output/bob_var_irfs.csv
	test -f $@

../../classifying_v2/output/Model_Characteristics_corrections_llm.xlsx: FORCE
	$(MAKE) --no-print-directory -C ../../classifying_v2/code corrections-workbook
	test -f $@

../input/responses: | ../../import_mmb_legacy_data/output/responses ../input
	ln -s ../../import_mmb_legacy_data/output/responses $@

../input/sacratios_csv: | ../../import_mmb_legacy_data/output/sacratios_csv ../input
	ln -s ../../import_mmb_legacy_data/output/sacratios_csv $@

../input/Model_Characteristics_corrections_llm.xlsx: | ../../classifying_v2/output/Model_Characteristics_corrections_llm.xlsx ../input
	ln -s ../../classifying_v2/output/Model_Characteristics_corrections_llm.xlsx $@

../input/bob_var_irfs.csv: | ../../import_mmb_legacy_data/output/bob_var_irfs.csv ../input
	ln -s ../../import_mmb_legacy_data/output/bob_var_irfs.csv $@

$(PRIMARY_OUTPUT): build_analysis_dataset.py ../input/responses ../input/sacratios_csv ../input/Model_Characteristics_corrections_llm.xlsx ../input/bob_var_irfs.csv ../../../../config/params.yaml | ../output
	$(PYTHON) build_analysis_dataset.py
	test -f $(PRIMARY_OUTPUT)
	test -f ../output/MMB_IRF_format.dta
	test -f ../output/MMB_IRF_format.csv
	test -f ../output/MMB_IRF_format_codebook.txt
	test -f ../output/MMB_IRF_format_full.dta
	test -f ../output/MMB_IRF_format_full_codebook.txt
	test -f ../output/MMB_reg_format.xlsx
	test -f ../output/MMB_reg_format_codebook.txt
	test -f ../output/rhs.dta
	test -f ../output/lhs_20.dta
	test -f ../output/lhs_40.dta
	test -f ../output/lhs_60.dta
	test -f ../output/sacratios_20.dta
	test -f ../output/sacratios_40.dta
	test -f ../output/sacratios_60.dta
	test -f ../output/parity_report.txt

$(SECONDARY_OUTPUTS): $(PRIMARY_OUTPUT)
	test -f $@

clean:
	rm -f $(OUTPUTS)
	rm -f '../output/~$$MMB_reg_format.xlsx'
	find ../input -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
