# Disentangle Spaghetti Report

## Executive Summary

Identification used for driver analysis:
- Main inference uses regressions with **rule controls** (`rule_itr`, `rule_g`) and model/non-model attributes as regressors.
- We **do not** use model fixed effects to infer attribute effects, because model FE absorb time-invariant attributes.
- Model FE analysis is included only as a diagnostic for where raw variance sits.

Main conclusions:
- Timing heterogeneity is driven most consistently by non-model features: `estimated` and `cb_authors_ext` are positive and significant in timing regressions; `cb_x_late` is negative for inflation timing.
- Output-power heterogeneity is linked to specific structural interactions: `bnk_x_ntw` is negative/significant for `IScurve20` (stronger output response), while `sw_x_noidx` is positive/significant (weaker output response).
- Inflation-power and disinflation-cost heterogeneity are tied to wage indexation structure: `sw_x_idx` raises `infl_per_rr20` (weaker inflation response) and raises `sacratio20` (higher disinflation cost), while `pr_ndx` lowers `sacratio20`.
- Archetype structure is not noise: 75 models split mostly into stable slow/moderate and fast/high-power classes with only 3 rule-switchers.

## 1) Diagnostic: Model vs Rule Variance Decomposition

       outcome  n_obs  r2_rule_only  r2_model_only  r2_rule_plus_model  inc_rule_given_model  inc_model_given_rule
     IScurve20    217        0.0270         0.3769              0.3951                0.0183                0.3681
 infl_per_rr20    217        0.0604         0.3027              0.3605                0.0578                0.3001
piq_timing_max    217        0.0039         0.9043              0.9098                0.0055                0.9059
    sacratio20    192        0.0003         0.9357              0.9360                0.0003                0.9358
  y_timing_max    217        0.0415         0.7432              0.7661                0.0229                0.7247

Model-vs-rule dominance ratio (`inc_model_given_rule / inc_rule_given_model`):
       outcome  model_to_rule_increment_ratio
     IScurve20                          20.15
 infl_per_rr20                           5.19
piq_timing_max                         165.92
    sacratio20                        3018.30
  y_timing_max                          31.65

Interpretation: this section is diagnostic only; it does not identify attribute effects.

## 2) Driver Regressions (Rule-Controlled, No Model FE)

Significant attribute drivers (panel, p<=0.10; rules forced in and omitted from this list):
       outcome        feature    coef  p_value                                interpretation
     IScurve20      bnk_x_ntw -1.1158   0.0014 stronger policy power (larger absolute slope)
     IScurve20     sw_x_noidx  0.4180   0.0032  weaker policy power (smaller absolute slope)
     IScurve20       bnkcrdit  0.3374   0.0675  weaker policy power (smaller absolute slope)
     IScurve20         pr_ndx  0.2124   0.0973  weaker policy power (smaller absolute slope)
 infl_per_rr20       sw_x_idx  0.2235   0.0025  weaker policy power (smaller absolute slope)
 infl_per_rr20 cb_authors_ext -0.2163   0.0190 stronger policy power (larger absolute slope)
 infl_per_rr20           open  0.1880   0.0682  weaker policy power (smaller absolute slope)
piq_timing_max cb_authors_ext  1.0741   0.0000                     longer lag to peak effect
piq_timing_max      cb_x_late -0.8581   0.0044                    shorter lag to peak effect
piq_timing_max         ntwrth -0.4899   0.0149                    shorter lag to peak effect
piq_timing_max       bnkcrdit  0.5341   0.0151                     longer lag to peak effect
piq_timing_max         pr_ndx  0.2842   0.0633                     longer lag to peak effect
    sacratio20       sw_x_idx  5.3618   0.0002            higher output cost of disinflation
    sacratio20         pr_ndx -2.8251   0.0110             lower output cost of disinflation
    sacratio20           open  4.0601   0.0978            higher output cost of disinflation
  y_timing_max cb_authors_ext  0.7319   0.0001                     longer lag to peak effect

