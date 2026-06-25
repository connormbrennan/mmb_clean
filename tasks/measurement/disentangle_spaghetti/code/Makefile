SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean FORCE build
.NOTPARALLEL:

UPSTREAM_MMB_REG := ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta
UPSTREAM_MMB_IRF := ../../../data/build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta
OUTDIR := ../output/disentangle_spaghetti

OUTPUTS := \
	$(OUTDIR)/attribute_driver_dropped_collinear_terms.csv \
	$(OUTDIR)/attribute_driver_modelavg_coefficients.csv \
	$(OUTDIR)/attribute_driver_modelavg_significant.csv \
	$(OUTDIR)/attribute_driver_panel_coefficients.csv \
	$(OUTDIR)/attribute_driver_panel_significant.csv \
	$(OUTDIR)/attribute_driver_panel_sparse_significant.csv \
	$(OUTDIR)/findings_report.md \
	$(OUTDIR)/irf_archetype_assignments.csv \
	$(OUTDIR)/irf_archetype_assignments_long_methods.csv \
	$(OUTDIR)/irf_archetype_assignments_wide_methods.csv \
	$(OUTDIR)/irf_archetype_attribute_prevalence.csv \
	$(OUTDIR)/irf_archetype_fpca_variance.csv \
	$(OUTDIR)/irf_archetype_method_attribute_prevalence.csv \
	$(OUTDIR)/irf_archetype_method_comparison.csv \
	$(OUTDIR)/irf_archetype_method_model_stability.csv \
	$(OUTDIR)/irf_archetype_method_outcome_means.csv \
	$(OUTDIR)/irf_archetype_method_stability_summary.csv \
	$(OUTDIR)/irf_archetype_model_stability.csv \
	$(OUTDIR)/irf_archetype_outcome_means.csv \
	$(OUTDIR)/irf_archetype_stability_summary.csv \
	$(OUTDIR)/irf_shape_features.csv \
	$(OUTDIR)/nonlinear_benchmark_cv.csv \
	$(OUTDIR)/outlier_sensitivity_cv.csv \
	$(OUTDIR)/outlier_table_1_99.csv \
	$(OUTDIR)/rf_feature_importance.csv \
	$(OUTDIR)/rf_group_importance.csv \
	$(OUTDIR)/rule_rank_stability.csv \
	$(OUTDIR)/variance_decomposition.csv \
	$(OUTDIR)/ward_archetype_summary.png \
	$(OUTDIR)/ward_archetype_summary_description.txt \
	$(OUTDIR)/within_model_rule_contrasts.csv \
	../output/manifest.csv

all: build

clean:
	mkdir -p ../input ../output
	rm -rf $(OUTDIR) ../output/manifest.csv
	find ../input -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
	touch ../input/.gitkeep ../output/.gitkeep

FORCE:

$(UPSTREAM_MMB_REG): FORCE
	$(MAKE) --no-print-directory -C ../../../data/build_mmb_analysis_dataset
	test -f $@

$(UPSTREAM_MMB_IRF): FORCE
	$(MAKE) --no-print-directory -C ../../../data/build_mmb_analysis_dataset
	test -f $@

../input/MMB_reg_format.dta: $(UPSTREAM_MMB_REG) | ../input
	ln -sfn $(UPSTREAM_MMB_REG) $@

../input/MMB_IRF_format_full.dta: $(UPSTREAM_MMB_IRF) | ../input
	ln -sfn $(UPSTREAM_MMB_IRF) $@

build: build_disentangle_spaghetti.py ../input/MMB_reg_format.dta ../input/MMB_IRF_format_full.dta $(UPSTREAM_MMB_REG) $(UPSTREAM_MMB_IRF) | ../output
	$(PYTHON) build_disentangle_spaghetti.py
	@for f in $(OUTPUTS); do test -f "$$f" || { echo "Missing $$f"; exit 1; }; done

$(OUTPUTS): build
	@test -f $@

../input ../output:
	mkdir -p $@
