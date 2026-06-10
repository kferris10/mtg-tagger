#!/usr/bin/env Rscript
# Loads analysis/tags-labeled - KF.csv into public.labeled_kf (PostgreSQL).
# Overwrites the table on each run so re-running is safe.
#
# Usage (from project root):
#   Rscript analysis/load_labeled_kf.R

library(DBI)
library(stringr)
library(RPostgres)
library(jsonlite)

readRenviron(".env")

# Parse "ramp: A-Tier; card_advantage: B-Tier" → {"ramp":"A-Tier","card_advantage":"B-Tier"}
parse_tags_json <- function(x) {
  if (is.na(x) || trimws(x) == "") return("{}")
  pairs <- trimws(strsplit(x, ";")[[1]])
  pairs <- pairs[nchar(pairs) > 0]
  result <- list()
  for (p in pairs) {
    kv <- strsplit(p, ":", fixed = TRUE)[[1]]
    if (length(kv) >= 2) {
      result[[trimws(kv[1])]] <- trimws(paste(kv[-1], collapse = ":"))
    }
  }
  jsonlite::toJSON(result, auto_unbox = TRUE)
}

csv_path <- "analysis/tags-labeled - KF.csv"
df <- read.csv(csv_path, stringsAsFactors = FALSE, check.names = FALSE)
df$KF <- str_replace_all(df$KF, "card_draw(?!_)", "card_advantage")
df[["KF"]] <- sapply(df[["KF"]], parse_tags_json)

con <- DBI::dbConnect(
  RPostgres::Postgres(),
  host     = Sys.getenv("DB_HOST"),
  port     = as.integer(Sys.getenv("DB_PORT")),
  user     = Sys.getenv("DB_USER"),
  password = Sys.getenv("DB_PASSWORD"),
  dbname   = "mtgcards"
)

DBI::dbWriteTable(
  con,
  DBI::Id(schema = "public", table = "labeled_kf"),
  df,
  overwrite = TRUE,
  row.names = FALSE
)

DBI::dbExecute(con, 'ALTER TABLE public.labeled_kf ALTER COLUMN "KF" TYPE jsonb USING "KF"::jsonb')
DBI::dbExecute(con, 'ALTER TABLE public.labeled_kf RENAME COLUMN "KF" TO kf')

n <- nrow(df)
message("Wrote ", n, " rows to public.labeled_kf with KF as jsonb")

DBI::dbDisconnect(con)
