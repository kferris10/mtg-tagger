#!/usr/bin/env Rscript
# Render accuracy-report.qmd for a given prompt file and model.
#
# Usage (from project root):
#   Rscript analysis/render_accuracy_report.R <prompt_file> <model>
#
# Examples:
#   Rscript analysis/render_accuracy_report.R prompts/prompt.md claude-sonnet-4-20250514
#   Rscript analysis/render_accuracy_report.R prompts/prompt2.md claude-sonnet-4-6

args <- commandArgs(trailingOnly = TRUE)

prompt_file  <- if (length(args) >= 1) args[1] else "prompts/prompt.md"
model_filter <- if (length(args) >= 2) args[2] else "claude-sonnet-4-20250514"

# Derive output filename from prompt and model
prompt_slug <- tools::file_path_sans_ext(basename(prompt_file))
model_slug  <- gsub("[^a-zA-Z0-9]", "-", model_filter)
output_file <- paste0("accuracy-report-", prompt_slug, "-", model_slug, ".html")

message("Rendering: analysis/", output_file)
message("  prompt_file  = ", prompt_file)
message("  model_filter = ", model_filter)

setwd("analysis")

quarto::quarto_render(
  input          = "accuracy-report.qmd",
  execute_params = list(
    prompt_file  = prompt_file,
    model_filter = model_filter
  ),
  output_file    = output_file
)

message("Done: analysis/", output_file)
