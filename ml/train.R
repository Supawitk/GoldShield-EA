#!/usr/bin/env Rscript
# ──────────────────────────────────────────────────────────
# GoldShield EA — R Model Training
# ──────────────────────────────────────────────────────────
# Trains forecasting models on XAUUSD candle data exported
# from the PostgreSQL database.
#
# Prerequisites:
#   install.packages(c("forecast", "randomForest", "caret", "jsonlite"))
#
# Usage:
#   Rscript ml/train.R                      # auto.arima by default
#   Rscript ml/train.R randomForest         # random forest classifier
#   Rscript ml/train.R ets                  # exponential smoothing
# ──────────────────────────────────────────────────────────

library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)
model_type <- ifelse(length(args) > 0, args[1], "arima")

# Load data
cat("Loading candle data ...\n")
data_path <- file.path(dirname(sys.frame(1)$ofile %||% "."), "candles_export.csv")
if (!file.exists(data_path)) {
  # Try relative path
  data_path <- "ml/candles_export.csv"
}
if (!file.exists(data_path)) {
  stop("candles_export.csv not found. Run: python ml/train_model.py --export-r")
}

df <- read.csv(data_path, stringsAsFactors = FALSE)
cat(sprintf("  Loaded %d rows\n", nrow(df)))

close_prices <- df$close
n <- length(close_prices)
split_idx <- floor(n * 0.8)
train_data <- close_prices[1:split_idx]
test_data <- close_prices[(split_idx + 1):n]

results <- list(model = model_type, language = "R")

# ── ARIMA ────────────────────────────────────────────────
if (model_type == "arima") {
  library(forecast)

  cat("Training auto.arima ...\n")
  ts_train <- ts(train_data, frequency = 24)
  fit <- auto.arima(ts_train)
  preds <- forecast(fit, h = length(test_data))

  mae <- mean(abs(as.numeric(preds$mean) - test_data))
  rmse <- sqrt(mean((as.numeric(preds$mean) - test_data)^2))

  results$mae <- round(mae, 4)
  results$rmse <- round(rmse, 4)
  results$order <- paste(arimaorder(fit), collapse = ",")

  cat(sprintf("  ARIMA Order: (%s)\n", results$order))
  cat(sprintf("  MAE:  %.4f\n", mae))
  cat(sprintf("  RMSE: %.4f\n", rmse))

# ── ETS (Exponential Smoothing) ──────────────────────────
} else if (model_type == "ets") {
  library(forecast)

  cat("Training ETS ...\n")
  ts_train <- ts(train_data, frequency = 24)
  fit <- ets(ts_train)
  preds <- forecast(fit, h = length(test_data))

  mae <- mean(abs(as.numeric(preds$mean) - test_data))
  rmse <- sqrt(mean((as.numeric(preds$mean) - test_data)^2))

  results$mae <- round(mae, 4)
  results$rmse <- round(rmse, 4)
  results$ets_model <- fit$method

  cat(sprintf("  ETS Model: %s\n", fit$method))
  cat(sprintf("  MAE:  %.4f\n", mae))
  cat(sprintf("  RMSE: %.4f\n", rmse))

# ── Random Forest ────────────────────────────────────────
} else if (model_type == "randomForest") {
  library(randomForest)
  library(caret)

  cat("Engineering features ...\n")

  df$return_val <- c(NA, diff(df$close) / head(df$close, -1))
  df$target <- factor(ifelse(c(tail(df$return_val, -1), NA) > 0, "UP", "DOWN"))
  df$body <- abs(df$close - df$open)
  df$upper_wick <- df$high - pmax(df$open, df$close)
  df$lower_wick <- pmin(df$open, df$close) - df$low

  # Rolling features
  df$ma_50 <- stats::filter(df$close, rep(1/50, 50), sides = 1)
  df$ma_200 <- stats::filter(df$close, rep(1/200, 200), sides = 1)

  df <- na.omit(df)

  feature_cols <- c("close", "volume", "body", "upper_wick",
                     "lower_wick", "ma_50", "ma_200")

  split_idx <- floor(nrow(df) * 0.8)
  train_df <- df[1:split_idx, ]
  test_df <- df[(split_idx + 1):nrow(df), ]

  cat(sprintf("Training Random Forest on %d samples ...\n", nrow(train_df)))
  rf <- randomForest(
    x = train_df[, feature_cols],
    y = train_df$target,
    ntree = 100,
    importance = TRUE
  )

  preds <- predict(rf, test_df[, feature_cols])
  cm <- confusionMatrix(preds, test_df$target)

  results$accuracy <- round(cm$overall["Accuracy"], 4)
  results$test_samples <- nrow(test_df)
  results$importance <- as.list(round(importance(rf)[, "MeanDecreaseGini"], 4))

  cat(sprintf("  Accuracy: %.1f%%\n", cm$overall["Accuracy"] * 100))
  cat("  Feature Importance:\n")
  imp <- sort(importance(rf)[, "MeanDecreaseGini"], decreasing = TRUE)
  for (nm in names(imp)) {
    cat(sprintf("    %-18s %.4f\n", nm, imp[nm]))
  }

} else {
  stop(sprintf("Unknown model type: %s. Use: arima, ets, randomForest", model_type))
}

# Save results
out_path <- file.path(dirname(data_path), "results_r.json")
write(toJSON(results, auto_unbox = TRUE, pretty = TRUE), out_path)
cat(sprintf("\nResults saved to %s\n", out_path))
