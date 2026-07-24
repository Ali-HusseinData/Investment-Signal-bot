# Investment Signal Bot

This project implements a modular Python bot to generate investment signals (Buy/Sell/Hold) for Stocks, Gold, and Crypto assets. It combines real-time price data, financial news sentiment analysis using FinBERT, and a customizable logic engine.

## Features

- **Data Fetching**: Retrieves current prices and technical indicators (50-day Moving Average) using `yfinance`, and fetches recent financial news headlines from NewsAPI.
- **Sentiment Analysis**: Utilizes the `transformers` library with the pre-trained FinBERT model (`ProsusAI/finbert`) to analyze the sentiment of news headlines.
- **Signal Logic Engine**: Generates 'Buy', 'Sell', or 'Hold' signals based on a combination of technical data and news sentiment.
- **Modular Architecture**: Code is separated into distinct modules for easy maintenance, updates, and swapping out components (e.g., different news APIs, sentiment models, or signal logic).
- **Alerting Placeholder**: Includes a placeholder function for integrating with external alerting services like Telegram or Discord webhooks.

## Project Structure

```
investment_signal_bot/
├── config/
│   ├── __init__.py
│   └── config.py             # API keys and configuration
├── data_fetching/
│   ├── __init__.py
│   └── fetcher.py            # Handles price data and news fetching
├── sentiment_analysis/
│   ├── __init__.py
│   └── analyzer.py           # FinBERT sentiment analysis
├── signal_engine/
│   ├── __init__.py
│   └── engine.py             # Signal generation logic and alerting
├── main.py                   # Main orchestrator to run the bot
└── requirements.txt          # Python dependencies
└── README.md                 # Project README
```

## Setup and Installation

1.  **Clone the repository (or create the files manually):**

    ```bash
    git clone <repository_url>
    cd investment_signal_bot
    ```

2.  **Create a Python virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Keys:**

    Copy the template to create your own local config (which is git-ignored, so
    your keys are never committed):

    ```bash
    cp config/config.example.py config/config.py     # macOS/Linux
    copy config\config.example.py config\config.py   # Windows
    ```

    Then open `config/config.py` and fill in your keys:

    ```python
    # config/config.py
    NEWS_API_KEY = "YOUR_NEWSAPI_KEY"
    FINNHUB_API_KEY = "YOUR_FINNHUB_KEY"
    ```

    You can obtain free API keys from [NewsAPI.org](https://newsapi.org/) and
    [Finnhub.io](https://finnhub.io/).

## How to Run

Execute the `main.py` script from the project root:

```bash
python main.py
```

The bot will process the predefined assets (Bitcoin, Gold, Apple Stock), fetch data, analyze sentiment, generate signals, and print a daily summary report to the console. It will also show a placeholder message for sending alerts.

## Extending the Bot

-   **Add/Remove Assets**: Modify the `assets` dictionary in `main.py`.
-   **Change News API**: Implement a new fetching method in `data_fetching/fetcher.py`.
-   **Swap Sentiment Model**: Modify `sentiment_analysis/analyzer.py` to use a different `transformers` model or an entirely different sentiment analysis approach.
-   **Refine Signal Logic**: Adjust the `generate_signal` method in `signal_engine/engine.py` to implement more complex trading strategies.
-   **Implement Real Alerts**: Integrate actual webhook calls in `signal_engine/engine.py` to send alerts to Telegram, Discord, or other platforms.
