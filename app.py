import streamlit as st
import os
from dotenv import load_dotenv
import anthropic
from nba_api.stats.endpoints import commonallplayers
from nba_api.stats.endpoints import playercareerstats
from nba_api.stats.endpoints import franchisehistory
import json

load_dotenv()

class AnthropicFunctionCalling:
    def __init__(self):
        self.API_KEY = os.getenv('ANTHROPIC_API_KEY')
        self.MODEL_NAME = "claude-3-haiku-20240307"
        self.client = anthropic.Client(api_key=self.API_KEY)
        self.tools = [
            {
                "name": "get_player_info",
                "description": "Retrieves player information based on their name. Returns the player id and team",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "DISPLAY_FIRST_LAST": {
                            "type": "string",
                            "description": "The name for the player."
                        }
                    },
                    "required": ["DISPLAY_FIRST_LAST"]
                }
            },
            {
                "name": "get_player_statistics",
                "description": "Retrieves the statistics of a specific player based on the player name. Returns the player ID, most points scored in a season, free throw pct for the same season, and the team the player is currently playing for.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "DISPLAY_FIRST_LAST": {
                            "type": "string",
                            "description": "The name for the player."
                        }
                    },
                    "required": ["DISPLAY_FIRST_LAST"]
                }
            },
            {
                "name": "get_league_titles",
                "description": "Gets the number of league titles won by a team based on the team ID. Returns the team ID, team city, team name, start year, end year, and the number of league titles won.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "TEAM_ID": {
                            "type": "string",
                            "description": "The unique identifier for the team."
                        }
                    },
                    "required": ["TEAM_ID"]
                }
            }
        ]
    
    def get_player_info(self, player_name):
        players = commonallplayers.CommonAllPlayers()
        players_df = players.get_data_frames()[0]
        players_df = players_df[players_df['DISPLAY_FIRST_LAST'] == player_name]
        return players_df

    def get_player_statistics(self, player_name):
        player_info = self.get_player_info(player_name)
        player_id = player_info['PERSON_ID'].values[0]
        career = playercareerstats.PlayerCareerStats(player_id=player_id)
        career_df = career.get_data_frames()[0]
        career_df = career_df[career_df['PTS'] == career_df['PTS'].max()]
        career_df = career_df[['PLAYER_ID', 'SEASON_ID', 'PTS', 'FT_PCT', 'TEAM_ID', 'TEAM_ABBREVIATION']]
        return career_df

    def get_league_titles(self, team_id):
        history = franchisehistory.FranchiseHistory()
        history_df = history.get_data_frames()[0]   
        history_df = history_df[history_df['TEAM_ID'] == int(team_id)]
        history_df = history_df[['TEAM_ID','TEAM_CITY','TEAM_NAME','START_YEAR', 'END_YEAR', 'LEAGUE_TITLES']]
        return history_df
    
    def process_tool_call(self, tool_name, tool_input):
        if tool_name == "get_player_info":
            return self.get_player_info(tool_input["DISPLAY_FIRST_LAST"])
        elif tool_name == "get_player_statistics":
            return self.get_player_statistics(tool_input["DISPLAY_FIRST_LAST"])
        elif tool_name == "get_league_titles":
            return self.get_league_titles(tool_input["TEAM_ID"])
        
    def calculate_cost(self, model_type, response_body):

        if 'tools' not in response_body:
            input_tokens = response_body.usage.input_tokens
            output_tokens = response_body.usage.output_tokens
        else:
            input_tokens = response_body['usage']['input_tokens']
            output_tokens = response_body['usage']['output_tokens']
        # Define a dictionary with the cost per 1000 tokens for each model type
        cost_per_thousand_tokens = {
            "anthropic.claude-3-sonnet-20240229-v1:0": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "meta.llama2-70b-chat-v1": {"input": 0.00195, "output": 0.00256},
            "ai21.j2-ultra-v1": {"input": 0.0188, "output": 0.0188}
        }

        # Get the cost per 1000 tokens for the given model type
        cost = cost_per_thousand_tokens.get(model_type)

        if cost is None:
            raise ValueError(f"Invalid model type: {model_type}")

        # Calculate the total cost
        total_cost = cost["input"] * (input_tokens / 1000) + cost["output"] * (output_tokens / 1000)

        return total_cost
    
def main():
    st.title("NBA Chatbot")
    hakkoda_avatar = "Images/hakkoda.jpeg"

    afc = AnthropicFunctionCalling()

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if "dataframes" not in st.session_state:
        st.session_state.dataframes = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=hakkoda_avatar):
            st.markdown(message["content"])

    prompt = st.chat_input("Write your question")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=hakkoda_avatar):
            response = afc.client.beta.tools.messages.create(
                model=afc.MODEL_NAME,
                max_tokens=4096,
                tools=afc.tools,
                messages=st.session_state.messages
            )
            
            initial_response_cost = afc.calculate_cost(response.model, response)

            st.session_state.messages.append({"role": "assistant", "content": response.content})

            while response.stop_reason == "tool_use":
                tool_use = next(block for block in response.content if block.type == "tool_use")
                tool_name = tool_use.name
                tool_input = tool_use.input
                tool_result = afc.process_tool_call(tool_name, tool_input)

                st.session_state.messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": str(tool_result),
                            }
                        ],
                    }
                )

                response = afc.client.beta.tools.messages.create(
                    model=afc.MODEL_NAME,
                    max_tokens=4096,
                    tools=afc.tools,
                    messages=st.session_state.messages
                )

                second_response_cost = afc.calculate_cost(response.model, response)

                st.session_state.messages.append({"role": "assistant", "content": response.content})

            
            final_response = next(
                (block.text for block in response.content if hasattr(block, "text")),
                None,
            )

            formatted_response = f"""
            Based on the response, ensure to format the message as follows:

            {final_response}

            Rules:

            - The message should be formatted as a string.
            - The message should be a response to the user's question.
            - The message should not mention the tool used.
            - Do not include the xml tags in the response
            - Respond in the exact format in the examples below

            Example:

            <get_player_info>"Draymond Greene currently plays for the Golden State Warriors."</get_player_info>
            <get_player_statistics>"Here are some statistics regarding Draymond Greene:
            1. The most amount of points he scored in a season was 100 and that occured during the 2020-2021 season.
            2. His free throw percentage was 100% during the same season.
            3. For the season he had his most points scored, he played for the Golden State Warriors.
            "</get_player_statistics>
            <get_league_titles>"The Golden State Warriors have won 6 league titles."</get_league_titles>
            """

            st.session_state.messages.append({"role": "user", "content": final_response})
            formatted_response = [{'role': 'user', 'content': formatted_response}]

            final_output_response = afc.client.messages.create(
                model='claude-3-opus-20240229',
                max_tokens=4096,
                temperature=0.0,
                messages=formatted_response
            )
            final_output_response_text = final_output_response.content[0].text
            st.markdown(final_output_response_text)
            final_output_response_cost = afc.calculate_cost(response.model, final_output_response)
            total_cost = initial_response_cost + second_response_cost + final_output_response_cost

        st.session_state.messages.append({"role": "assistant", "content": final_output_response_text})
        st.session_state.dataframes.append((prompt, total_cost))

        for question, cost in st.session_state.dataframes:
            with st.expander(f"Question - {question}"):
                st.write(f"TOTAL COST: ${cost}")

    

if __name__ == "__main__":
    main()