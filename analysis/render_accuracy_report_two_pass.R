#!/usr/bin/env Rscript
# Render accuracy-report-two-pass.qmd for a given prompt, feedback prompt, and model.
#
# Usage (from project root):
#   Rscript analysis/render_accuracy_report_two_pass.R <prompt_file> <feedback_prompt_file> <model>
#
# Example:
#   Rscript analysis/render_accuracy_report_two_pass.R prompts/prompt10.md prompts/feedback_prompt.md claude-opus-4-8

args <- commandArgs(trailingOnly = TRUE)

prompt_file          <- if (length(args) >= 1) args[1] else "prompts/prompt10.md"
feedback_prompt_file <- if (length(args) >= 2) args[2] else "prompts/feedback_prompt.md"
model_filter         <- if (length(args) >= 3) args[3] else "claude-opus-4-8"

prompt_slug   <- tools::file_path_sans_ext(basename(prompt_file))
feedback_slug <- tools::file_path_sans_ext(basename(feedback_prompt_file))
model_slug    <- gsub("[^a-zA-Z0-9]", "-", model_filter)
output_file   <- paste0("accuracy-report-two-pass-", prompt_slug, "-", feedback_slug, "-", model_slug, ".html")

message("Rendering: analysis/", output_file)
message("  prompt_file          = ", prompt_file)
message("  feedback_prompt_file = ", feedback_prompt_file)
message("  model_filter         = ", model_filter)

setwd("analysis")

quarto::quarto_render(
  input          = "accuracy-report-two-pass.qmd",
  execute_params = list(
    prompt_file          = prompt_file,
    feedback_prompt_file = feedback_prompt_file,
    model_filter         = model_filter
  ),
  output_file    = output_file
)

message("Done: analysis/", output_file)
