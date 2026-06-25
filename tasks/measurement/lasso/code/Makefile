SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean FORCE build
.NOTPARALLEL:

UPSTREAM_MMB_REG := ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta

OUTPUTS := \
	../output/lasso/lasso_metadata.json \
	../output/lasso/lasso_coefficients_long.csv \
	../output/lasso/lasso_coefficients_long_citation_weighted.csv \
	../output/lasso/lasso_zeroed_summary.csv \
	../output/lasso/lasso_zeroed_summary_citation_weighted.csv \
	../output/lasso/lasso_zeroed_features.csv \
	../output/lasso/lasso_zeroed_features_citation_weighted.csv \
	../output/lasso/lasso_nonzero_features.csv \
	../output/lasso/lasso_nonzero_features_citation_weighted.csv \
	../output/lasso/lasso_sparse_dropped_features.csv \
	../output/lasso/lasso_sparse_dropped_features_by_outcome.csv \
	../output/lasso/lasso_sparse_dropped_features_by_outcome_citation_weighted.csv \
	../output/lasso/lasso_zeroed_report.txt \
	../output/lasso/lasso_zeroed_report_citation_weighted.txt \
	../output/lasso/lasso_post_selection_table.tex \
	../output/lasso/lasso_post_selection_table.csv \
	../output/lasso/lasso_post_selection_table_citation_weighted.tex \
	../output/lasso/lasso_post_selection_table_citation_weighted.csv \
	../output/lasso/post_refit_diagnostics.csv \
	../output/lasso/post_refit_diagnostics_citation_weighted.csv

all: build

clean:
	mkdir -p ../input ../output
	rm -rf ../output/lasso
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

build: build_lasso.py ../../regression_table_tools.py ../input/MMB_reg_format.dta $(UPSTREAM_MMB_REG) | ../output upstream_mmb_analysis_dataset
	$(PYTHON) build_lasso.py
	@for f in $(OUTPUTS); do test -f "$$f" || { echo "Missing $$f"; exit 1; }; done

$(OUTPUTS): build
	@test -f $@

../input ../output:
	mkdir -p $@
