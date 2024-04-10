
# NBA Chatbot using Anthropic API

This project integrates the Anthropic API to create a chatbot for querying NBA statistics. It uses the `nba_api` library to fetch player and team statistics.

## Features

- Fetch player information, including team and player ID, based on the player's name.
- Retrieve player statistics, like points scored in a season, free throw percentage, and current team.
- Get the number of league titles won by a team.

## Setup

1. Install the required Python libraries:
```bash
pip install streamlit dotenv anthropic nba_api
```
2. Create a `.env` file in the project root and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

Run the Streamlit application:

```bash
streamlit run app.py
```

In the app, you can enter a player's name or team ID to fetch the respective data and statistics.

## Code Overview

- `AnthropicFunctionCalling`: Class to handle API interaction and processing of NBA data.
- `get_player_info`, `get_player_statistics`, `get_league_titles`: Methods to fetch specific data from the NBA API.
- `process_tool_call`: Processes the function calls based on the tool name and input.
- `calculate_cost`: Calculates the cost of using the Anthropic API based on input and output tokens.
- `main`: The main function of the Streamlit app, handling the UI and session state.

## Deployment

The application can be deployed on a web server or run locally to interact with the NBA data through a chat interface.

## Notes

- Ensure you have a valid Anthropic API key set in your `.env` file.
- The cost of using the Anthropic API will depend on the number of tokens processed during the conversation.
