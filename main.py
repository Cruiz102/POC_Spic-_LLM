from openai import OpenAI
import os
import json
import subprocess
import argparse
import datetime
import traceback

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)
tools = [
    {
        "type": "function",
        "name": "execute_pyspice_script",
        "description": "This tool will execute a PySpice script and return the output.",
        "parameters": {
            "type": "object",
            "properties": {
                "pyspice_script": {
                    "type": "string",
                    "description": "The pyspice script to execute",
                },
            },
            "required": ["pyspice_script"],
        },
    },
    {
        "type": "function",
        "name": "execute_schemedraw_script",
        "description": "This tool will execute a Schemedraw script and return the file path of the image.",
        "parameters": {
            "type": "object",
            "properties": {
                "schemedraw_script": {
                    "type": "string",
                    "description": "The schemedraw script to execute",
                },
            },
            "required": ["schemedraw_script"],
        },
    },
        {
        "type": "function",
        "name": "save_intermediate_circuit_representation",
        "description": "This tool will save the intermediate circuit representation.",
        "parameters": {
            "type": "object",
            "properties": {
                "circuit_representation": {
                    "type": "string",
                    "description": "The intermediate circuit representation to save",
                },
            },
            "required": ["circuit_representation"],
        },
    },
]

def execute_pyspice_script(script: str) -> str:
    with open("temp_script.py", "w") as f:
        f.write(script)
    result = subprocess.run(["python", "temp_script.py"], capture_output=True, text=True)
    os.remove("temp_script.py")
    if result.returncode != 0:
        return f"Error executing script: {result.stderr}"
    return result.stdout

def execute_schemedraw_script(script: str) -> str:
    with open("scheme_script.py", "w") as f:
        f.write(script)
    result = subprocess.run(["python", "scheme_script.py"], capture_output=True, text=True)
    os.remove("scheme_script.py")
    if result.returncode != 0:
        return f"Error executing script: {result.stderr}"
    return result.stdout

def save_intermediate_circuit_representation(circuit_representation: str) -> str:
    with open("circuit_representation.py", "w") as f:
        f.write(circuit_representation)
    return "Circuit representation saved to circuit_representation.py"



def chat(prompt: str, chat_memory: list) -> str:
    chat_memory.append({"role": "user", "content": prompt})

    # Iteratively call the model until no more function_call outputs are returned
    accumulated_text = ""
    while True:
        response = client.responses.create(
            model="gpt-5",
            input=chat_memory,
            tools=tools,
        )

        # Collect plain assistant text (if any) from this round
        round_text = getattr(response, 'output_text', '') or ''
        if round_text:
            accumulated_text += ("\n" if accumulated_text and round_text else "") + round_text

        # Gather tool calls
        tool_calls = [item for item in response.output if item.type == "function_call"]
        if not tool_calls:
            # No more tool calls -> finalize
            chat_memory.append({"role": "assistant", "content": accumulated_text})
            return accumulated_text

        # For each tool call, run the corresponding function and append a function_call_output object
        for call in tool_calls:
            try:
                parsed_args = json.loads(call.arguments) if isinstance(call.arguments, str) else (call.arguments or {})
            except Exception:
                parsed_args = {}

            output_payload = {}
            if call.name == "execute_pyspice_script":
                script = parsed_args.get("pyspice_script")
                if not isinstance(script, str):
                    output_payload['pyspice_output'] = "Error: expected 'pyspice_script' string argument"
                else:
                    output_payload['pyspice_output'] = execute_pyspice_script(script)
            elif call.name == "execute_schemedraw_script":
                script = parsed_args.get("schemedraw_script")
                if not isinstance(script, str):
                    output_payload['schemedraw_output'] = "Error: expected 'schemedraw_script' string argument"
                else:
                    output_payload['schemedraw_output'] = execute_schemedraw_script(script)
            elif call.name == "save_intermediate_circuit_representation":
                rep = parsed_args.get("circuit_representation")
                if not isinstance(rep, str):
                    output_payload['save_output'] = "Error: expected 'circuit_representation' string argument"
                else:
                    output_payload['save_output'] = save_intermediate_circuit_representation(rep)
            else:
                output_payload['error'] = f"Unknown tool name: {call.name}"

            chat_memory.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(output_payload)
            })

        # Loop continues; the updated chat_memory (with function_call_output items) is sent next iteration


# ----------------------------- Persistence Helpers -----------------------------
def save_chat_memory(chat_memory, path):
    """Persist chat memory to a JSON file."""
    with open(path, 'w') as f:
        json.dump(chat_memory, f, indent=2)


