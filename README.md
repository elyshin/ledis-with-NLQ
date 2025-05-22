# ledis-with-NLQ
 Ledis: A lightweight Redis server with NLQ features.

## Python Version

Python 3.9.9

## Notes
By default, the server uses a Hugging Face model that is downloaded into a folder called `model_cache` in the project directory. This avoids using the default Hugging Face cache and makes model management easier.

You can change which model is used by editing the model name in `llm.py`.

## Setup Instructions

1. Clone the repository

    ```bash
    git clone https://github.com/elyshin/ledis-with-NLQ
    cd ledis-nlp
    ```

2. (Optional) Create and activate a virtual environment

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install required libraries

    ```bash
    pip install -r requirements.txt
    ```

4. Install SpaCy language model

    ```bash
    python -m spacy download en_core_web_md
    ```

## Running the Application

1. Start the FastAPI server

    ```bash
    fastapi run server.py
    ```

2. Open a new terminal and launch the CLI

    ```bash
    python cli.py
    ```

