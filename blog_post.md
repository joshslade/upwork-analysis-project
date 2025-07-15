# Blog Post: From Upwork Noise to Airtable Signal: My Python-Powered Job Scraper

## Introduction

As a freelancer trying to build up a profile on Upwork, I spend a lot of time browsing for jobs. As anyone who has used the platform before will be aware, there are 1000s of jobs and a lot of competition. I found myself frustrated with the platform's interface. Sifting through countless unsuitable job postings, many that I'd already viewed in a previous sitting, to find the needles in the haystack was a daily time sink and motivation killer. I wanted a way to quickly identify the most promising opportunities and gain more control over the searching process. That's why I decided to build my own solution: a Python-based scraper that extracts Upwork job data and pushes it to a clean, manageable Airtable dashboard for triage and analysis.

This blog post chronicles my journey of developing this tool, from the initial idea to the final, automated workflow.

## A bit about me

I am an aspiring Data Freelancer. I am a full stack Data Scientist with nearly a decade of commercial experience working for a large multinational. I wasn't always a Data Scientist, I started my career as an Automotive Engineer working in an engine testing facility, but I have loved working with data, building machine learning models and developing automation in every job that I have done. In my current job, I don't get to be a professional data geek so I am turning to freelancing and Upwork to fulfill my passion in my free time.

This project was just as much about building a tool to solve a problem I faced as it is to test what I am capable of building; learning new frameworks, how to work with APIs and move data between different platforms. This project was also my first experience of `vibe coding`, testing out the new Gemini CLI from Google - more about my AI coding experience later.

So, back to the project...
## Using Gemini CLI
Previously I had been a religious user of ChatGPT, using it as a brain storming partner and problem solving assistant, however going to full agentic hands off mode with Gemini CLI has been a new experience entirely - turns out the warnings about ending up in a mess were true, be very careful of asking for a full refactor!

## The Problem: Upwork Overload

As a newbie, Upwork is incredibly daunting. Here's how my first experience went - 
I sign up for the free trial of Freelancer Plus (100 free connects (what are these for?) and access to an AI assistant called Uma). I'm looking for job postings requiring a data scientist and my proficiency is python, so naturally I searched for "Data Scientist Python" - internally this searches for job postings that contain all of those words so it matches to jobs also asking for "Data Engineering", "Data Mining", "Data Scraping" etc. With no additional filters, this returns over 1000 job postings. I scroll for a bit and see a job, "Data Clean-up Python", that I like the look of, something simple to get started with. I hit the apply now button, it's at this point that I discover what connects do, I use these connects as a currency when applying for jobs - it's a good job I got 100 for free! I use the lovely AI tool to generate a proposal, spent some more connects to boost my profile - I really want this first job! And finally once submitted I see some stats and realise that I am competing with 70 other bidders and after a few days the job is closed and see my proposal was never opened. This is going to be harder than I thought...

Fortunately, a week or so later I reached the stage of the Data Freelancer course where I learned from Upwork experts and coaches how the Upwork platform really works and how to avoid the mistakes that I made with my first experience. It's a shame I'll never get those connects back, but they say you learn from mistakes, although I think the lesson might have been one of patience rather than Upwork success! The course also showed how Upwork used to work with job postings available through an RSS feed that could be viewed in Airtable which allowed far more control over filtering and sorting of jobs. This looked great! I'm a data geek, I want to search for my jobs using code, custom filtering and advanced searching, I want to develop insights on my own behavior searching for jobs and use this to optimise my searches. Too bad the RSS feed was shut down deprecating the tool.

So armed with my new knowledge of how Upwork was supposed to work, and following strategies to identify jobs and screen clients before applying, I returned to the manual search. But I still found it very frustrating! I couldn't easily remove jobs that I had decided unsuitable from my feed so when I came back again later I would be scrolling through the same jobs again.

*   Decision fatigue from a cluttered UI.
*   Difficulty tracking promising leads.
*   Desire for a personalized and efficient job-hunting process.

## The Solution: A Personal ETL Pipeline

I designed a system that would allow me to:

1.  **Manually download** Upwork search results to respect their Terms of Service.
2.  **Automatically extract** job data from the downloaded HTML files.
3.  **Process and clean** the data to make it usable.
4.  **Store** the data in a long-term archive (Supabase).
5.  **Visualize and manage** the job leads in a user-friendly Airtable base.

### Tech Stack

*   **Python:** The core of the project, for its powerful data manipulation libraries.
*   **Playwright:** To render the JavaScript-heavy Upwork pages and extract the data.
*   **Pandas:** For data cleaning and transformation.
*   **Supabase:** As a robust, long-term data store.
*   **Airtable:** For a flexible and visually appealing front-end dashboard.
*   **Typer:** To create a simple and effective Command-Line Interface (CLI).

## The Development Journey

### Phase 1: Scraping with Playwright

The first challenge was getting the data out of the HTML files. Since Upwork uses a modern JavaScript framework (Nuxt.js), a simple `requests` and `BeautifulSoup` approach wouldn't work. I turned to Playwright, a powerful browser automation tool, to render the pages and access the underlying data.

### Phase 2: Data Processing and Storage

Once I had the raw JSON data, I used Pandas to clean it up, strip out HTML tags, and format it into a clean, tabular structure. I chose Supabase for long-term storage due to its ease of use and generous free tier.

### Phase 3: The Airtable Dashboard

This was the most rewarding part of the project. I designed an Airtable base with a Kanban view to track jobs from "Lead" to "Applied" to "Interview." Using the Airtable API, I wrote a script to sync the processed data from Supabase to my new dashboard.

### Phase 4: Automation with a CLI

To tie everything together, I built a CLI using Typer. Now, a single command (`python -m src.upwork_scraper run-all`) orchestrates the entire workflow: scraping, processing, storing, and syncing.

## The Final Workflow

1.  **Manual:** Save Upwork search pages as HTML.
2.  **Automated:** Run the CLI.
3.  **Review:** Triage new jobs in the Airtable dashboard.

## What I Learned

*   The power of browser automation tools like Playwright for modern web scraping.
*   The importance of a well-structured data pipeline.
*   The joy of building a custom solution that perfectly fits your needs.

## Future Plans

*   Explore automating the HTML download process.
*   Implement a more sophisticated job scoring and prioritization system.
*   Add notifications for high-priority jobs.

I hope this post gives you some insight into my project and inspires you to build your own tools to streamline your workflows. You can find the complete project on my GitHub!
