# H1 Weather Internal Consistency and Plausibility Assessment

## Purpose
This analysis provides an internal consistency and plausibility assessment against the climate normals used for model parameterization for H1, using weather as the empirically assessable everyday contextual condition.

It is not an independent external validation.

## Source and reference period
MeteoSwiss climate normals for Bern/Zollikofen, 553 m above sea level, 46.99 N, 7.46 E, Central Plateau, reference period 1991–2020; climsheet 2.2.0, status 2024.

## Simulation design
Number of simulated 360-day model years: 50
Seed range/list: 3263–3312; complete list recorded in `run_config.json`.

The native weather model calendar contains 12 months, 30 days per month, 360 days per simulated model year, and 8,640 hourly observations per simulated model year.

For extensive variables and event-day counts, native 30-day monthly values are preserved and standardized as native / 30 × average Gregorian month length for 1991–2020. The reference period contains eight leap years.

The simulated snow-cover variable is a binary hourly indicator; a simulated snow-cover day is operationalized as at least one hour with `snow_cover=True`.

## Summary metrics
                    variable  pearson_r       mae      rmse  mean_bias_sim_minus_ref
                  frost_days   0.990193  3.022974  4.345264                 2.006530
                   heat_days   0.881817  0.342000  0.759230                -0.342000
                humidity_pct   0.999940  0.734341  0.738546                 0.734341
                    ice_days        NaN  1.566667  2.990819                -1.566667
         precip_days_ge_10mm   0.878774  0.669774  0.770396                 0.669774
          precip_days_ge_1mm   0.697589  0.768774  0.940891                -0.270996
         precip_days_ge_50mm   0.537197  0.026333  0.044430                -0.019667
          precip_days_ge_5mm   0.832200  1.036170  1.195631                 1.035170
      precipitation_total_mm   0.913974 11.276302 12.988203                10.370897
             snow_cover_days   0.960073  0.723000  1.345310                 0.262000
                 summer_days   0.963024  1.689833  2.825383                 0.309944
              sunshine_hours   0.999965  1.865061  2.163545                 1.818307
                sunshine_pct   0.999546  2.642967  2.841460                -2.642967
temperature_daily_max_mean_c   0.999167  0.789757  0.976385                 0.756577
temperature_daily_min_mean_c   0.998408  1.128157  1.314170                -1.128157
          temperature_mean_c   0.999985  0.076200  0.086092                -0.076200
                    wind_m_s   0.999797  0.069329  0.069443                 0.069329

Undefined Pearson correlations are reported as NaN when either the reference or simulated monthly series has zero variance.

## 95% interval coverage
                    variable  months_inside_95_interval  n_months  coverage_fraction
                  frost_days                          6        12           0.500000
                   heat_days                          9        12           0.750000
                humidity_pct                          1        12           0.083333
                    ice_days                          7        12           0.583333
         precip_days_ge_10mm                         12        12           1.000000
          precip_days_ge_1mm                         12        12           1.000000
         precip_days_ge_50mm                         10        12           0.833333
          precip_days_ge_5mm                         12        12           1.000000
      precipitation_total_mm                         12        12           1.000000
             snow_cover_days                         11        12           0.916667
                 summer_days                          8        12           0.666667
              sunshine_hours                         12        12           1.000000
                sunshine_pct                         12        12           1.000000
temperature_daily_max_mean_c                          3        12           0.250000
temperature_daily_min_mean_c                          1        12           0.083333
          temperature_mean_c                         12        12           1.000000
                    wind_m_s                          3        12           0.250000

