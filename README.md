# Function Calling Starter project

This is a starter project for the function calling project here: https://hackmd.io/@timothy1ee/Hk1jhHCaA

It starts you off with a basic Chainlit app that streams responses, and maintains chat history. There is an initial system prompt that sets up an AI movie assistant that can generate a function call to fetch now playing movies.

There is a helper file that provides the required movie functions.

To run the app, use the following command:

```bash
chainlit run app.py -w
```

## Installation

### 1. Create a virtual environment

First, create a virtual environment to isolate the project dependencies:
```bash
python -m venv .venv
```

### 2. Activate the virtual environment:

- On Windows:
  ```bash
  .venv\Scripts\activate
  ```
- On macOS and Linux:
  ```bash
  source .venv/bin/activate
  ```

### 3. Set up environment variables

Copy the `.env_sample` file to `.env`:
```bash
cp .env_sample .env
```

Then edit the `.env` file and add your API keys:
- OPENAI_API_KEY: Your OpenAI API key
- TMDB_API_ACCESS_TOKEN: Your TMDB API access token
- SERP_API_KEY: Your SERP API key
- LANGCHAIN_API_KEY: Your LangChain API key

### 4. Install dependencies

Install the project dependencies from the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Updating dependencies

If you need to update the project dependencies, follow these steps:

1. Update the `requirements.in` file with the new package or version.

2. Install `pip-tools` if you haven't already:
   ```bash
   pip install pip-tools
   ```

3. Compile the new `requirements.txt` file:
   ```bash
   pip-compile requirements.in
   ```

4. Install the updated dependencies:
   ```bash
   pip install -r requirements.txt
   ```

This process ensures that all dependencies are properly resolved and pinned to specific versions for reproducibility.