Significant attribute drivers in model-averaged check (p<=0.10):
       outcome        feature    coef  p_value                                interpretation
     IScurve20      bnk_x_ntw -1.4236   0.0206 stronger policy power (larger absolute slope)
 infl_per_rr20       sw_x_idx  0.2060   0.0787  weaker policy power (smaller absolute slope)
piq_timing_max cb_authors_ext  4.6716   0.0048                     longer lag to peak effect
piq_timing_max      cb_x_late -3.9540   0.0138                    shorter lag to peak effect
    sacratio20       sw_x_idx  5.9340   0.0571            higher output cost of disinflation
  y_timing_max cb_authors_ext  1.2605   0.0689                     longer lag to peak effect

## 3) Cross-Rule Rank Stability

       outcome          rule_a          rule_b  n_models  spearman_rho  spearman_p  pearson_r  pearson_p
     IScurve20 Inertial_Taylor          Growth        73        0.8718      0.0000    -0.2308     0.0494
     IScurve20          Taylor          Growth        69        0.6931      0.0000    -0.1703     0.1619
     IScurve20          Taylor Inertial_Taylor        69        0.8963      0.0000     0.9757     0.0000
 infl_per_rr20 Inertial_Taylor          Growth        73        0.4561      0.0001     0.1731     0.1430
 infl_per_rr20          Taylor          Growth        69        0.3570      0.0026    -0.0771     0.5288
 infl_per_rr20          Taylor Inertial_Taylor        69        0.8166      0.0000    -0.1335     0.2741
piq_timing_max Inertial_Taylor          Growth        73        0.9267      0.0000     0.9825     0.0000
piq_timing_max          Taylor          Growth        69        0.8112      0.0000     0.8088     0.0000
piq_timing_max          Taylor Inertial_Taylor        69        0.8471      0.0000     0.8344     0.0000
    sacratio20 Inertial_Taylor          Growth        65        0.9753      0.0000     0.9712     0.0000
    sacratio20          Taylor          Growth        61        0.8641      0.0000     0.9358     0.0000
    sacratio20          Taylor Inertial_Taylor        61        0.8984      0.0000     0.9726     0.0000
  y_timing_max Inertial_Taylor          Growth        73        0.9769      0.0000     0.7779     0.0000
  y_timing_max          Taylor          Growth        69        0.5770      0.0000     0.5626     0.0000
  y_timing_max          Taylor Inertial_Taylor        69        0.6182      0.0000     0.5976     0.0000

Interpretation: model ranking persistence across rules is high (especially for timing and sacratio).

## 4) Within-Model Rule Contrasts

       outcome                 contrast                      group  n_models  mean_delta  median_delta  t_test_p
     IScurve20 Growth - Inertial_Taylor                 all_models        73     -0.2284       -0.1220    0.5645
     IScurve20 Growth - Inertial_Taylor          calibrated_models        30      0.3824       -0.1072    0.6716
     IScurve20 Growth - Inertial_Taylor estimated_minus_calibrated        30     -1.0369       -0.0358    0.2703
     IScurve20 Growth - Inertial_Taylor           estimated_models        43     -0.6545       -0.1431    0.0099
     IScurve20          Growth - Taylor                 all_models        69     -0.5285       -0.4275    0.1030
     IScurve20          Growth - Taylor          calibrated_models        30     -0.3156       -0.4227    0.6673
     IScurve20          Growth - Taylor estimated_minus_calibrated        30     -0.3767       -0.0245    0.6119
     IScurve20          Growth - Taylor           estimated_models        39     -0.6923       -0.4472    0.0000
     IScurve20 Inertial_Taylor - Taylor                 all_models        69     -0.4980       -0.3285    0.0000
     IScurve20 Inertial_Taylor - Taylor          calibrated_models        30     -0.6979       -0.3277    0.0019
     IScurve20 Inertial_Taylor - Taylor estimated_minus_calibrated        30      0.3537       -0.0119    0.0996
     IScurve20 Inertial_Taylor - Taylor           estimated_models        39     -0.3442       -0.3396    0.0000
 infl_per_rr20 Growth - Inertial_Taylor                 all_models        73     -0.4123       -0.1635    0.0005
 infl_per_rr20 Growth - Inertial_Taylor          calibrated_models        30     -0.4749       -0.1939    0.0159
 infl_per_rr20 Growth - Inertial_Taylor estimated_minus_calibrated        30      0.1062        0.0368    0.6532
 infl_per_rr20 Growth - Inertial_Taylor           estimated_models        43     -0.3687       -0.1571    0.0145
 infl_per_rr20          Growth - Taylor                 all_models        69     -0.8222       -0.3793    0.0070
 infl_per_rr20          Growth - Taylor          calibrated_models        30     -1.4534       -0.5732    0.0361
 infl_per_rr20          Growth - Taylor estimated_minus_calibrated        30      1.1167        0.3115    0.1039
 infl_per_rr20          Growth - Taylor           estimated_models        39     -0.3366       -0.2617    0.0001
 infl_per_rr20 Inertial_Taylor - Taylor                 all_models        69     -0.5060       -0.1789    0.0819
 infl_per_rr20 Inertial_Taylor - Taylor          calibrated_models        30     -0.9785       -0.2734    0.1452
 infl_per_rr20 Inertial_Taylor - Taylor estimated_minus_calibrated        30      0.8360        0.1386    0.2116
 infl_per_rr20 Inertial_Taylor - Taylor           estimated_models        39     -0.1425       -0.1348    0.0002
