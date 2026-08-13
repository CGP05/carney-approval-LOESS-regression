Sys.setlocale("LC_TIME", "English")
library(ggplot2)
library(tidyverse)
library(svglite)

### ---------- Parameters ----------
# Election system parameters
# Approve = Green, Disapprove = Red
approvalcolors <- c("#2ca02c", "#d62728")

startdate <- "2025-05-14"   # 
enddate <- "2026-07-01"     # date of latest poll in table

# Figure parameters
# individual smoothing parameter for the trend line of the 3 approval states
# this parameter must be decreased when the number of polls increases
approvalspansize <- c(0.25, 0.25, 0.25)

transp <- "55"              # transparency level of points
nnum <- 500                 # number of points used for trendline (resolution)
limits <- c(25, 75)          # percentage limits of figure
graph_width <- 18           # image width
graph_height <- 8           # image height


### ---------- Plotting code ----------
#add Liaison Strategies and Angus Reid polls to the csv
polls <- read_csv(
                  "carney government approval polls.csv",
                  na = c("", "NA", "N/a", "—N/a", "—"),
                  locale = locale(encoding = "UTF-8"))

# Parse 2-digit years correctly (e.g., '22-Jun-26')
polls$Last_date_of_polling <- as.Date(polls$Last_date_of_polling, format = "%d-%b-%y") # nolint: line_length_linter.

# retrieve the 3 approval states from the CSV
approvalstates <- colnames(polls)[3:4]
# remove potential leading/trailing spaces so names match exactly
approvalstates <- trimws(approvalstates)

# Strip '%' signs and convert values to numbers (NA tokens handled by read_csv)
polls[approvalstates] <- lapply(polls[approvalstates], parse_number)

# safety check: same number of approval states and colors
if (length(approvalcolors) != length(approvalstates)) {
  stop("The number of 'approvalstates' must match the three states.")
}

# convert to long format (needed for legend & per approval state smoothing)
polls_long <- polls |>
  pivot_longer(
    cols = all_of(approvalstates),
    names_to = "approval",
    values_to = "value"
  )

# ensure the approval factor has the same order as "approvalstates"
polls_long$approval <- factor(polls_long$approval, levels = approvalstates)

# start ggplot without global data so we can add per approval state points
graph <- ggplot() +
  geom_vline(
             xintercept = as.Date(startdate),
             color = "#aaaaaabb")

# add poll points per approval state # nolint
for (i in seq_along(approvalstates)) {
  pdata <- subset(polls_long, approval == approvalstates[i])
  graph <- graph + geom_point(
    data = pdata,
    aes(x = Last_date_of_polling, y = value),
    size = ifelse(
                  pdata$Last_date_of_polling == as.Date(startdate) |
                    pdata$Last_date_of_polling == as.Date(enddate), 3, 1.5),
    shape = ifelse(
                   pdata$Last_date_of_polling == as.Date(startdate) |
                     pdata$Last_date_of_polling == as.Date(enddate), 23, 21),
    color = paste0(approvalcolors[i], transp),
    fill = paste0(approvalcolors[i], transp)
  )
}

# add trend lines per approval state
for (i in seq_along(approvalstates)) {
  pdata <- subset(polls_long, approval == approvalstates[i])
  graph <- graph + geom_smooth(
    data = pdata,
    aes(x = Last_date_of_polling, y = value, color = approval),

    method = "loess",
    span = approvalspansize[i],
    n = nnum,
    se = FALSE,
    na.rm = TRUE
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
  # apply colors and approval state names
  scale_color_manual(
    name = "",
    values = setNames(approvalcolors, approvalstates),
    breaks = approvalstates,
    labels = approvalstates
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
       file = "carney government approval polls.svg",
       plot = graph,
       width = graph_width,
       height = graph_height)

# workaround since svglite does not properly work in Wikipedia
aaa <- readLines("carney government approval polls.svg", -1)
bbb <- gsub(".svglite ", "", aaa)
writeLines(bbb, "carney government approval polls.svg")