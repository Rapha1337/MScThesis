# Reproducible T1 persona clustering for AIcoPA v1.1
#
# Primary analysis:
#   Gower distance + partitioning around medoids (PAM) using occupational
#   status, weekly workload, holiday/stress weeks, care work, social hours,
#   and MVPA hours/week.
#
# Sensitivities: omit/replace PA, omit occupation, add daily routine, POI,
# residential context, sociodemographics, or require holiday + stress <= 52.
#
# Run from repository root:
#   Rscript analysis/t1_persona_cluster_analysis.R
# Optional arguments:
#   Rscript analysis/t1_persona_cluster_analysis.R INPUT_FILE OUTPUT_DIRECTORY
# Required packages:
#   install.packages(c("cluster", "readxl"))

required_packages <- c("cluster", "readxl")
missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]
if (length(missing_packages) > 0L) {
  stop(
    "Missing required package(s): ", paste(missing_packages, collapse = ", "),
    ". Install them with install.packages() before running the analysis.",
    call. = FALSE
  )
}

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

K_RANGE <- 2:8
MIN_CLUSTER_SIZE <- 5L
PRIMARY_STABILITY_REPETITIONS <- 500L
SENSITIVITY_STABILITY_REPETITIONS <- 200L
SUBSAMPLE_FRACTION <- 0.80
RANDOM_SEED <- 20260916L

# Leave as NA for data-driven selection. Use a fixed value only as a documented
# a-priori override.
PRIMARY_K_OVERRIDE <- NA_integer_