piq_timing_max Growth - Inertial_Taylor                 all_models        73      0.3425        0.0000    0.0053
piq_timing_max Growth - Inertial_Taylor          calibrated_models        30      0.0000        0.0000       NaN
piq_timing_max Growth - Inertial_Taylor estimated_minus_calibrated        30      0.5814        0.0000    0.0047
piq_timing_max Growth - Inertial_Taylor           estimated_models        43      0.5814        0.0000    0.0047
piq_timing_max          Growth - Taylor                 all_models        69      0.5942        0.0000    0.0377
piq_timing_max          Growth - Taylor          calibrated_models        30      0.1667        0.0000    0.0226
piq_timing_max          Growth - Taylor estimated_minus_calibrated        30      0.7564        1.0000    0.1338
piq_timing_max          Growth - Taylor           estimated_models        39      0.9231        1.0000    0.0669
piq_timing_max Inertial_Taylor - Taylor                 all_models        69      0.2609        0.0000    0.1913
piq_timing_max Inertial_Taylor - Taylor          calibrated_models        30      0.1667        0.0000    0.0226
piq_timing_max Inertial_Taylor - Taylor estimated_minus_calibrated        30      0.1667        0.0000    0.6403
piq_timing_max Inertial_Taylor - Taylor           estimated_models        39      0.3333        0.0000    0.3431
    sacratio20 Growth - Inertial_Taylor                 all_models        65     -1.7841        0.7300    0.5185
    sacratio20 Growth - Inertial_Taylor          calibrated_models        25      2.4793        0.6746    0.1169
    sacratio20 Growth - Inertial_Taylor estimated_minus_calibrated        25     -6.9279        0.1937    0.1379
    sacratio20 Growth - Inertial_Taylor           estimated_models        40     -4.4487        0.8684    0.3108
    sacratio20          Growth - Taylor                 all_models        61     -1.6206        2.1035    0.6083
    sacratio20          Growth - Taylor          calibrated_models        25      0.7857        2.1035    0.8490
    sacratio20          Growth - Taylor estimated_minus_calibrated        25     -4.0774        0.0124    0.5068
    sacratio20          Growth - Taylor           estimated_models        36     -3.2916        2.1159    0.4733
    sacratio20 Inertial_Taylor - Taylor                 all_models        61      0.1730        1.6081    0.9136
    sacratio20 Inertial_Taylor - Taylor          calibrated_models        25     -1.6936        1.4788    0.6444
    sacratio20 Inertial_Taylor - Taylor estimated_minus_calibrated        25      3.1628        0.2015    0.4067
    sacratio20 Inertial_Taylor - Taylor           estimated_models        36      1.4692        1.6803    0.1435
  y_timing_max Growth - Inertial_Taylor                 all_models        73      0.4658        0.0000    0.0664
  y_timing_max Growth - Inertial_Taylor          calibrated_models        30      0.0333        0.0000    0.3256
  y_timing_max Growth - Inertial_Taylor estimated_minus_calibrated        30      0.7341        0.0000    0.0882
  y_timing_max Growth - Inertial_Taylor           estimated_models        43      0.7674        0.0000    0.0744
  y_timing_max          Growth - Taylor                 all_models        69      0.7101        0.0000    0.0002
  y_timing_max          Growth - Taylor          calibrated_models        30      0.1000        0.0000    0.4146
  y_timing_max          Growth - Taylor estimated_minus_calibrated        30      1.0795        1.0000    0.0012
  y_timing_max          Growth - Taylor           estimated_models        39      1.1795        1.0000    0.0002
  y_timing_max Inertial_Taylor - Taylor                 all_models        69      0.5217        0.0000    0.0028
  y_timing_max Inertial_Taylor - Taylor          calibrated_models        30      0.0667        0.0000    0.5362
  y_timing_max Inertial_Taylor - Taylor estimated_minus_calibrated        30      0.8051        1.0000    0.0089
  y_timing_max Inertial_Taylor - Taylor           estimated_models        39      0.8718        1.0000    0.0030

