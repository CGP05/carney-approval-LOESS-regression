## Overview
This is a non-parametric [local regression](https://en.wikipedia.org/wiki/Local_regression) graph for the Wikipedia page ["Opinion polling for the 46th Canadian federal election", specifically the section "Government approval"](https://en.wikipedia.org/wiki/Opinion_polling_for_the_46th_Canadian_federal_election#Government_approval_polls).

**Current version:**
<img width="1728" height="768" alt="image" src="https://github.com/user-attachments/assets/9e37c3f0-d108-421d-b111-7fe6db3b1b41" />



## Acknowledgements
Based off of [this person's](https://en.wikipedia.org/wiki/User:Gbuvn) [code on GitLab](https://gitlab.com/gbuvn1/opinion-polling-graph), which was used for LOESS regressions of election polls (from polling firms such as Abacus Data, Léger, and Ipsos) on Wikipedia, such as [this one](https://commons.wikimedia.org/wiki/File:Opinion_polling_graph_for_the_next_United_Kingdom_general_election_(post-2024).svg).

The previous graph (as seen below) was made by Wikipedia user ST2407 but stopped being updated for a long time and was [removed by them](https://en.wikipedia.org/w/index.php?title=Opinion_polling_for_the_46th_Canadian_federal_election&diff=prev&oldid=1360141768) from Wikipedia.

<img width="1208" height="748" alt="current graph" src="https://github.com/user-attachments/assets/9fae70fc-e1e4-4364-941f-d509792582c1" />


## Automated CSV Updates
[`update_polls.py`](update_polls.py) checks the Wikipedia page's "Table of polls" section daily for new government approval polls, parses the wikitext directly (rather than scraping rendered HTML), and appends any new rows to `carney government approval polls.csv`, skipping firms listed in [`Which polling firms to inlcude.md`](Which%20polling%20firms%20to%20inlcude.md). This runs via a scheduled [GitHub Actions workflow](.github/workflows/update-polls.yml), which also re-renders the LOESS plot and opens a GitHub issue summarizing any new polls when the CSV changes.
I will also try to update the original Wikipedia table with new polls.
A future project could be to scrape new polls directly from the pollters websites.