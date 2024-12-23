import json
from dotenv import load_dotenv
import chainlit as cl
from movie_functions import get_now_playing_movies, get_showtimes
import litellm
from datetime import datetime

load_dotenv(override=True)

from langsmith import traceable
litellm.success_callback = ["langsmith"] 

# Choose one of these model configurations by uncommenting it:

# OpenAI GPT-4
# model = "openai/gpt-4o"

# Anthropic Claude
model = "claude-3-5-sonnet-20241022"

# Fireworks Qwen
# model = "fireworks_ai/accounts/fireworks/models/qwen2p5-coder-32b-instruct"

gen_kwargs = {
    "temperature": 0.2,
    "max_tokens": 500
}

SYSTEM_PROMPT_V1 = """\
You are a helpful movie chatbot that helps people explore movies that are out in \
theaters. If a user asks for recent information, output a function call and \
the system add to the context. If you need to call a function, only output the \
function call. Call functions using Python syntax in plain text, no code blocks.

You have access to the following functions:

get_now_playing()
get_showtimes(title, location)
buy_ticket(theater, movie, showtime)
confirm_ticket_purchase(theater, movie, showtime)
"""

SYSTEM_PROMPT = """\
You are an AI movie assistant designed to provide information about currently \
playing movies and engage in general movie-related discussions. Your primary \
function is to answer questions about movies currently in theaters and offer \
helpful information to users interested in cinema.

You have access to the following functions:

<available_functions>
{
  "get_now_playing": {
    "description": "Fetches a list of movies currently playing in theaters",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  },
  "get_showtimes": {
    "description": "Fetches a list of movies currently playing in theaters",
    "parameters": {
      title: {
        type: "string",
        description: "The title of the movie to get showtimes for",
        required: true,
      },
      location: {
        type: "string",
        description: "The location to get showtimes for",
        required: true,
      },
    },
  "buy_ticket": {
    "description": "Buys a ticket for a movie at a specific theater and showtime",
    "parameters": {
      movie: {
        type: "string",
        description: "The title of the movie to buy a ticket for",
        required: true,
      },
      theater: {
        type: "string",
        description: "The movie theater to buy a ticket for",
        required: true
      },
      showtime: {
        type: "string",
        description: "The showtime to buy a ticket for",
        required: true
      },
    }
  },
  "confirm_ticket_purchase": {
    "description": "Confirms the purchase of a ticket for a movie at a specific theater and showtime",
    "parameters": {
      movie: {
        type: "string",
        description: "The title of the movie to buy a ticket for",
        required: true,
      },
      theater: {
        type: "string",
        description: "The movie theater to buy a ticket for",
        required: true
      },
      showtime: {
        type: "string",
        description: "The showtime to buy a ticket for",
        required: true
      },
    }
  }
}
</available_functions>

To use any function, generate a function call in JSON format, wrapped in \
<function_call> tags. For example:
<function_call>
{
  "name": "get_now_playing",
  "arguments": {}
}
</function_call>

When making a function call, output ONLY the thought process and function call, \
then stop. Do not provide any additional information until you receive the function \
response.

When answering questions, follow these guidelines:

1. Always begin with a <thought_process> section to think through your response \
strategy. Consider:
   a. Determine if the question is about currently playing movies or general \
cinema topics
   b. Identify key elements of the question (e.g., specific movie titles, \
genres, actors)
   c. Decide if any available functions are needed
   d. Assess your confidence level based on the following criteria:
      - High confidence: Questions about movies released before 2020, film \
history, classic directors, or basic cinema concepts
      - Medium confidence: Questions about movies from 2020-2022, general \
industry trends, or recent developments in cinema
      - Low confidence: Questions about movies released after 2022, \
        box office numbers, or current industry specifics

2. If the question is to fetch currently playing movies:
   - Call the get_now_playing function before responding

3. For general movie-related discussions:
   - Draw upon your knowledge of cinema, directors, actors, and film history
   - Be aware that your knowledge of older movies is likely to be more accurate \
than your knowledge of recent movies
   - Offer recommendations based on genres, actors, or directors mentioned in \
the conversation
   - Explain basic film terminology or concepts if asked

4. When answering:
   - Prioritize accuracy over speculation
   - If you're unsure about something, especially regarding recent movies, \
admit it and offer to provide related information you are confident about
   - Keep responses concise but informative
   - If a question is unclear, ask for clarification before answering

Example interactions:

1. User: "What movies are playing in theaters right now?"
<thought_process>
The user wants to know about current movie listings. I need to fetch this \
real-time information using the get_now_playing function.
</thought_process>

<function_call>
{
  "name": "get_now_playing",
  "arguments": {}
}
</function_call>

2. User: "Can you tell me about the French New Wave? I'm interested in learning \
about classic film movements."
<thought_process>
This is a question about film history and a major cinematic movement. I have \
high confidence in this topic as it's well-documented historical information \
that doesn't require current data.
</thought_process>

The French New Wave (Nouvelle Vague) was a groundbreaking film movement that \
emerged in France during the late 1950s and 1960s. Led by young \
critics-turned-filmmakers like François Truffaut and Jean-Luc Godard, it \
revolutionized cinema with innovative techniques and storytelling approaches. \
Some essential films from this period include "The 400 Blows" (1959), \
"Breathless" (1960), and "Cléo from 5 to 7" (1962). Would you like to know \
more about specific directors or techniques from this movement?

3. User: "Who directed The Godfather?"
<thought_process>
This is a straightforward question about a classic film from 1972. I have high \
confidence in this information as it's a well-established historical fact.
</thought_process>

The Godfather was directed by Francis Ford Coppola. Released in 1972, it's \
considered one of the greatest films ever made and won him the Academy Award \
for Best Picture and Best Adapted Screenplay, though he lost Best Director to \
Bob Fosse for Cabaret that year.
"""