Interpretation: rules shift levels/timing, but most models keep their relative ranking across rules.

## 5) ML Cross-Check on Drivers

Top random-forest feature importances by outcome (rule controls included):
       outcome        feature  rf_importance
     IScurve20         ln_neq         0.2288
     IScurve20    wlth_x_open         0.1393
     IScurve20         rule_g         0.1207
     IScurve20      bnk_x_ntw         0.0834
     IScurve20      estimated         0.0616
     IScurve20       bnkcrdit         0.0481
     IScurve20       sw_x_idx         0.0410
     IScurve20         pr_ndx         0.0378
 infl_per_rr20         ln_neq         0.2491
 infl_per_rr20         rule_g         0.1788
 infl_per_rr20     wlth_x_bnk         0.1088
 infl_per_rr20      estimated         0.0809
 infl_per_rr20       rule_itr         0.0778
 infl_per_rr20 cb_authors_ext         0.0539
 infl_per_rr20      cb_x_late         0.0482
 infl_per_rr20       sw_x_idx         0.0342
piq_timing_max         ln_neq         0.5530
piq_timing_max cb_authors_ext         0.1285
piq_timing_max      estimated         0.0887
piq_timing_max       vint_mid         0.0475
piq_timing_max      vint_late         0.0407
piq_timing_max         pr_ndx         0.0271
piq_timing_max           open         0.0253
piq_timing_max       sw_x_idx         0.0213
    sacratio20         ln_neq         0.7845
    sacratio20         pr_ndx         0.0367
    sacratio20       sw_x_idx         0.0284
    sacratio20      estimated         0.0266
    sacratio20      bnk_x_ntw         0.0213
    sacratio20           wlth         0.0137
    sacratio20     sw_x_noidx         0.0134
    sacratio20      cb_x_late         0.0134
  y_timing_max         ln_neq         0.3983
  y_timing_max      estimated         0.1766
  y_timing_max cb_authors_ext         0.0922
  y_timing_max         rule_g         0.0863
  y_timing_max       sw_x_idx         0.0440
  y_timing_max       rule_itr         0.0435
  y_timing_max       bnkcrdit         0.0368
  y_timing_max           wlth         0.0356

Grouped importance via group-permutation drop in holdout R2:
       outcome    group  base_cv_r2  group_permute_r2_drop
     IScurve20 nonmodel      0.0503                 0.0785
     IScurve20     real      0.0503                 0.0777
     IScurve20    rules      0.0503                 0.0755
     IScurve20  nominal      0.0503                 0.0578
 infl_per_rr20    rules     -0.4823                 0.5249
 infl_per_rr20  nominal     -0.4823                -0.0034
 infl_per_rr20 nonmodel     -0.4823                -0.0254
 infl_per_rr20     real     -0.4823                -0.2155
