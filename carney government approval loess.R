Sys.setlocale("LC_TIME", "English")
library(ggplot2)
library(anytime)
library(tidyverse)
library(svglite)
library(Rcpp)

### ---------- Parameters ----------
# Election system parameters
# Approve = Green, Disapprove = Red, Unsure = Grey
approvalcolors <- c("#2ca02c", "#d62728", "#7f7f7f")

startdate <- "2025-05-26"   # date of previous election
enddate <- "2026-07-01"     # (latest) date of next election

# Figure parameters
# individual smoothing parameter for the trend line of the 3 approval states
# this parameter must be decreased when the number of polls increases
approvalspansize <- c(0.25, 0.25, 0.25)

transp < - "55"              # transparency level of points
nnum <- 500                 # number of points used for trendline (resolution)
limits <- c(1, 40)          # percentage limits of figure
graph_width <- 18           # image width
graph_height <- 8           # image height


### ---------- Plotting code ----------
polls <- read.table(
                    "de.csv",
                    header = TRUE,
                    sep = ",",
                    fileEncoding = "UTF-8",
                    stringsAsFactors = FALSE)
polls$polldate <- as.Date(anydate(polls$polldate))

# retrieve the 3 approval states from CSV
approvalstatenames <- colnames(polls)[2:ncol(polls)]
# remove potential leading/trailing spaces so names match exactly
approvalstates <- trimws(approvalstates)

# safety check: same number of parties and colors
if (length(approvalcolors) != length(partynames)) {
  stop("The number of 'partycolors' must match the three state.")
}

# convert to long format (needed for legend & per-party smoothing)
polls_long <- polls |>
  pivot_longer(
    cols = all_of(partynames),
    names_to = "party",
    values_to = "value"
  )

# ensure the party factor has the same order as "partynames"
polls_long$party <- factor(polls_long$party, levels = partynames)

# start ggplot without global data so we can add per-party points
graph <- ggplot() +
  geom_vline(
             xintercept = as.Date(startdate),
             color = "#aaaaaabb") + #last election)
  #geom_vline(xintercept = as.Date(enddate), color="#aaaaaabb") +
  # vertical line (next election), comment out if unknown yet
  geom_segment(aes(x = as.Date(startdate),
                   xend = as.Date(enddate), y = threshold, yend = threshold),
               color = "#666666bb",
               linetype = "dashed")# horizontal line (election threshold 5%)

# add poll points per party
for (i in seq_along(partynames)) {
  pdata <- subset(polls_long, party == partynames[i])
  graph <- graph + geom_point(
    data = pdata,
    aes(x = polldate, y = value),
    size = ifelse(
                  pdata$polldate == as.Date(startdate) |
                    pdata$polldate == as.Date(enddate), 3, 1.5),
    shape = ifelse(
                   pdata$polldate == as.Date(startdate) |
                     pdata$polldate == as.Date(enddate), 23, 21),
    color = paste0(partycolors[i], transp),
    fill = paste0(partycolors[i], transp)
  )
}

# add trend lines per party
for (i in seq_along(partynames)) {
  pdata <- subset(polls_long, party == partynames[i])
  graph <- graph + geom_smooth(
    data = pdata,
    aes(x = polldate, y = value, color = party),
    method = "loess",
    span = partyspansize[i],
    n = nnum,
    se = FALSE
  )
}

# customize graph
graph <- graph +
  # y-axis: add % and custom limits
  scale_y_continuous(
                     labels = function(x) paste0(x, "%"),
                     limits = limits) +
  # x-axis: 1 month grid, labels every 3 months
  scale_x_date(
               limits = as.Date(c(startdate, enddate)),
               date_minor_breaks = "1 months",
               date_breaks = "3 months",
               date_labels = "%b %Y") +
  labs(x = "", y = "") +
  # apply colors and party names
  scale_color_manual(
    name = "",
    values = setNames(partycolors, partynames),
    breaks = partynames,
    labels = partynames
  ) +
  # legend appearance
  theme(
    axis.text.x = element_text(size = 11),
    axis.text.y = element_text(size = 12),
    axis.title.y = element_text(size = 16),
    legend.position = "right",
    legend.key.width = unit(24, "pt"),
    legend.key.height = unit(24, "pt"),
    legend.text = element_text(
                               size = 16,
                               margin = margin(b = 5, t = 5, unit = "pt"))
  )

graph

ggsave(
       file = "polls.svg",
       plot = graph,
       width = graph_width,
       height = graph_height)

# workaround since svglite doesn"t properly work in Wikipedia
aaa <- readLines("polls.svg", -1)
bbb <- gsub(".svglite ", "", aaa)
writeLines(bbb, "polls.svg")