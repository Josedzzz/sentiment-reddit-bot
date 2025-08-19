import os
import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import deque
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import threading
import pandas as pd
import time
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get values
client_id = os.getenv("REDDIT_CLIENT_ID")
client_secret = os.getenv("REDDIT_CLIENT_SECRET")
user_agent = os.getenv("REDDIT_USER_AGENT")

# Reddit API Setup
reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    user_agent=user_agent
)

# Initialize sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Store sentiment history (shared between threads)
sentiment_history = deque(maxlen=100)
comments_processed = 0
all_comments = []
stop_streaming = False

def analyze_reddit_sentiment(subreddit_name="wallstreetbets", limit=1000):
    global comments_processed, sentiment_history, all_comments, stop_streaming
    subreddit = reddit.subreddit(subreddit_name)
    print(f"Streaming comments from r/{subreddit_name}...")

    try:
        for comment in subreddit.stream.comments(skip_existing=True):
            if stop_streaming:
                break

            try:
                # Get sentiment score
                sentiment = analyzer.polarity_scores(comment.body)
                compound_score = sentiment['compound']

                sentiment_history.append(compound_score)
                all_comments.append({
                    'text': comment.body[:100] + '...' if len(comment.body) > 100 else comment.body,
                    'sentiment': compound_score,
                    'timestamp': comment.created_utc
                })
                comments_processed += 1

                print(f"Comments: {comments_processed} | Sentiment: {compound_score:.3f} | Text: {comment.body[:50]}...")

                # Optional: Break after limit for demo
                if comments_processed >= limit:
                    break

            except Exception as e:
                print(f"Error processing comment: {e}")
                continue

    except Exception as e:
        print(f"Stream error: {e}")
        # Try to restart the stream after a delay
        time.sleep(5)
        if not stop_streaming:
            analyze_reddit_sentiment(subreddit_name, limit)

# Initialize Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Reddit Sentiment Analysis Live Dashboard", style={'textAlign': 'center'}),
    html.Button('Start/Stop Streaming', id='stream-button', n_clicks=0, 
                style={'margin': '10px', 'padding': '10px', 'backgroundColor': '#0074D9', 'color': 'white'}),
    dcc.Graph(id='live-sentiment-graph'),
    dcc.Interval(id='update-interval', interval=2000, n_intervals=0),
    html.Div([
        html.H3("Current Stats:", style={'textAlign': 'center'}),
        html.P(id='current-stats', style={'textAlign': 'center', 'fontSize': '20px'})
    ]),
    html.Div([
        html.H3("Recent Comments:", style={'textAlign': 'center'}),
        html.Div(id='recent-comments', style={
            'height': '200px', 
            'overflowY': 'scroll', 
            'border': '1px solid #ddd',
            'padding': '10px',
            'margin': '10px'
        })
    ])
])

@app.callback(
    [Output('live-sentiment-graph', 'figure'),
     Output('current-stats', 'children'),
     Output('recent-comments', 'children')],
    [Input('update-interval', 'n_intervals'),
     Input('subreddit-selector', 'value')]
)
def update_dashboard(subreddit):
    if not sentiment_history:
        # Create empty figure
        fig = go.Figure()
        fig.update_layout(
            title=f"Real-time Sentiment - r/{subreddit}",
            yaxis_title="Sentiment Score (-1 to +1)",
            yaxis=dict(range=[-1, 1])
        )
        return fig, "No data yet...", "No comments yet..."

    # Create rolling average
    window = min(20, len(sentiment_history))
    rolling_avg = pd.Series(sentiment_history).rolling(window=window, min_periods=1).mean().tolist()

    # Create figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=list(sentiment_history),
        mode='lines+markers',
        name='Raw Sentiment',
        opacity=0.6,
        marker=dict(size=4)
    ))
    fig.add_trace(go.Scatter(
        y=rolling_avg,
        mode='lines',
        name=f'{window}-comment Average',
        line=dict(width=3, color='red')
    ))
    
    fig.update_layout(
        title=f"Real-time Sentiment - r/{subreddit}",
        yaxis_title="Sentiment Score (-1 to +1)",
        showlegend=True,
        yaxis=dict(range=[-1, 1])
    )

    # Current stats
    current_sentiment = sum(sentiment_history) / len(sentiment_history)
    stats_text = f"Comments Analyzed: {comments_processed} | Avg Sentiment: {current_sentiment:.3f}"

    # Recent comments
    recent_comments = all_comments[-10:]  # Last 10 comments
    comments_html = []
    for comment in reversed(recent_comments):
        sentiment_color = "green" if comment['sentiment'] > 0.05 else "red" if comment['sentiment'] < -0.05 else "gray"
        comments_html.append(
            html.Div([
                html.Span(f"{comment['text']} ", style={'fontWeight': 'bold'}),
                html.Span(f"({comment['sentiment']:.3f})", 
                         style={'color': sentiment_color, 'fontSize': '12px'})
            ], style={'marginBottom': '5px'})
        )

    if not comments_html:
        comments_html = [html.P("No comments yet...")]

    return fig, stats_text, comments_html

@app.callback(
    Output('stream-button', 'style'),
    Input('stream-button', 'n_clicks')
)
def toggle_streaming(n_clicks):
    global stop_streaming
    stop_streaming = not stop_streaming if n_clicks > 0 else False
    
    if stop_streaming:
        return {'margin': '10px', 'padding': '10px', 'backgroundColor': '#FF4136', 'color': 'white'}
    else:
        return {'margin': '10px', 'padding': '10px', 'backgroundColor': '#0074D9', 'color': 'white'}

# Run Reddit stream in background
def run_reddit_stream():
    analyze_reddit_sentiment(limit=500)  # Adjust as needed

if __name__ == '__main__':
    # Start the Reddit stream in a separate thread
    thread = threading.Thread(target=run_reddit_stream, daemon=True)
    thread.start()

    app.run(debug=True, port=8050)
