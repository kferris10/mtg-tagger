library(tidyverse); library(jsonlite); library(DBI)
con <- DBI::dbConnect(RPostgres::Postgres(),
  host=Sys.getenv("DB_HOST"), port=as.integer(Sys.getenv("DB_PORT")),
  user=Sys.getenv("DB_USER"), password=Sys.getenv("DB_PASSWORD"), dbname="mtgcards")

veggies <- c("ramp","card_advantage","targeted_disruption","mass_disruption")

df_kf <- tibble(DBI::dbGetQuery(con,"SELECT card_name, kf FROM public.labeled_kf_final"))
df_kf_tags <- df_kf %>%
  mutate(kf=map(as.character(kf),fromJSON)) %>%
  unnest_longer(kf,indices_to="category",values_to="tier")

df_tp_raw <- tibble(DBI::dbGetQuery(con,
  "SELECT card_name,raw_json_final FROM public.labeled_two_pass
   WHERE prompt_file='prompts/prompt11.md' AND model='claude-sonnet-4-6'"))
df_tp_tags <- df_tp_raw %>%
  filter(!is.na(raw_json_final)) %>%
  mutate(raw_json_final=map(as.character(raw_json_final),fromJSON)) %>%
  unnest_longer(raw_json_final,indices_to="category",values_to="tier") %>%
  filter(category!="card_name")

shared <- intersect(unique(df_tp_tags$card_name), unique(df_kf$card_name))

# full_join (used by meta report for tier_acc_veggies)
df_full <- df_tp_tags %>% filter(card_name %in% shared) %>%
  full_join(df_kf_tags %>% filter(card_name %in% shared),
            by=c("card_name","category"), suffix=c("_claude","_kf"))
df_full_v <- df_full %>% filter(category %in% veggies)

cat("=== full_join veggies (meta-report style) ===\n")
cat("rows:", nrow(df_full_v), "\n")
cat("detection acc (is.na agree):", round(mean(is.na(df_full_v$tier_kf)==is.na(df_full_v$tier_claude)),3),"\n")
cat("tier acc (na.rm=T):         ", round(mean(df_full_v$tier_kf==df_full_v$tier_claude,na.rm=TRUE),3),"\n\n")

# left_join from KF (used by two-pass report)
df_left <- df_kf_tags %>% filter(card_name %in% shared) %>%
  left_join(df_tp_tags %>% filter(card_name %in% shared),
            by=c("card_name","category"), suffix=c("_kf","_final"))
df_left_v <- df_left %>% filter(category %in% veggies)

cat("=== left_join from KF (two-pass report style) ===\n")
cat("rows:", nrow(df_left_v), "\n")
cat("detection acc (is.na agree):", round(mean(is.na(df_left_v$tier_kf)==is.na(df_left_v$tier_final)),3),"\n")
cat("tier acc (na.rm=T):         ", round(mean(df_left_v$tier_kf==df_left_v$tier_final,na.rm=TRUE),3),"\n")

DBI::dbDisconnect(con)
