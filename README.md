# Reddit Sentiment Analysis Dashboard

This project streams live Reddit comments from a subreddit, analyzes their sentiment using **VADER Sentiment**, and displays the results in a real-time interactive dashboard built with **Dash** and **Plotly**.

---

## Features

- Live Reddit comment streaming via **PRAW**
- Real-time sentiment analysis (positive/neutral/negative)
- Interactive dashboard with:
  - Rolling sentiment graph
  - Stats (average sentiment, comments processed)
  - Latest comments with color-coded sentiment
- Start/Stop streaming button

## Requirements

- Python 3.8+
- A Reddit API application (to get `client_id`, `client_secret`, `user_agent`)