def load_chat_memory(path):
    """Load previously saved chat memory from JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


system_promt = """

You are a helpful assistant that can do the following things:
 You have access to a pyspice enviroment where you can execute pyspice scripts and can draw with schemedraw.

 You can do the following operations:

 the user will ask you a question about basic analogs circuits. You will specify that you can only work with (RC) circuits.
 if the user ask you to create a circuit that is not an RC circuit you will tell them that you can only work with RC circuits.

 The first thing that will ask for is to provide a description of the circuit they want to create. That means that you will
 iterate with the user until you have a full description of the circuit they want to create.


 After having a good description of the circuit you will create a a graph represention of the circuit.
 build a list of components and nodes that you will use to create the circuit with the following format:


 # ---------- 1) Common circuit IR ----------
@dataclass
class Component:
    name: str        # e.g. "R1", "C1", "V1"
    ctype: str       # 'R','C','V','I','D', ...
    nodes: Tuple[str, str]  # (n1, n2)
    value: str       # '10k', '1uF', '5V', etc.


after creating the description you will interpret the lost of components and draw the circuit with schemedraw.
you will create a script that visualize it and save that into a file called circuit.png


The user with this visualiztion could prompt you to change some components or values. so you will iterate with the user until they are satisfied with the circuit.



after doing that you will create a pyspice script that simulate the circuit and print the output voltages of each node.
you will run the script and return the output to the user.


 The following is an example of a PySpice script that creates a simple RC circuit and simulates its transient response:
 import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()


from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

circuit = Circuit('Resistor Bridge')

circuit.V('input', 1, circuit.gnd, 10@u_V)
circuit.R(1, 1, 2, 2@u_kΩ)
circuit.R(2, 1, 3, 1@u_kΩ)
circuit.R(3, 2, circuit.gnd, 1@u_kΩ)
circuit.R(4, 3, circuit.gnd, 2@u_kΩ)
circuit.R(5, 3, 2, 2@u_kΩ)

simulator = circuit.simulator(temperature=25, nominal_temperature=25)
analysis = simulator.operating_point()

for node in analysis.nodes.values():
    print('Node {}: {:4.1f} V'.format(str(node), float(node))) # Fixme: format value + unit



"""



def main():
    parser = argparse.ArgumentParser(description="Interactive PySpice assistant with resume capability")
    parser.add_argument('--resume', metavar='FILE', help='Resume from a previously saved chat memory JSON file')
    parser.add_argument('--auto-save', metavar='FILE', default='chat_memory_autosave.json', help='Autosave chat memory after each turn')
    parser.add_argument('--dump-on-crash', metavar='FILE', default=None, help='File to dump chat memory if an unhandled exception occurs (default: timestamped)')
    args = parser.parse_args()

    if args.resume:
        try:
            chat_memory = load_chat_memory(args.resume)
            print(f"[Resume] Loaded chat memory from {args.resume} (entries={len(chat_memory)})")
        except Exception as e:
            print(f"[Resume] Failed to load {args.resume}: {e}. Starting fresh.")
            chat_memory = []
    else:
        chat_memory = []

    # Ensure system prompt exists exactly once at start of a fresh session
    if not any(m.get('role') == 'system' for m in chat_memory):
        chat_memory.append({"role": "system", "content": system_promt})
        chat_memory.append({"role": "user", "content": "You are a helpful assistant that can execute PySpice scripts."})

    def autosave():
        if args.auto_save:
            try:
                save_chat_memory(chat_memory, args.auto_save)
            except Exception as e:
                print(f"[Warn] Failed autosave: {e}")

    autosave()

    try:
        while True:
            try:
                prompt = input("Enter your prompt: ")
            except EOFError:
                print("\n[Exit] EOF received. Saving and quitting.")
                autosave()
                break
            if prompt.strip().lower() in {':q', 'quit', 'exit'}:
                print('[Exit] User requested termination.')
                autosave()
                break
            response_text = chat(prompt, chat_memory)
            print("Response: ", response_text)
            autosave()
    except KeyboardInterrupt:
        print("\n[Exit] KeyboardInterrupt. Saving state.")
        autosave()
    except Exception:
        # Crash dump
        dump_file = args.dump_on_crash or f"chat_memory_crash_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
        try:
            save_chat_memory(chat_memory, dump_file)
            print(f"[Crash] Unhandled exception. Chat memory dumped to {dump_file}")
        except Exception as se:
            print(f"[Crash] Failed to dump chat memory: {se}")
        print("[Crash] Exception traceback:")
        traceback.print_exc()
        raise
if __name__ == "__main__":
    main()