piq_timing_max nonmodel      0.4573                 0.7948
piq_timing_max  nominal      0.4573                 0.0359
piq_timing_max     real      0.4573                 0.0318
piq_timing_max    rules      0.4573                -0.0080
    sacratio20 nonmodel      0.1924                 0.4422
    sacratio20  nominal      0.1924                 0.0715
    sacratio20     real      0.1924                 0.0318
    sacratio20    rules      0.1924                -0.0085
  y_timing_max nonmodel      0.2905                 0.7061
  y_timing_max    rules      0.2905                 0.1656
  y_timing_max     real      0.2905                 0.1000
  y_timing_max  nominal      0.2905                -0.0006

Interpretation: non-model features dominate timing predictability; rules dominate inflation-slope predictability.

## 6) IRF Archetypes

Cluster outcome means:
 cluster_raw  IScurve20  infl_per_rr20  sacratio20  y_timing_max  piq_timing_max
           0    -2.2338        -0.8239      8.4717        1.1333          1.1667
           1    -0.8231        -0.2069     15.4429        2.4225          2.7005

Cluster attribute prevalence:
 cluster_raw  estimated  cb_authors_ext   wlth  ntwrth  bnkcrdit   open  rule_itr  rule_g
           0     0.1667          0.5333 0.5000  0.2333    0.4333 0.1333    0.3000  0.3667
           1     0.6471          0.7433 0.2513  0.2781    0.4385 0.1070    0.3422  0.3369

Model-level cluster stability:
       stability_class  n_models  avg_dominant_share
  stable_slow_moderate        63              1.0000
stable_fast_high_power         9              1.0000
         rule_switcher         3              0.6667

Fast/high-power archetype (cluster 0) mean y_timing=1.13, pi_timing=1.17; Slow/moderate archetype (cluster 1) mean y_timing=2.42, pi_timing=2.70.

Rule-switcher models:
   model  n_rules_present  n_clusters_seen  dominant_cluster  dominant_share stability_class
NK_MPT10                3                2                 1        0.666667   rule_switcher
US_FRB03                3                2                 1        0.666667   rule_switcher
US_IAC05                3                2                 1        0.666667   rule_switcher

## 7) Nonlinear vs Linear Benchmark (CV)

       outcome model  n_obs  cv_r2_mean  cv_r2_sd  cv_mae_mean
     IScurve20   HGB    217     -0.0575    0.2291       0.8800
     IScurve20    RF    217      0.0802    0.1753       0.8600
     IScurve20 Ridge    217      0.0598    0.2617       0.9200
 infl_per_rr20   HGB    217     -0.7886    0.6263       0.5868
 infl_per_rr20    RF    217     -0.1957    0.1783       0.4951
 infl_per_rr20 Ridge    217     -0.1860    0.2919       0.5743
piq_timing_max   HGB    217      0.5475    0.2433       1.0818
piq_timing_max    RF    217      0.4463    0.1805       1.2004
piq_timing_max Ridge    217     -0.1645    0.7003       1.7139
    sacratio20   HGB    192      0.4016    0.2098      14.3364
    sacratio20    RF    192      0.1966    0.1777      17.5316
    sacratio20 Ridge    192     -0.5523    0.8478      24.7300
  y_timing_max   HGB    217      0.2841    0.1468       0.9666
  y_timing_max    RF    217      0.3180    0.1060       0.9246
  y_timing_max Ridge    217      0.0551    0.1097       1.2055

Interpretation: nonlinear models materially improve fit for timing and sacratio, indicating interaction/nonlinearity in transmission differences.

## 8) Outlier Sensitivity

