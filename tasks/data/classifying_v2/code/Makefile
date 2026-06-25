SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all run status corrections-workbook clean-output reset clean

all: run

../input ../output:
	mkdir -p $@

../input/Model_Characteristics_corrections.xlsx: ../../classifying/output/Model_Characteristics_corrections.xlsx | ../input
	ln -s ../../classifying/output/Model_Characteristics_corrections.xlsx $@

../input/mmb_model_paper_map.md: ../../classifying/output/mmb_model_paper_map.md | ../input
	ln -s ../../classifying/output/mmb_model_paper_map.md $@

../input/papers: ../../../../SamplePapers | ../input
	ln -s ../../../../SamplePapers $@

run: audit_model_characteristics_with_gemini.py ../input/Model_Characteristics_corrections.xlsx ../input/mmb_model_paper_map.md ../input/model_paper_files.csv ../input/papers ../../../../config/params.yaml | ../output
	CLASSIFYING_V2_STAGE=run $(PYTHON) audit_model_characteristics_with_gemini.py

status: audit_model_characteristics_with_gemini.py ../input/Model_Characteristics_corrections.xlsx ../input/mmb_model_paper_map.md ../input/model_paper_files.csv ../input/papers ../../../../config/params.yaml | ../output
	CLASSIFYING_V2_STAGE=status $(PYTHON) audit_model_characteristics_with_gemini.py

corrections-workbook: ../output/Model_Characteristics_corrections_llm.xlsx ../output/Model_Characteristics_corrections_llm_summary.txt

../output/Model_Characteristics_corrections_llm.xlsx ../output/Model_Characteristics_corrections_llm_summary.txt: apply_llm_corrections_to_workbook.py ../input/Model_Characteristics_corrections.xlsx ../output/model_audit.csv | ../output
	$(PYTHON) apply_llm_corrections_to_workbook.py

clean-output reset:
	rm -f ../output/model_audit.csv
	rm -f ../output/gemini_all_answers.csv
	rm -f ../output/gemini_raw_responses.jsonl
	rm -f ../output/cache_manifest.csv
	rm -f ../output/progress.log
	rm -f ../output/classifying_v2_run_summary.txt
	rm -f ../output/Model_Characteristics_corrections_llm.xlsx
	rm -f ../output/Model_Characteristics_corrections_llm_summary.txt

clean: clean-output
	find ../input -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
