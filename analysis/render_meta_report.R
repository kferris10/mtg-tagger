#!/usr/bin/env Rscript
# Render meta-report.qmd — no parameters needed.
#
# Usage (from project root):
#   Rscript analysis/render_meta_report.R

setwd("analysis")

quarto::quarto_render(
  input       = "meta-report.qmd",
  output_file = "meta-report.html"
)

message("Done: analysis/meta-report.html")