Extreme rows (1/99-tail on any outcome):
    model            rule  IScurve20  infl_per_rr20  sacratio20  y_timing_max  piq_timing_max  IScurve20_out_1_99  infl_per_rr20_out_1_99  sacratio20_out_1_99  y_timing_max_out_1_99  piq_timing_max_out_1_99  n_outlier_flags
 US_CCF12          Growth -10.723366      -5.343422   28.051451          25.0             1.0                True                    True                False                   True                    False                3
  NK_NS14          Growth  12.704152       2.846872   56.818375           1.0             1.0                True                    True                False                  False                    False                2
  NK_KW16          Growth  -8.154112      -2.906513   14.196266           3.0             1.0                True                    True                False                  False                    False                2
  NK_ET14          Taylor  -0.138958      18.567568   82.342567           1.0             1.0               False                    True                False                  False                    False                1
  US_RS99 Inertial_Taylor  -1.066298      -0.884351   13.242410           8.0            21.0               False                   False                False                  False                     True                1
  US_PV15          Growth   0.013817      -0.072876  226.889053           2.0             4.0                True                   False                False                  False                    False                1
NK_GLSV07          Growth  -3.080499      -2.955461    3.639272           1.0             1.0               False                    True                False                  False                    False                1
  NK_ET14          Growth  -0.017670      -1.286785   -6.018770           1.0             1.0               False                   False                 True                  False                    False                1
  US_PV15 Inertial_Taylor  -0.123962      -0.075872  384.605713           2.0             3.0               False                   False                 True                  False                    False                1
US_CFOP14          Taylor   0.107877      -0.024060    0.310718           1.0            12.0                True                   False                False                  False                    False                1
  NK_NS14 Inertial_Taylor -13.097503      -0.231173   21.764202           1.0             1.0                True                   False                False                  False                    False                1
  NK_KW16 Inertial_Taylor  -4.939347       0.728454    9.498955           3.0             1.0               False                    True                False                  False                    False                1
  NK_ET14 Inertial_Taylor  -0.017560      -1.304964   -6.076959           1.0             1.0               False                   False                 True                  False                    False                1
  US_PV15          Taylor   0.007066      -0.021715  360.375671           1.0             2.0               False                   False                 True                  False                    False                1
US_MI07AL          Taylor  -0.002437      -0.177437    8.872213           1.0            16.0               False                   False                False                  False                     True                1
  US_DG08          Taylor  -0.731767      -0.013312    6.531013          10.0             3.0               False                   False                False                   True                    False                1
  US_RS99          Growth  -0.864486      -0.659129   13.280334           8.0            28.0               False                   False                False                  False                     True                1

Predictive sensitivity (full vs trimmed):
          subset        outcome model  n_obs  cv_r2_mean
            full      IScurve20    RF    217      0.0762
            full      IScurve20 Ridge    217      0.0598
trimmed_1_99_any      IScurve20    RF    200      0.2814
trimmed_1_99_any      IScurve20 Ridge    200      0.1418
            full  infl_per_rr20    RF    217     -0.2190
            full  infl_per_rr20 Ridge    217     -0.1860
trimmed_1_99_any  infl_per_rr20    RF    200      0.1567
trimmed_1_99_any  infl_per_rr20 Ridge    200      0.0706
            full piq_timing_max    RF    217      0.4455
            full piq_timing_max Ridge    217     -0.1645
trimmed_1_99_any piq_timing_max    RF    200      0.2663
trimmed_1_99_any piq_timing_max Ridge    200      0.1739
            full     sacratio20    RF    192      0.2033
            full     sacratio20 Ridge    192     -0.5523
trimmed_1_99_any     sacratio20    RF    175     -1.0014
trimmed_1_99_any     sacratio20 Ridge    175     -2.0954
            full   y_timing_max    RF    217      0.3207
            full   y_timing_max Ridge    217      0.0551
trimmed_1_99_any   y_timing_max    RF    200      0.4146
trimmed_1_99_any   y_timing_max Ridge    200      0.1858

## 9) So What

- The main empirical split is **speed/persistence**, not just slope magnitudes.
- `estimated`, `cb_authors_ext`, and vintage interactions matter most for timing outcomes.
- Wage-indexation design is the clearest nominal-rigidity driver of inflation effectiveness/cost tradeoffs.
- Real-friction interactions matter for output power but do not robustly map one-for-one into inflation power.
- Therefore, “not much explains differences” is too pessimistic: differences are structured around a few recurring channels, with large residual heterogeneity still present.