## Precipitation quantile comparison
 month month_label  quantile  reference_mm  simulated_mm  difference_mm  absolute_difference_mm
     1         Jan         0          11.0     19.841033       8.841033                8.841033
     1         Jan        20          30.0     43.497753      13.497753               13.497753
     1         Jan        40          43.0     63.752120      20.752120               20.752120
     1         Jan        60          53.0     91.984440      38.984440               38.984440
     1         Jan        80          86.0    109.695773      23.695773               23.695773
     1         Jan       100         149.0    158.085533       9.085533                9.085533
     2         Feb         0           8.0     15.978204       7.978204                7.978204
     2         Feb        20          30.0     35.022588       5.022588                5.022588
     2         Feb        40          38.0     49.981120      11.981120               11.981120
     2         Feb        60          55.0     65.645753      10.645753               10.645753
     2         Feb        80          85.0     94.464373       9.464373                9.464373
     2         Feb       100         123.0    111.128516     -11.871484               11.871484
     3         Mar         0          20.0      8.740967     -11.259033               11.259033
     3         Mar        20          35.0     47.756533      12.756533               12.756533
     3         Mar        40          48.0     65.720413      17.720413               17.720413
     3         Mar        60          63.0     85.280380      22.280380               22.280380
     3         Mar        80          77.0    113.371340      36.371340               36.371340
     3         Mar       100         248.0    166.642567     -81.357433               81.357433
     4         Apr         0          13.0     18.381000       5.381000                5.381000
     4         Apr        20          41.0     68.833600      27.833600               27.833600
     4         Apr        40          55.0     86.994800      31.994800               31.994800
     4         Apr        60          84.0     98.677400      14.677400               14.677400
     4         Apr        80         118.0    119.839200       1.839200                1.839200
     4         Apr       100         209.0    172.054000     -36.946000               36.946000
     5         May         0          34.0     40.531467       6.531467                6.531467
     5         May        20          76.0     80.529527       4.529527                4.529527
     5         May        40          85.0     98.652747      13.652747               13.652747
     5         May        60         127.0    125.332793      -1.667207                1.667207
     5         May        80         161.0    149.521887     -11.478113               11.478113
     5         May       100         189.0    255.373867      66.373867               66.373867
     6         Jun         0          41.0     53.137000      12.137000               12.137000
     6         Jun        20          70.0     93.230400      23.230400               23.230400
     6         Jun        40          82.0    122.041000      40.041000               40.041000
     6         Jun        60         107.0    133.884000      26.884000               26.884000
     6         Jun        80         141.0    154.167600      13.167600               13.167600
     6         Jun       100         183.0    215.918000      32.918000               32.918000
     7         Jul         0          38.0     35.709933      -2.290067                2.290067
     7         Jul        20          62.0     63.757287       1.757287                1.757287
     7         Jul        40          83.0     83.691320       0.691320                0.691320
     7         Jul        60         119.0    108.609120     -10.390880               10.390880
     7         Jul        80         149.0    140.934473      -8.065527                8.065527
     7         Jul       100         252.0    206.751400     -45.248600               45.248600
     8         Aug         0          10.0     20.788600      10.788600               10.788600
     8         Aug        20          75.0     79.565427       4.565427                4.565427
     8         Aug        40          93.0    106.405227      13.405227               13.405227
     8         Aug        60         114.0    134.300473      20.300473               20.300473
     8         Aug        80         159.0    166.906067       7.906067                7.906067
     8         Aug       100         224.0    238.620433      14.620433               14.620433
     9         Sep         0          17.0     35.500000      18.500000               18.500000
     9         Sep        20          49.0     63.588800      14.588800               14.588800
     9         Sep        40          71.0     89.373800      18.373800               18.373800
     9         Sep        60          92.0    118.111600      26.111600               26.111600
     9         Sep        80         130.0    134.291400       4.291400                4.291400
     9         Sep       100         162.0    190.034000      28.034000               28.034000
    10         Oct         0          11.0     13.633800       2.633800                2.633800
    10         Oct        20          50.0     55.417047       5.417047                5.417047
    10         Oct        40          72.0     82.465580      10.465580               10.465580
    10         Oct        60          93.0    104.279040      11.279040               11.279040
    10         Oct        80         125.0    128.733493       3.733493                3.733493
    10         Oct       100         163.0    196.143200      33.143200               33.143200
    11         Nov         0           4.0     25.341000      21.341000               21.341000
    11         Nov        20          35.0     48.080800      13.080800               13.080800
    11         Nov        40          57.0     73.394800      16.394800               16.394800
    11         Nov        60          85.0     94.262600       9.262600                9.262600
    11         Nov        80         127.0    117.972600      -9.027400                9.027400
    11         Nov       100         183.0    198.120000      15.120000               15.120000
    12         Dec         0           1.0     17.112000      16.112000               16.112000
    12         Dec        20          37.0     47.029273      10.029273               10.029273
    12         Dec        40          67.0     57.057980      -9.942020                9.942020
    12         Dec        60          88.0     84.031700      -3.968300                3.968300
    12         Dec        80         124.0    102.341747     -21.658253               21.658253
    12         Dec       100         152.0    214.647100      62.647100               62.647100

## Figures
- [Temperature monthly comparison](figures/temperature_monthly_comparison.png)
- [Temperature event days](figures/temperature_event_days.png)
- [Precipitation monthly comparison](figures/precipitation_monthly_comparison.png)
- [Precipitation quantiles](figures/precipitation_quantiles.png)
- [Other weather variables](figures/other_weather_variables.png)

## Limitations
- Reference data were used for parameterization.
- Simulated years contain 360 days.
- Only climate normals, not independent hourly observations, are used.
- Agreement demonstrates implementation consistency, not predictive validity.

## Neutral conclusion
The outputs provide descriptive evidence about implementation consistency and plausibility. They do not automatically support or reject H1.