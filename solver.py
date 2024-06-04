from openai import OpenAI, AssistantEventHandler, APIConnectionError
from typing_extensions import override
from os import system
from json import loads
from rich import print as rprint
import requests

client = OpenAI()

# Get the raw content of the file from GitHub
request = requests.get("https://raw.githubusercontent.com/smgabardo/AI_assistant/main/solver.json")
request.raise_for_status()
settings = request.json()
model_settings = settings["model"]

# Define the quit commands
quit_commands = settings["model"]["commands"]["quit"]
clear_commands = settings["model"]["commands"]["clear"]
formatted_quit_commands = ', '.join([f'!{cmd}' for cmd in quit_commands[:-1]]) + f', or !{quit_commands[-1]}'

def clear_terminal():
    pathname = '/Users/sergiogabardo/actual api testing'
    system(f'cd "{pathname}" && clear')

def format(unformatted_str) -> str:
    term = str(unformatted_str)
    if term[0].isupper() and term[1:].islower():
        return term.replace('.', '').strip().lower()
    else:
        return term.replace('.', '').strip()

def hyperlink(link: str, visual: str = None) -> str:
    if visual is None:
        visual = link
    return f"[link={link}]{visual}[/link]"

try:
    assistant = client.beta.assistants.create(
        name=model_settings["name"],
        tools=[{"type": "code_interpreter"}],
        temperature=model_settings["temperature"],
        top_p=model_settings["top_p"],
        model=model_settings["model"],
    )
except Exception as e:
    clear_terminal()
    base_link = "https://platform.openai.com/docs/guides/error-codes/python-library-error-types"
    match e:
        case APIConnectionError:
            link = base_link + '#:~:text=OVERVIEW-,APIConnectionError,-Cause%3A%20Issue'
            rprint(f"A {format(e)} ocurred. {hyperlink(link, "Learn more")} on {e}.")
    exit(1)

# creates an EventHandler class to define how we want to handle the events in the response stream
class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text):
        print(f"\n{assistant.name} > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

    def on_tool_call_created(self, tool_call):
        print(f"\n{assistant.name} > {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print("\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)


thread = client.beta.threads.create()

print(f"{len(str(thread.id)[6:32])} characters, {str(thread.id)[7:]}")
print(f"Welcome to equation helper!\nType {formatted_quit_commands} to quit.")

def retrieve_thread(t_id: str):  # outputs in <class 'openai.types.beta.thread.Thread'>
    return client.beta.threads.messages.list(
            thread_id=t_id
    )

while True:
    user_message = input(f"\n{settings["user"]["name"]} > ")

    if user_message.strip():
        if user_message.startswith('!') and user_message[1:].lower().strip() in quit_commands:
            rprint(f"Exiting the assistant. If you wish to continue this conversation, your thread id is [bold]{thread.id}[/bold]. Goodbye!")
            break
        elif user_message.lower().strip() in clear_commands or (user_message.startswith('!') and user_message[1:].lower().strip() in clear_commands):
            clear_terminal()
            break
        elif user_message.startswith('thread_'):
            retrieve_thread(user_message.lower().strip().replace('.', ''))
            break

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions=f"You are a fun and gangsta math tutor. Write and run code to answer math questions GANGSTA STYLE. Note that if a user provides an equation only, solve it without asking further questions. You may also help with general math questions, despite their depth. If a user requests for anything non-STEM related, provide a funny response, without actually answering the question. If the user asks for how to quit (or just tries to), provide one of the possible possibilities: {formatted_quit_commands}.",
        event_handler=EventHandler(),
    ) as stream:
        stream.until_done()