def extract_tag_content(text: str, tag_name: str) -> str | None:
    """
    Extract content between XML-style tags.
    
    Args:
        text: The text containing the tags
        tag_name: Name of the tag to find
        
    Returns:
        String content between tags if found, None if not found
        
    Example:
        >>> text = "before <foo>content</foo> after"
        >>> extract_tag_content(text, "foo")
        'content'
    """
    import re
    pattern = f"<{tag_name}>(.*?)</{tag_name}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else None

@traceable
@cl.on_chat_start
def on_chat_start():    
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)

@cl.on_message
@traceable
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    response_message = cl.Message(content="")
    await response_message.send()

    response = litellm.completion(
        model=model,
        messages=message_history,
        stream=True,
        **gen_kwargs
    )
    
    for part in response:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)
    
    await response_message.update()

    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)

    # The confirmation map gets reset every time we drop out of the function call loop so ticket purchase only occurs on "confirm_ticket_purchase" -> "buy_ticket" sequence
    # I could have just had buy-ticket do confirmation and then have confirm_ticket_purchase do the purchase but I wanted to experiment with keeping the context outisde the conversation
    confirmation_map = {}
    while True:
      
      context_str = extract_tag_content(response_message.content, "function_call")
      if context_str is None:
        break
      context_json = json.loads(context_str)
      print (f"[CONTEXT]: {context_json}")
      if context_json is not None:
        func_name = context_json['name']
        print(f"[CALLING FUNCTION]: {func_name}")
        if func_name == "get_now_playing":
            movies = get_now_playing_movies()
            date = datetime.now().strftime("%Y-%m-%d")
            context_message = {"role": "user", "content": f"CONTEXT Today's date is {date} and here are movies with their release dates. All movies with release date before today's date are currently playing: {movies}"}
        elif func_name == "get_showtimes":
            title = context_json.get("arguments", {}).get("title", "Unknown Title")
            location = context_json.get("arguments", {}).get("location", "Unknown Location")
            showtimes = get_showtimes(title, location)
            context_message = {"role": "user", "content": f"CONTEXT: {showtimes}"}
        elif func_name == "buy_ticket":
            theater = context_json.get("arguments", {}).get("theater", "Unknown Theater")
            movie = context_json.get("arguments", {}).get("movie", "Unknown Movie")
            showtime = context_json.get("arguments", {}).get("showtime", "Unknown Showtime")
            key = (movie, theater, showtime)

            if key not in confirmation_map: 
              confirmation = f"First confirm ticket purchase for {movie} at {theater} for the {showtime} showtime. If user confirms buy the ticket, else cancel the ticket purchase."
              context_message = {"role": "user", "content": f"CONTEXT: {confirmation}"}
            elif confirmation_map[key] is True:
              ticket_purchase = f"Buying a ticket for {movie} at {theater} for the {showtime} showtime."
              context_message = {"role": "user", "content": f"CONTEXT: {ticket_purchase}"}
            else:
              ticket_purchase = f"Ticket purchase for {movie} at {theater} for the {showtime} showtime cancelled."
              context_message = {"role": "user", "content": f"CONTEXT: {ticket_purchase}"}
        elif func_name == "confirm_ticket_purchase":
            theater = context_json.get("arguments", {}).get("theater", "Unknown Theater")
            movie = context_json.get("arguments", {}).get("movie", "Unknown Movie")
            showtime = context_json.get("arguments", {}).get("showtime", "Unknown Showtime")
            key = (movie, theater, showtime)
            confirmation_map[key] = True
            confirmation = f"Confirmed ticket purchase for {movie} at {theater} for the {showtime} showtime. Proceed to buy the ticket"
            context_message = {"role": "user", "content": f"CONTEXT: {confirmation}"}
        else:
            context_message = {"role": "user", "content": "CONTEXT: Function call not recognized."}

        print (f"[FUNCTION RETURNED]: {context_message}")
        message_history.append(context_message)
        # send response of the function call
        response_message = cl.Message(content="")
        await response_message.send()

        response = litellm.completion(
            model=model,
            messages=message_history,
            stream=True,
            **gen_kwargs
        )
        
        for part in response:
            if token := part.choices[0].delta.content or "":
                await response_message.stream_token(token)
        
        await response_message.update()
        message_history.append({"role": "assistant", "content": response_message.content})
        cl.user_session.set("message_history", message_history)
    
if __name__ == "__main__":
    cl.main()