args <- commandArgs(trailingOnly = TRUE)
default_input_candidates <- c(
  "analysis/data/AIcoPA_T1_complete_responses_anonym_20260916.xlsx",
  "data/AIcoPA_T1_complete_responses_anonym_20260916.xlsx",
  "analysis/data/AIcoPA_T1_complete_responses_anonym_20260916.csv",
  "analysis/data/AIcoPA_T1_complete_anonym_20260915.CSV"
)
input_path <- if (length(args) >= 1L) {
  args[[1L]]
} else {
  existing <- default_input_candidates[file.exists(default_input_candidates)]
  if (length(existing) > 0L) existing[[1L]] else default_input_candidates[[1L]]
}
output_dir <- if (length(args) >= 2L) {
  args[[2L]]
} else {
  "analysis/results_t1_persona_clustering_v1_1"
}
if (!file.exists(input_path)) {
  stop(
    "Input file not found: ", input_path,
    "\nPass the anonymized T1 XLSX/CSV as the first command-line argument.",
    call. = FALSE
  )
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------

write_utf8_csv <- function(x, filename) {
  utils::write.csv(
    x, file = file.path(output_dir, filename), row.names = FALSE, na = "",
    fileEncoding = "UTF-8"
  )
}

extract_variable_name <- function(label) {
  prefix <- sub("\\.\\s.*$", "", trimws(as.character(label)), perl = TRUE)
  prefix <- gsub('^"|"$', "", prefix)
  match <- regexec("^([^\\[]+)\\[([^\\]]+)\\]$", prefix, perl = TRUE)
  parts <- regmatches(prefix, match)[[1L]]
  if (length(parts) == 3L) {
    if (identical(parts[[3L]], "other")) return(paste0(parts[[2L]], "_other"))
    return(parts[[3L]])
  }
  prefix
}

read_t1_file <- function(path) {
  extension <- tolower(tools::file_ext(path))
  if (extension %in% c("xlsx", "xls")) {
    imported <- as.data.frame(
      readxl::read_excel(path, col_types = "text", .name_repair = "minimal"),
      stringsAsFactors = FALSE, check.names = FALSE
    )
    labels <- names(imported)
  } else if (extension %in% c("csv", "txt")) {
    imported <- utils::read.csv2(
      path, header = TRUE, colClasses = "character",
      fileEncoding = "windows-1252", quote = '"', comment.char = "",
      check.names = FALSE, na.strings = character()
    )
    generic_header <- all(grepl("^Column[0-9]+$", names(imported)))
    if (generic_header) {
      if (nrow(imported) < 1L) stop("CSV has no LimeSurvey label row.", call. = FALSE)
      labels <- unlist(imported[1L, ], use.names = FALSE)
      imported <- imported[-1L, , drop = FALSE]
    } else {
      labels <- names(imported)
    }
  } else {
    stop("Unsupported format. Use XLSX, XLS, or semicolon-separated CSV.", call. = FALSE)
  }
  mapped_names <- vapply(labels, extract_variable_name, character(1))
  if (anyDuplicated(mapped_names)) {
    duplicates <- unique(mapped_names[duplicated(mapped_names)])
    stop("Duplicate mapped names: ", paste(duplicates, collapse = ", "), call. = FALSE)
  }
  names(imported) <- mapped_names
  rownames(imported) <- NULL
  imported
}

numeric_prefix <- function(x) {
  x <- trimws(as.character(x))
  position <- regexpr("-?[0-9]+(?:[.,][0-9]+)?", x, perl = TRUE)
  output <- rep(NA_real_, length(x))
  # regexpr() returns NA when the input itself is NA. Exclude these positions
  # explicitly before using the logical vector for subscripted assignment.
  matched <- !is.na(position) & position > 0L
  match_length <- attr(position, "match.length")
  text <- substring(
    x[matched], position[matched], position[matched] + match_length[matched] - 1L
  )
  output[matched] <- as.numeric(chartr(",", ".", text))
  output
}

strict_row_mean <- function(data, variables) {
  values <- vapply(
    variables, function(variable) numeric_prefix(data[[variable]]),
    numeric(nrow(data))
  )
  if (is.null(dim(values))) values <- matrix(values, ncol = 1L)
  rowMeans(values, na.rm = FALSE)
}

clock_minutes <- function(x, bedtime = FALSE) {
  x <- trimws(as.character(x))
  parts <- regmatches(x, regexec("^([0-9]{1,2}):([0-9]{2})$", x, perl = TRUE))
  output <- vapply(parts, function(value) {
    if (length(value) != 3L) return(NA_real_)
    as.numeric(value[[2L]]) * 60 + as.numeric(value[[3L]])
  }, numeric(1))
  if (bedtime) {
    after_midnight <- !is.na(output) & output < 12 * 60
    output[after_midnight] <- output[after_midnight] + 24 * 60
  }
  output
}

parse_date <- function(x) {
  suppressWarnings(as.Date(substr(trimws(as.character(x)), 1L, 10L)))
}

assert_variables <- function(data, variables) {
  missing <- setdiff(variables, names(data))
  if (length(missing) > 0L) {
    stop("Required variables missing: ", paste(missing, collapse = ", "), call. = FALSE)
  }
}

assert_range <- function(x, lower, upper, variable) {
  invalid <- !is.na(x) & (x < lower | x > upper)
  if (any(invalid)) {
    stop(
      variable, " contains ", sum(invalid), " value(s) outside [",
      lower, ", ", upper, "].", call. = FALSE
    )
  }
}

mode_value <- function(x) {
  x <- x[!is.na(x) & nzchar(as.character(x))]
  if (length(x) == 0L) return(NA_character_)
  names(sort(table(x), decreasing = TRUE))[[1L]]
}

choose2 <- function(x) x * (x - 1) / 2

adjusted_rand_index <- function(labels_a, labels_b) {
  contingency <- table(labels_a, labels_b)
  n <- sum(contingency)
  if (n < 2L) return(NA_real_)
  index <- sum(choose2(contingency))
  row_index <- sum(choose2(rowSums(contingency)))
  column_index <- sum(choose2(colSums(contingency)))
  total_pairs <- choose2(n)
  expected <- row_index * column_index / total_pairs
  maximum <- 0.5 * (row_index + column_index)
  denominator <- maximum - expected
  if (abs(denominator) < .Machine$double.eps) return(1)
  (index - expected) / denominator
}

silhouette_interpretation <- function(value) {
  if (value <= 0.25) return("no substantial cluster structure")
  if (value <= 0.50) return("weak cluster structure")
  if (value <= 0.70) return("reasonable cluster structure")
  "strong cluster structure"
}

# -----------------------------------------------------------------------------
# Clustering helpers
# -----------------------------------------------------------------------------

make_gower_distance <- function(data, variables, categorical_variables) {
  cluster_input <- data[, variables, drop = FALSE]
  for (variable in categorical_variables) {
    cluster_input[[variable]] <- factor(cluster_input[[variable]])
  }
  cluster::daisy(cluster_input, metric = "gower")
}

fit_pam <- function(dissimilarity, k) {
  cluster::pam(
    dissimilarity, k = k, diss = TRUE, keep.diss = TRUE, keep.data = FALSE
  )
}

summarize_pam <- function(fit, dissimilarity, k) {
  silhouette <- cluster::silhouette(fit$clustering, dissimilarity)
  widths <- silhouette[, "sil_width"]
  sizes <- as.integer(table(fit$clustering))
  data.frame(
    k = k,
    average_silhouette = mean(widths),
    minimum_silhouette = min(widths),
    negative_silhouette_n = sum(widths < 0),
    negative_silhouette_proportion = mean(widths < 0),
    minimum_cluster_size = min(sizes),
    maximum_cluster_size = max(sizes),
    cluster_sizes = paste(sizes, collapse = "/"),
    pam_objective = unname(fit$objective[[2L]]),
    stringsAsFactors = FALSE
  )
}

select_k <- function(diagnostics, override = NA_integer_) {
  if (!is.na(override)) {
    if (!(override %in% diagnostics$k)) stop("k override is outside K_RANGE.", call. = FALSE)
    return(override)
  }
  eligible <- diagnostics$minimum_cluster_size >= MIN_CLUSTER_SIZE
  if (!any(eligible)) {
    warning("No solution met minimum cluster size; highest silhouette used diagnostically.")
    eligible <- rep(TRUE, nrow(diagnostics))
  }
  diagnostics$k[which.max(ifelse(eligible, diagnostics$average_silhouette, -Inf))]
}

fit_variant <- function(data, variables, categorical_variables, k_override = NA_integer_) {
  distance <- make_gower_distance(data, variables, categorical_variables)
  fits <- setNames(
    lapply(K_RANGE, function(k) fit_pam(distance, k)), paste0("k", K_RANGE)
  )
  diagnostics <- do.call(rbind, lapply(K_RANGE, function(k) {
    summarize_pam(fits[[paste0("k", k)]], distance, k)
  }))
  rownames(diagnostics) <- NULL
  diagnostics$silhouette_interpretation <- vapply(
    diagnostics$average_silhouette, silhouette_interpretation, character(1)
  )
  diagnostics$meets_minimum_cluster_size <- (
    diagnostics$minimum_cluster_size >= MIN_CLUSTER_SIZE
  )
  selected_k <- select_k(diagnostics, k_override)
  list(
    distance = distance, fits = fits, diagnostics = diagnostics,
    selected_k = selected_k, selected_fit = fits[[paste0("k", selected_k)]]
  )
}

# Relabel clusters in a stable, interpretable order based on their dominant
# occupation. This changes labels only, never memberships or medoids.
canonicalize_selected_solution <- function(fit, sample_data) {
  old_labels <- as.integer(fit$clustering)
  old_ids <- sort(unique(old_labels))
  priority_lookup <- c(
    "Studium" = 1, "Sonstiges" = 2, "Angestellt" = 3,
    "Arbeitslos" = 4, "Ausbildung/Lehre" = 5, "Selbständig" = 6
  )
  order_table <- do.call(rbind, lapply(old_ids, function(cluster_id) {
    members <- old_labels == cluster_id
    dominant <- mode_value(sample_data$occupational_status[members])
    dominant_n <- sum(sample_data$occupational_status[members] == dominant, na.rm = TRUE)
    priority <- unname(priority_lookup[dominant])
    if (length(priority) == 0L || is.na(priority)) priority <- 99
    data.frame(
      old_cluster = cluster_id, dominant_occupation = dominant,
      dominant_n = dominant_n, cluster_n = sum(members),
      dominant_proportion = dominant_n / sum(members), priority = priority,
      medoid_id = sample_data$participant_id[fit$id.med[[cluster_id]]],
      stringsAsFactors = FALSE
    )
  }))
  order_table <- order_table[order(
    order_table$priority, -order_table$dominant_proportion, order_table$medoid_id
  ), , drop = FALSE]
  order_table$cluster <- seq_len(nrow(order_table))
  mapping <- setNames(order_table$cluster, order_table$old_cluster)
  labels <- unname(mapping[as.character(old_labels)])
  medoids <- fit$id.med[order_table$old_cluster]
  labels_table <- order_table[, c(
    "cluster", "old_cluster", "dominant_occupation", "dominant_n",
    "cluster_n", "dominant_proportion", "medoid_id"
  )]
  list(labels = as.integer(labels), medoid_rows = as.integer(medoids),
       cluster_labels = labels_table)
}

subsampling_stability <- function(
  sample_data, variables, categorical_variables, full_labels, k,
  repetitions, seed
) {
  n <- nrow(sample_data)
  subsample_n <- floor(SUBSAMPLE_FRACTION * n)
  ari <- rep(NA_real_, repetitions)
  set.seed(seed)
  for (iteration in seq_len(repetitions)) {
    indices <- sort(sample.int(n, size = subsample_n, replace = FALSE))
    subsample <- sample_data[indices, , drop = FALSE]
    distance <- make_gower_distance(subsample, variables, categorical_variables)
    fit <- fit_pam(distance, k)
    ari[[iteration]] <- adjusted_rand_index(full_labels[indices], fit$clustering)
  }
  data.frame(
    iteration = seq_len(repetitions), adjusted_rand_index = ari,
    stringsAsFactors = FALSE
  )
}

summarize_stability <- function(resamples) {
  values <- resamples$adjusted_rand_index
  data.frame(
    repetitions = nrow(resamples),
    mean_adjusted_rand_index = mean(values, na.rm = TRUE),
    median_adjusted_rand_index = stats::median(values, na.rm = TRUE),
    q025_adjusted_rand_index = unname(stats::quantile(values, 0.025, na.rm = TRUE)),
    q975_adjusted_rand_index = unname(stats::quantile(values, 0.975, na.rm = TRUE)),
    stringsAsFactors = FALSE
  )
}

# -----------------------------------------------------------------------------
# Read and prepare data
# -----------------------------------------------------------------------------

data <- read_t1_file(input_path)
required_raw_variables <- c(
  "id", "submitdate", "timePoint", "Einv", "AttentionCheckFlag",
  "Prof", "Prof_other", "Geb", "Einko", "HHGroesse", "HHMinderj",
  paste0("Bew", 1:6), paste0("Habit", 1:4), paste0("VolSelf", 1:3),
  paste0("ActionPlan", 1:4), paste0("Int", 1:3), paste0("Con", 1:4),
  paste0("Att", 1:5), paste0("Norm", 1:6), paste0("IntVer", 1:3),
  paste0("MotivComp", 1:4), "BeschaeftProz", "UrlaubWochen",
  "StressWochen", "CareArbeit", "CareStunden", "Social", "AufWa",
  "StaProf", "EndProf", "BettZeit", "PausDau", "FreiDau", "BStel",
  "InBew", "OutBew", "Wohnort", "Ver", "Nat", "Mov"
)
assert_variables(data, required_raw_variables)

prepared <- data.frame(
  participant_id = trimws(data$id),
  time_point = numeric_prefix(data$timePoint),
  consent = trimws(data$Einv),
  attention_check_flag = numeric_prefix(data$AttentionCheckFlag),
  occupational_status = trimws(data$Prof),
  occupational_status_other = trimws(data$Prof_other),
  stringsAsFactors = FALSE
)
prepared$occupational_status[prepared$occupational_status == ""] <- NA_character_
prepared$occupational_status_other[prepared$occupational_status_other == ""] <- NA_character_

# Retained as medoid inputs, but not primary clustering variables.
prepared$automaticity <- (strict_row_mean(data, paste0("Habit", 1:4)) - 1) / 6
prepared$pa_specific_self_control <- (
  strict_row_mean(data, paste0("VolSelf", 1:3)) - 1
) / 4
prepared$action_planning <- (
  strict_row_mean(data, paste0("ActionPlan", 1:4)) - 1
) / 5
prepared$intention <- (strict_row_mean(data, paste0("Int", 1:3)) - 1) / 6
prepared$perceived_behavioral_control <- (
  strict_row_mean(data, paste0("Con", 1:4)) - 1
) / 6
prepared$attitude <- (strict_row_mean(data, paste0("Att", 1:5)) - 1) / 6
prepared$subjective_norm <- (strict_row_mean(data, paste0("Norm", 1:6)) - 1) / 6
prepared$intrinsic_motivation <- strict_row_mean(data, paste0("IntVer", 1:3)) / 4
prepared$motivational_competence <- (
  strict_row_mean(data, paste0("MotivComp", 1:4)) - 1
) / 4

prepared$workload_hours_per_week <- numeric_prefix(data$BeschaeftProz) / 100 * 40
prepared$holiday_weeks <- numeric_prefix(data$UrlaubWochen)
prepared$stress_weeks <- numeric_prefix(data$StressWochen)
care_hours <- numeric_prefix(data$CareStunden)
no_care_work <- tolower(trimws(data$CareArbeit)) %in% c("nein", "no", "n")
prepared$care_work_hours_per_week <- care_hours
prepared$care_work_hours_per_week[no_care_work] <- 0
prepared$social_hours_per_week <- numeric_prefix(data$Social)

vigorous_days <- numeric_prefix(data$Bew1)
vigorous_minutes <- numeric_prefix(data$Bew2)
moderate_days <- numeric_prefix(data$Bew3)
moderate_minutes <- numeric_prefix(data$Bew4)
light_days <- numeric_prefix(data$Bew5)
light_minutes <- numeric_prefix(data$Bew6)
vigorous_minutes[!is.na(vigorous_days) & vigorous_days == 0 & is.na(vigorous_minutes)] <- 0
moderate_minutes[!is.na(moderate_days) & moderate_days == 0 & is.na(moderate_minutes)] <- 0
light_minutes[!is.na(light_days) & light_days == 0 & is.na(light_minutes)] <- 0
prepared$pa_mvpa_hours_per_week <- (
  vigorous_days * vigorous_minutes + moderate_days * moderate_minutes
) / 60
prepared$pa_total_hours_per_week <- prepared$pa_mvpa_hours_per_week + (
  light_days * light_minutes
) / 60

prepared$wake_time_minutes <- clock_minutes(data$AufWa)
prepared$work_start_time_minutes <- clock_minutes(data$StaProf)
prepared$work_end_time_minutes <- clock_minutes(data$EndProf)
prepared$bed_time_minutes <- clock_minutes(data$BettZeit, bedtime = TRUE)
prepared$break_duration_minutes <- clock_minutes(data$PausDau)
prepared$leisure_duration_minutes <- clock_minutes(data$FreiDau)
prepared$workplace_distance_km <- numeric_prefix(data$BStel)
prepared$indoor_activity_distance_km <- numeric_prefix(data$InBew)
prepared$outdoor_activity_distance_km <- numeric_prefix(data$OutBew)

agreement_levels <- c(
  "Trifft voll und ganz zu" = 1, "Trifft eher zu" = 2,
  "Teils/teils" = 3, "Trifft eher nicht zu" = 4,
  "Trifft gar nicht zu" = 5
)
prepared$residential_sealing <- unname(agreement_levels[trimws(data$Ver)])
prepared$residential_nature_access <- unname(agreement_levels[trimws(data$Nat)])
prepared$residential_active_routes <- unname(agreement_levels[trimws(data$Mov)])
residence_levels <- c(
  "Ländliche Gemeinde / Dorf (unter 5.000 Einwohner:innen)" = 1,
  "Kleinstadt (5.000 bis unter 20.000 Einwohner:innen)" = 2,
  "Mittelstadt (20.000 bis unter 100.000 Einwohner:innen)" = 3,
  "Grossstadt (100.000 bis unter 500.000 Einwohner:innen)" = 4,
  "Großstadt (100.000 bis unter 500.000 Einwohner:innen)" = 4,
  "Metropole / Sehr große Stadt (500.000 Einwohner:innen oder mehr)" = 5,
  "Metropole / Sehr grosse Stadt (500.000 Einwohner:innen oder mehr)" = 5
)
prepared$residence_size_ordinal <- unname(residence_levels[trimws(data$Wohnort)])

birth_date <- parse_date(data$Geb)
submission_date <- parse_date(data$submitdate)
prepared$age_years <- as.numeric(submission_date - birth_date) / 365.2425
income_levels <- c(
  "< 1000" = 1, "1000 - 1500" = 2, "1500-2000" = 3,
  "2000-2500" = 4, "2500-3000" = 5, "3000-3500" = 6,
  "3500-4000" = 7, "4000-4500" = 8, "4500-5000" = 9,
  "> 5000" = 10
)
prepared$income_ordinal <- unname(income_levels[trimws(data$Einko)])
prepared$household_size <- numeric_prefix(data$HHGroesse)
prepared$household_minors <- numeric_prefix(data$HHMinderj)
one_person_missing <- !is.na(prepared$household_size) &
  prepared$household_size <= 1 & is.na(prepared$household_minors)
prepared$household_minors[one_person_missing] <- 0
prepared$normal_weeks_raw <- 52 - prepared$holiday_weeks - prepared$stress_weeks
prepared$phase_weeks_compatible <- !is.na(prepared$normal_weeks_raw) &
  prepared$normal_weeks_raw >= 0

psychological_variables <- c(
  "automaticity", "pa_specific_self_control", "action_planning", "intention",
  "perceived_behavioral_control", "attitude", "subjective_norm",
  "intrinsic_motivation", "motivational_competence"
)
weekly_variables <- c(
  "workload_hours_per_week", "holiday_weeks", "stress_weeks",
  "care_work_hours_per_week", "social_hours_per_week"
)
routine_variables <- c(
  "wake_time_minutes", "work_start_time_minutes", "work_end_time_minutes",
  "break_duration_minutes", "leisure_duration_minutes", "bed_time_minutes"
)
poi_variables <- c(
  "workplace_distance_km", "indoor_activity_distance_km",
  "outdoor_activity_distance_km"
)
residential_variables <- c(
  "residence_size_ordinal", "residential_sealing",
  "residential_nature_access", "residential_active_routes"
)
sociodemographic_variables <- c(
  "age_years", "income_ordinal", "household_size", "household_minors"
)
for (variable in psychological_variables) assert_range(prepared[[variable]], 0, 1, variable)
assert_range(prepared$workload_hours_per_week, 0, 40, "workload_hours_per_week")
assert_range(prepared$holiday_weeks, 0, 52, "holiday_weeks")
assert_range(prepared$stress_weeks, 0, 52, "stress_weeks")
assert_range(prepared$care_work_hours_per_week, 0, Inf, "care_work_hours_per_week")
assert_range(prepared$social_hours_per_week, 0, Inf, "social_hours_per_week")
assert_range(prepared$pa_mvpa_hours_per_week, 0, Inf, "pa_mvpa_hours_per_week")
assert_range(prepared$pa_total_hours_per_week, 0, Inf, "pa_total_hours_per_week")

is_t1 <- prepared$time_point == 1
has_consent <- tolower(prepared$consent) %in% c("ja", "yes", "y")
passes_attention_checks <- prepared$attention_check_flag == 0
base_valid <- is_t1 & has_consent & passes_attention_checks
base_valid[is.na(base_valid)] <- FALSE

# -----------------------------------------------------------------------------
# Primary and sensitivity definitions
# -----------------------------------------------------------------------------

primary_variables <- c(
  "occupational_status", weekly_variables, "pa_mvpa_hours_per_week"
)
variants <- list(
  primary = list(
    description = "Primary: occupation + weekly structure + MVPA",
    variables = primary_variables, categorical = "occupational_status",
    require_phase_compatibility = FALSE
  ),
  omit_pa = list(
    description = "Occupation + weekly structure, without PA",
    variables = c("occupational_status", weekly_variables),
    categorical = "occupational_status", require_phase_compatibility = FALSE
  ),
  total_pa = list(
    description = "Total PA instead of MVPA",
    variables = c("occupational_status", weekly_variables, "pa_total_hours_per_week"),
    categorical = "occupational_status", require_phase_compatibility = FALSE
  ),
  omit_occupation = list(
    description = "Weekly structure + MVPA, without occupation",
    variables = c(weekly_variables, "pa_mvpa_hours_per_week"),
    categorical = character(0), require_phase_compatibility = FALSE
  ),
  add_daily_routine = list(
    description = "Primary + typical daily routine",
    variables = c(primary_variables, routine_variables),
    categorical = "occupational_status", require_phase_compatibility = FALSE
  ),
  add_poi = list(
    description = "Primary + work and PA distances",
    variables = c(primary_variables, poi_variables),
    categorical = "occupational_status", require_phase_compatibility = FALSE
  ),
  add_residential_context = list(
    description = "Primary + residential context",
    variables = c(primary_variables, residential_variables),
    categorical = "occupational_status", require_phase_compatibility = FALSE
  ),
  add_sociodemographics = list(
    description = "Primary + age, income and household",
    variables = c(primary_variables, sociodemographic_variables),
    categorical = "occupational_status", require_phase_compatibility = FALSE
  ),
  add_routine_and_poi = list(
    description = "Primary + daily routine + distances",
    variables = c(primary_variables, routine_variables, poi_variables),
    categorical = "occupational_status", require_phase_compatibility = FALSE
  ),
  full_context = list(
    description = "Primary + routine + POI + residence + sociodemographics",
    variables = c(
      primary_variables, routine_variables, poi_variables,
      residential_variables, sociodemographic_variables
    ),
    categorical = "occupational_status", require_phase_compatibility = FALSE
  ),
  phase_compatible = list(
    description = "Primary restricted to holiday + stress <= 52 weeks",
    variables = primary_variables, categorical = "occupational_status",
    require_phase_compatibility = TRUE
  )
)

variant_definitions <- do.call(rbind, lapply(names(variants), function(name) {
  variant <- variants[[name]]
  data.frame(
    variant = name, description = variant$description,
    variables = paste(variant$variables, collapse = "; "),
    categorical_variables = paste(variant$categorical, collapse = "; "),
    require_phase_compatibility = variant$require_phase_compatibility,
    stringsAsFactors = FALSE
  )
}))
rownames(variant_definitions) <- NULL

# -----------------------------------------------------------------------------
# Fit all analyses
# -----------------------------------------------------------------------------

results <- list()
summary_rows <- list()
diagnostic_rows <- list()
stability_rows <- list()

for (variant_index in seq_along(variants)) {
  variant_name <- names(variants)[[variant_index]]
  variant <- variants[[variant_name]]
  complete_inputs <- stats::complete.cases(prepared[, variant$variables, drop = FALSE])
  included <- base_valid & complete_inputs
  if (variant$require_phase_compatibility) {
    included <- included & prepared$phase_weeks_compatible
  }
  included[is.na(included)] <- FALSE
  sample_data <- prepared[included, , drop = FALSE]
  if (nrow(sample_data) <= max(K_RANGE)) {
    stop("Too few complete cases for variant: ", variant_name, call. = FALSE)
  }

  override <- if (variant_name == "primary") PRIMARY_K_OVERRIDE else NA_integer_
  fitted <- fit_variant(
    sample_data, variant$variables, variant$categorical, override
  )
  canonical <- canonicalize_selected_solution(fitted$selected_fit, sample_data)
  repetitions <- if (variant_name == "primary") {
    PRIMARY_STABILITY_REPETITIONS
  } else {
    SENSITIVITY_STABILITY_REPETITIONS
  }
  resamples <- subsampling_stability(
    sample_data, variant$variables, variant$categorical, canonical$labels,
    fitted$selected_k, repetitions, RANDOM_SEED + variant_index * 1000L
  )
  stability <- summarize_stability(resamples)
  selected <- fitted$diagnostics[
    fitted$diagnostics$k == fitted$selected_k, , drop = FALSE
  ]
  results[[variant_name]] <- list(
    sample = sample_data, included = included, fit = fitted,
    canonical = canonical, stability_resamples = resamples,
    stability_summary = stability
  )
  summary_rows[[variant_index]] <- data.frame(
    variant = variant_name, description = variant$description,
    n = nrow(sample_data), variable_n = length(variant$variables),
    selected_k = fitted$selected_k,
    average_silhouette = selected$average_silhouette,
    silhouette_interpretation = selected$silhouette_interpretation,
    negative_silhouette_n = selected$negative_silhouette_n,
    minimum_cluster_size = selected$minimum_cluster_size,
    cluster_sizes = selected$cluster_sizes,
    mean_adjusted_rand_index = stability$mean_adjusted_rand_index,
    median_adjusted_rand_index = stability$median_adjusted_rand_index,
    q025_adjusted_rand_index = stability$q025_adjusted_rand_index,
    q975_adjusted_rand_index = stability$q975_adjusted_rand_index,
    stringsAsFactors = FALSE
  )
  variant_diagnostics <- fitted$diagnostics
  variant_diagnostics$variant <- variant_name
  diagnostic_rows[[variant_index]] <- variant_diagnostics[, c(
    "variant", setdiff(names(variant_diagnostics), "variant")
  )]
  stability$variant <- variant_name
  stability$selected_k <- fitted$selected_k
  stability_rows[[variant_index]] <- stability[, c(
    "variant", "selected_k", setdiff(names(stability), c("variant", "selected_k"))
  )]
}

sensitivity_summary <- do.call(rbind, summary_rows)
sensitivity_diagnostics <- do.call(rbind, diagnostic_rows)
sensitivity_stability <- do.call(rbind, stability_rows)
rownames(sensitivity_summary) <- NULL
rownames(sensitivity_diagnostics) <- NULL
rownames(sensitivity_stability) <- NULL

# Same-sample comparison: differences then cannot be attributed to missingness.
common_variant_names <- c(
  "primary", "add_daily_routine", "add_poi", "add_residential_context",
  "add_sociodemographics", "add_routine_and_poi", "full_context"
)
common_variables <- unique(unlist(lapply(
  variants[common_variant_names], function(x) x$variables
)))
common_included <- base_valid & stats::complete.cases(
  prepared[, common_variables, drop = FALSE]
)
common_included[is.na(common_included)] <- FALSE
common_sample <- prepared[common_included, , drop = FALSE]
common_sample_comparison <- do.call(rbind, lapply(common_variant_names, function(name) {
  variant <- variants[[name]]
  fitted <- fit_variant(common_sample, variant$variables, variant$categorical)
  selected <- fitted$diagnostics[
    fitted$diagnostics$k == fitted$selected_k, , drop = FALSE
  ]
  data.frame(
    variant = name, n = nrow(common_sample), selected_k = fitted$selected_k,
    average_silhouette = selected$average_silhouette,
    negative_silhouette_n = selected$negative_silhouette_n,
    minimum_cluster_size = selected$minimum_cluster_size,
    cluster_sizes = selected$cluster_sizes, stringsAsFactors = FALSE
  )
}))
rownames(common_sample_comparison) <- NULL

# -----------------------------------------------------------------------------
# Primary outputs
# -----------------------------------------------------------------------------

primary <- results$primary
primary_sample <- primary$sample
primary_fit <- primary$fit
primary_labels <- primary$canonical$labels
primary_medoids <- primary$canonical$medoid_rows
primary_k <- primary_fit$selected_k
primary_silhouette <- cluster::silhouette(primary_labels, primary_fit$distance)
primary_widths <- primary_silhouette[, "sil_width"]

sample_flow <- data.frame(
  step = c(
    "Imported records", "Measurement time point T1", "Consent provided",
    "Passed attention-check rule", "Base-valid T1 records",
    "Complete occupational status", "Complete primary clustering inputs",
    "Primary inputs and holiday + stress <= 52 weeks"
  ),
  n = c(
    nrow(prepared), sum(is_t1, na.rm = TRUE),
    sum(is_t1 & has_consent, na.rm = TRUE),
    sum(is_t1 & has_consent & passes_attention_checks, na.rm = TRUE),
    sum(base_valid), sum(base_valid & !is.na(prepared$occupational_status)),
    nrow(primary_sample), sum(results$phase_compatible$included)
  ),
  stringsAsFactors = FALSE
)

membership_all_k <- data.frame(
  participant_id = primary_sample$participant_id, stringsAsFactors = FALSE
)
for (k in K_RANGE) {
  fit <- primary_fit$fits[[paste0("k", k)]]
  silhouette <- cluster::silhouette(fit$clustering, primary_fit$distance)
  membership_all_k[[paste0("cluster_k", k)]] <- as.integer(fit$clustering)
  membership_all_k[[paste0("silhouette_k", k)]] <- silhouette[, "sil_width"]
}

selected_membership <- data.frame(
  participant_id = primary_sample$participant_id,
  occupational_status = primary_sample$occupational_status,
  occupational_status_other = primary_sample$occupational_status_other,
  cluster = primary_labels, silhouette_width = primary_widths,
  is_medoid = seq_len(nrow(primary_sample)) %in% primary_medoids,
  stringsAsFactors = FALSE
)

numeric_primary_variables <- setdiff(primary_variables, "occupational_status")
primary_profiles <- do.call(rbind, lapply(seq_len(primary_k), function(cluster_id) {
  cluster_data <- primary_sample[
    primary_labels == cluster_id, numeric_primary_variables, drop = FALSE
  ]
  data.frame(
    cluster = cluster_id, n = nrow(cluster_data),
    variable = numeric_primary_variables,
    mean = vapply(cluster_data, mean, numeric(1), na.rm = TRUE),
    median = vapply(cluster_data, stats::median, numeric(1), na.rm = TRUE),
    sd = vapply(cluster_data, stats::sd, numeric(1), na.rm = TRUE),
    minimum = vapply(cluster_data, min, numeric(1), na.rm = TRUE),
    maximum = vapply(cluster_data, max, numeric(1), na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}))
rownames(primary_profiles) <- NULL

occupation_composition <- as.data.frame(table(
  cluster = primary_labels,
  occupational_status = primary_sample$occupational_status,
  useNA = "ifany"
), stringsAsFactors = FALSE)
occupation_composition <- occupation_composition[occupation_composition$Freq > 0, ]
names(occupation_composition)[names(occupation_composition) == "Freq"] <- "n"
cluster_totals <- table(primary_labels)
occupation_composition$within_cluster_proportion <- occupation_composition$n /
  as.numeric(cluster_totals[as.character(occupation_composition$cluster)])

medoid_output_variables <- c(
  "participant_id", "occupational_status", "occupational_status_other",
  psychological_variables, "workload_hours_per_week",
  "pa_mvpa_hours_per_week", "pa_total_hours_per_week", "holiday_weeks",
  "stress_weeks", "normal_weeks_raw", "phase_weeks_compatible",
  "care_work_hours_per_week", "social_hours_per_week", routine_variables,
  poi_variables, residential_variables, sociodemographic_variables
)
medoid_personas <- primary_sample[
  primary_medoids, medoid_output_variables, drop = FALSE
]
medoid_personas$cluster <- seq_len(primary_k)
required_simulation_inputs <- c(
  psychological_variables, "workload_hours_per_week",
  "pa_mvpa_hours_per_week", "holiday_weeks", "stress_weeks",
  "care_work_hours_per_week", "social_hours_per_week",
  routine_variables, poi_variables
)
medoid_personas$complete_required_simulation_inputs <- stats::complete.cases(
  primary_sample[primary_medoids, required_simulation_inputs, drop = FALSE]
)
medoid_personas <- merge(
  medoid_personas,
  primary$canonical$cluster_labels[, c(
    "cluster", "dominant_occupation", "dominant_n", "cluster_n",
    "dominant_proportion"
  )],
  by = "cluster", sort = TRUE
)
if (any(!medoid_personas$complete_required_simulation_inputs)) {
  warning(
    "At least one selected medoid has a missing required simulation input. ",
    "Inspect 11_primary_medoid_personas.csv before using the personas."
  )
}

# Flag medoid values in the outer 5% of their own cluster. A medoid is only
# guaranteed to be central in the variables used to create the clusters.
numeric_medoid_variables <- medoid_output_variables[vapply(
  primary_sample[, medoid_output_variables, drop = FALSE], is.numeric, logical(1)
)]
medoid_diagnostic_rows <- list()
row_index <- 1L
for (cluster_id in seq_len(primary_k)) {
  members <- primary_labels == cluster_id
  medoid_row <- primary_medoids[[cluster_id]]
  for (variable in numeric_medoid_variables) {
    values <- primary_sample[[variable]][members]
    values <- values[!is.na(values)]
    value <- primary_sample[[variable]][medoid_row]
    percentile <- if (is.na(value) || length(values) == 0L) {
      NA_real_
    } else if (length(unique(values)) == 1L) {
      0.5
    } else {
      (sum(values < value) + 0.5 * sum(values == value)) / length(values)
    }
    medoid_diagnostic_rows[[row_index]] <- data.frame(
      cluster = cluster_id,
      participant_id = primary_sample$participant_id[medoid_row],
      variable = variable, value = value,
      within_cluster_percentile = percentile,
      used_in_primary_clustering = variable %in% primary_variables,
      outer_five_percent = !is.na(percentile) &
        (percentile <= 0.05 | percentile >= 0.95),
      stringsAsFactors = FALSE
    )
    row_index <- row_index + 1L
  }
}
medoid_representativeness <- do.call(rbind, medoid_diagnostic_rows)
rownames(medoid_representativeness) <- NULL

variable_mapping <- data.frame(
  derived_variable = c(
    "occupational_status", "workload_hours_per_week", "holiday_weeks",
    "stress_weeks", "care_work_hours_per_week", "social_hours_per_week",
    "pa_mvpa_hours_per_week", "pa_total_hours_per_week", routine_variables,
    poi_variables, residential_variables, sociodemographic_variables
  ),
  source_or_derivation = c(
    "Prof", "BeschaeftProz / 100 * 40", "UrlaubWochen", "StressWochen",
    "CareStunden; 0 if CareArbeit = Nein", "Social",
    "((Bew1 * Bew2) + (Bew3 * Bew4)) / 60",
    "MVPA + (Bew5 * Bew6) / 60",
    "AlltagAbl[AufWa], minutes after midnight",
    "AlltagAbl[StaProf], minutes after midnight",
    "AlltagAbl[EndProf], minutes after midnight",
    "AlltagAbl[PausDau], duration minutes",
    "AlltagAbl[FreiDau], duration minutes",
    "AlltagAbl[BettZeit], after midnight > 1440",
    "EntfernPOI[BStel]", "EntfernPOI[InBew]", "EntfernPOI[OutBew]",
    "Wohnort, ordinal 1-5", "UmgebTyp[Ver], ordinal response 1-5",
    "UmgebTyp[Nat], ordinal response 1-5",
    "UmgebTyp[Mov], ordinal response 1-5",
    "Difference between Geb and submitdate in years", "Einko, ordinal 1-10",
    "HHGroesse", "HHMinderj; missing 0 only for one-person households"
  ),
  primary_clustering_variable = c(
    TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, FALSE,
    rep(FALSE, length(routine_variables) + length(poi_variables) +
      length(residential_variables) + length(sociodemographic_variables))
  ),
  stringsAsFactors = FALSE
)

# -----------------------------------------------------------------------------
# Save results and figures
# -----------------------------------------------------------------------------

write_utf8_csv(sample_flow, "01_sample_flow.csv")
write_utf8_csv(variant_definitions, "02_analysis_variant_definitions.csv")
write_utf8_csv(prepared, "03_prepared_t1_inputs.csv")
write_utf8_csv(variable_mapping, "04_variable_mapping.csv")
write_utf8_csv(primary_fit$diagnostics, "05_primary_cluster_diagnostics.csv")
write_utf8_csv(primary$stability_summary, "06_primary_stability_summary.csv")
write_utf8_csv(primary$stability_resamples, "07_primary_stability_resamples.csv")
write_utf8_csv(membership_all_k, "08_primary_membership_all_k.csv")
write_utf8_csv(selected_membership, "09_primary_selected_membership.csv")
write_utf8_csv(primary_profiles, "10_primary_cluster_profiles.csv")
write_utf8_csv(medoid_personas, "11_primary_medoid_personas.csv")
write_utf8_csv(occupation_composition, "12_primary_occupation_composition.csv")
write_utf8_csv(primary$canonical$cluster_labels, "13_primary_cluster_labels.csv")
write_utf8_csv(medoid_representativeness, "14_medoid_representativeness_check.csv")
write_utf8_csv(sensitivity_summary, "15_sensitivity_summary.csv")
write_utf8_csv(sensitivity_diagnostics, "16_sensitivity_diagnostics_all_k.csv")
write_utf8_csv(sensitivity_stability, "17_sensitivity_stability_summary.csv")
write_utf8_csv(common_sample_comparison, "18_common_sample_comparison.csv")

grDevices::png(
  file.path(output_dir, "19_primary_average_silhouette_by_k.png"),
  width = 1800, height = 1200, res = 180
)
graphics::plot(
  primary_fit$diagnostics$k, primary_fit$diagnostics$average_silhouette,
  type = "b", pch = 19, xlab = "Number of clusters (k)",
  ylab = "Average silhouette width",
  main = "Primary PAM solution: cluster separation across k",
  ylim = range(c(0, primary_fit$diagnostics$average_silhouette))
)
graphics::abline(h = c(0.25, 0.50), lty = 2, col = c("grey50", "grey70"))
graphics::text(
  primary_fit$diagnostics$k, primary_fit$diagnostics$average_silhouette,
  labels = sprintf("%.3f", primary_fit$diagnostics$average_silhouette),
  pos = 3, cex = 0.8
)
grDevices::dev.off()

grDevices::png(
  file.path(output_dir, "20_primary_selected_silhouette.png"),
  width = 1800, height = 1400, res = 180
)
graphics::plot(
  primary_silhouette,
  main = sprintf("Primary PAM silhouette plot (k = %d)", primary_k),
  col = seq_len(primary_k), border = NA
)
grDevices::dev.off()

grDevices::png(
  file.path(output_dir, "21_sensitivity_selected_silhouettes.png"),
  width = 2200, height = 1500, res = 180
)
bar_positions <- graphics::barplot(
  sensitivity_summary$average_silhouette,
  names.arg = sensitivity_summary$variant, las = 2,
  col = ifelse(sensitivity_summary$variant == "primary", "#377EB8", "grey70"),
  border = NA, ylab = "Average silhouette width",
  main = "Selected PAM solution for each analysis variant",
  ylim = c(0, max(sensitivity_summary$average_silhouette) * 1.18)
)
graphics::abline(h = c(0.25, 0.50), lty = 2, col = c("grey40", "grey60"))
graphics::text(
  bar_positions, sensitivity_summary$average_silhouette,
  labels = sprintf(
    "k=%d\n%.3f", sensitivity_summary$selected_k,
    sensitivity_summary$average_silhouette
  ),
  pos = 3, cex = 0.75
)
grDevices::dev.off()

primary_row <- sensitivity_summary[sensitivity_summary$variant == "primary", , drop = FALSE]
omit_pa_row <- sensitivity_summary[sensitivity_summary$variant == "omit_pa", , drop = FALSE]
phase_row <- sensitivity_summary[
  sensitivity_summary$variant == "phase_compatible", , drop = FALSE
]
selection_summary <- c(
  "AIcoPA T1 persona clustering v1.1", "",
  paste0("Input file: ", normalizePath(input_path, winslash = "/", mustWork = TRUE)),
  paste0("Imported records: n = ", nrow(prepared)),
  paste0("Primary complete-case sample: n = ", nrow(primary_sample)),
  paste0("Candidate k values: ", paste(K_RANGE, collapse = ", ")),
  paste0("Minimum permitted cluster size: ", MIN_CLUSTER_SIZE), "",
  paste0("Selected primary k: ", primary_k),
  paste0("Cluster sizes: ", primary_row$cluster_sizes),
  paste0("Average silhouette: ", sprintf("%.4f", primary_row$average_silhouette)),
  paste0("Interpretation: ", primary_row$silhouette_interpretation),
  paste0("Mean 80% subsampling ARI: ", sprintf("%.4f", primary_row$mean_adjusted_rand_index)),
  paste0(
    "95% subsampling ARI interval: ",
    sprintf("%.4f", primary_row$q025_adjusted_rand_index), " to ",
    sprintf("%.4f", primary_row$q975_adjusted_rand_index)
  ), "", "Primary variables:", paste(primary_variables, collapse = ", "), "",
  paste0(
    "Sensitivity without PA: k = ", omit_pa_row$selected_k,
    ", silhouette = ", sprintf("%.4f", omit_pa_row$average_silhouette)
  ),
  paste0(
    "Phase-compatible sensitivity: n = ", phase_row$n,
    ", k = ", phase_row$selected_k,
    ", silhouette = ", sprintf("%.4f", phase_row$average_silhouette)
  ), "",
  paste(
    "Interpretive limitation: occupational status is a primary clustering",
    "variable. These are occupation-informed profiles, not latent types",
    "discovered independently of occupation."
  ),
  paste(
    "Medoids are representative in primary clustering variables only. Review",
    "14_medoid_representativeness_check.csv before transferring all remaining",
    "psychological, routine, and environmental values to the simulation."
  ),
  paste(
    "The raw category 'Sonstiges' is heterogeneous. Describe its free-text",
    "responses carefully or recode them using a prespecified rule."
  )
)
writeLines(selection_summary, file.path(output_dir, "22_analysis_summary.txt"), useBytes = TRUE)
writeLines(
  capture.output(utils::sessionInfo()),
  file.path(output_dir, "23_session_info.txt"), useBytes = TRUE
)

message("Analysis completed.")
message("Imported records: n = ", nrow(prepared))
message("Primary analysis sample: n = ", nrow(primary_sample))
message("Selected primary k: ", primary_k)
message(
  "Average silhouette width: ", sprintf("%.4f", primary_row$average_silhouette),
  " (", primary_row$silhouette_interpretation, ")"
)
message(
  "Mean 80% subsampling ARI: ",
  sprintf("%.4f", primary_row$mean_adjusted_rand_index)
)
message("Results written to: ", normalizePath(output_dir, winslash = "/", mustWork = TRUE))
