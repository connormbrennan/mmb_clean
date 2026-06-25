SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean FORCE build
.NOTPARALLEL:

UPSTREAM_MMB_REG := ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta

OUTPUTS := \
	../output/nonmodel_attributes_full_sample.txt \
	../output/nonmodel_attributes_estimated_models.txt \
	../output/table9_nonmodel_attributes_full_sample.tex \
	../output/table9_nonmodel_attributes_full_sample.csv \
	../output/table9_nonmodel_attributes_estimated_models.tex \
	../output/table9_nonmodel_attributes_estimated_models.csv \
	../output/table9_nonmodel_attributes_full_sample_citation_weighted.tex \
	../output/table9_nonmodel_attributes_full_sample_citation_weighted.csv \
	../output/table9_nonmodel_attributes_estimated_models_citation_weighted.tex \
	../output/table9_nonmodel_attributes_estimated_models_citation_weighted.csv \
	../output/manifest.csv

all: build

clean:
	mkdir -p ../input ../output
	rm -f $(OUTPUTS)
	find ../input -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
	touch ../input/.gitkeep ../output/.gitkeep

FORCE:

upstream_mmb_analysis_dataset: FORCE
	$(MAKE) --no-print-directory -C ../../../data/build_mmb_analysis_dataset
	test -f $(UPSTREAM_MMB_REG)

$(UPSTREAM_MMB_REG): | upstream_mmb_analysis_dataset
	test -f $@

../input/MMB_reg_format.dta: | ../input upstream_mmb_analysis_dataset
	ln -sfn $(UPSTREAM_MMB_REG) $@

build: main.py ../../regression_table_tools.py ../input/MMB_reg_format.dta $(UPSTREAM_MMB_REG) ../../../../config/params.yaml | ../output upstream_mmb_analysis_dataset
	$(PYTHON) main.py
	@for f in $(OUTPUTS); do test -f "$$f" || { echo "Missing $$f"; exit 1; }; done

$(OUTPUTS): build
	@test -f $@

../input ../output:
	mkdir -p $@
