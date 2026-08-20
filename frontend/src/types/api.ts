// frontend/src/types/api.ts
// Mirrors backend/app/schemas/*.py — keep in sync with the FastAPI response models.

export type UserRole = 'owner' | 'analyst' | 'viewer';

export interface User {
  id: string;
  company_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  country: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type DatasetStatus = 'uploaded' | 'cleaning' | 'cleaned' | 'analyzed' | 'failed';
export type FileType = 'csv' | 'xlsx';

export interface DatasetColumn {
  id: string;
  name: string;
  dtype: string;
  null_count: number;
  unique_count: number;
  min_value: number | null;
  max_value: number | null;
  mean_value: number | null;
  std_value: number | null;
  is_target_candidate: boolean;
}

export interface Dataset {
  id: string;
  company_id: string;
  name: string;
  original_filename: string;
  file_type: FileType;
  status: DatasetStatus;
  row_count: number | null;
  column_count: number | null;
  created_at: string;
}

export interface DatasetDetail extends Dataset {
  columns: DatasetColumn[];
}

export interface DatasetPreview {
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
  preview_rows: number;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  field_errors: Record<string, unknown> | null;
}

export interface ApiErrorResponse {
  detail: ApiErrorDetail;
}

// --- Analytics: descriptive ------------------------------------------------

export interface NumericColumnStats {
  column: string;
  count: number;
  missing: number;
  mean: number | null;
  median: number | null;
  mode: number | null;
  variance: number | null;
  std: number | null;
  skewness: number | null;
  kurtosis: number | null;
  q1: number | null;
  q3: number | null;
  iqr: number | null;
  min: number | null;
  max: number | null;
}

export interface CategoricalColumnStats {
  column: string;
  count: number;
  missing: number;
  unique: number;
  top_values: Record<string, number>;
}

export interface DescriptiveResult {
  dataset_id: string;
  row_count: number;
  numeric_columns: NumericColumnStats[];
  categorical_columns: CategoricalColumnStats[];
  correlation: { columns: string[]; pearson: number[][]; spearman: number[][] } | null;
  target_candidates: string[];
  missingness_summary: Record<string, number>;
}

// --- Analytics: regression ---------------------------------------------------

export interface CoefficientResult {
  term: string;
  coefficient: number;
  std_error: number;
  t_stat: number;
  p_value: number;
  ci_lower: number;
  ci_upper: number;
  significant: boolean;
  interpretation: string;
}

export interface RegressionResult {
  dataset_id: string;
  model_id: string;
  formula: string;
  n_observations: number;
  r_squared: number;
  adj_r_squared: number;
  f_statistic: number;
  f_p_value: number;
  aic: number;
  bic: number;
  coefficients: CoefficientResult[];
  interpretation: string;
}

// --- Analytics: ANOVA ------------------------------------------------------------

export interface TukeyPairResult {
  group1: string;
  group2: string;
  mean_diff: number;
  p_adj: number;
  lower: number;
  upper: number;
  reject_null: boolean;
}

export interface ANOVAResult {
  dataset_id: string;
  factor: string;
  response: string;
  groups: string[];
  ss_between: number;
  ss_within: number;
  df_between: number;
  df_within: number;
  ms_between: number;
  ms_within: number;
  f_statistic: number;
  p_value: number;
  eta_squared: number;
  significant: boolean;
  tukey: TukeyPairResult[];
  interpretation: string;
}

// --- Analytics: validation -----------------------------------------------------

export type Verdict = 'pass' | 'warn' | 'fail';

export interface TestResult {
  statistic: number;
  p_value: number | null;
  threshold: string;
  verdict: Verdict;
  meaning: string;
}

export interface VIFResult {
  feature: string;
  vif: number;
  verdict: Verdict;
}

export interface ValidationResult {
  model_id: string;
  dataset_id: string;
  normality: TestResult;
  qq_plot: { theoretical: number[]; sample: number[] };
  heteroscedasticity: TestResult;
  autocorrelation: TestResult;
  multicollinearity: { vif: VIFResult[]; verdict: Verdict; meaning: string };
  influence: {
    threshold: number;
    influential_count: number;
    influential_ratio: number;
    influential_indices: number[];
    verdict: Verdict;
    meaning: string;
  };
  residual_vs_fitted: { fitted: number[]; residuals: number[] };
  residual_histogram: { bin_edges: number[]; counts: number[] };
  overall_verdict: Verdict;
  remediation: string[];
}

// --- Analytics: forecast ---------------------------------------------------------

export interface ForecastResult {
  dataset_id: string;
  model_id: string;
  forecast_id: string;
  time_column: string;
  target: string;
  horizon: number;
  stationarity: { test: string; statistic: number; p_value: number; verdict: string; meaning: string }[];
  arima_order: number[] | null;
  arima_metrics: { mae: number; rmse: number; mape: number };
  ets_config: Record<string, unknown> | null;
  ets_metrics: { mae: number; rmse: number; mape: number };
  best_model: 'arima' | 'ets';
  history: { dates: string[]; actual: (number | null)[]; fitted: (number | null)[] };
  forecast: {
    dates: string[];
    point: number[];
    ci_lower_80: number[];
    ci_upper_80: number[];
    ci_lower_95: number[];
    ci_upper_95: number[];
  };
  interpretation: string;
}

// --- Analytics: segmentation --------------------------------------------------

export interface ClusterProfile {
  cluster: number;
  name: string;
  size: number;
  share: number;
  feature_means: Record<string, number>;
}

export interface SegmentationResult {
  segment_id: string;
  dataset_id: string;
  algorithm: string;
  n_clusters: number | null;
  silhouette: number | null;
  elbow: { k: number; inertia: number; silhouette: number | null }[];
  clusters: ClusterProfile[];
  pca_explained_variance: number[];
  pca_points: { x: number; y: number; cluster: number }[];
  centroids: Record<string, Record<string, number>>;
  interpretation: string;
}

// --- Analytics: KPIs -----------------------------------------------------------

export type KPIType = 'cltv' | 'churn' | 'take_rate' | 'cac' | 'wom' | 'revenue_growth' | 'gross_margin';
export type KPIStatus = 'computed' | 'insufficient_data';

export interface KPIItem {
  kpi_type: KPIType;
  status: KPIStatus;
  value: number | null;
  formula: string;
  data_coverage: { rows_used: number; rows_total: number; coverage_ratio: number };
  missing: string[];
  trend: { direction: 'up' | 'down' | 'flat'; change_pct: number | null } | null;
  interpretation: string;
  extra: Record<string, unknown> | null;
}

export interface KPISuiteResult {
  dataset_id: string;
  kpis: KPIItem[];
  supporting_metrics: { name: string; value: number | null; formula: string; status: KPIStatus }[];
  interpretation: string;
}

// --- Decisions -----------------------------------------------------------------

export type DecisionPriority = 'high' | 'medium' | 'low';
export type DecisionStatus = 'open' | 'acknowledged' | 'applied' | 'dismissed';

export interface Decision {
  id: string;
  priority: DecisionPriority;
  category: string;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  recommended_action: string;
  confidence: 'high' | 'medium' | 'low';
  status: DecisionStatus;
}

// --- Jobs -------------------------------------------------------------------------

export type JobType =
  | 'descriptive' | 'regression' | 'anova' | 'validation'
  | 'forecast' | 'segmentation' | 'kpi' | 'decision';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface AnalysisJob {
  id: string;
  company_id: string;
  dataset_id: string;
  type: JobType;
  config: Record<string, unknown>;
  status: JobStatus;
  progress: number;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
}

// --- Reports -----------------------------------------------------------------------

export type ReportFormat = 'pdf' | 'xlsx';
export type ReportType = 'executive' | 'raw_results';

export interface Report {
  id: string;
  company_id: string;
  type: ReportType;
  format: ReportFormat;
  storage_path: string;
  created_at: string;
}
