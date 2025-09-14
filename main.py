from openai import OpenAI
import os
import json
import subprocess

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
    response = client.responses.create(
        model="gpt-5",
        input=chat_memory,
        tools=tools,
    )
    # If it is a function call we check if it is a function type and call it again
    for item in response.output:
        if item.type == "function_call":

            if item.name == "execute_pyspice_script":
                pyspice_output = execute_pyspice_script(json.loads(item.arguments))
                chat_memory.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                    "pyspice_output": pyspice_output
                    })
                })
                # call again with the pyspice output
                response = client.responses.create(
                    model="gpt-5",
                    instructions="Respond only with the output of the executed PySpice script.",
                    tools=tools,
                    input=chat_memory,
                )
            elif item.name == "execute_schemedraw_script":
                schemedraw_output = execute_schemedraw_script(json.loads(item.arguments))
                chat_memory.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                    "schemedraw_output": schemedraw_output
                    })
                })
            elif item.name == "save_intermediate_circuit_representation":
                save_output = save_intermediate_circuit_representation(json.loads(item.arguments))
                chat_memory.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                    "save_output": save_output
                    })
                })

    chat_memory.append({"role": "assistant", "content": response.output_text})
    return response.output_text


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
    chat_memory = []
    chat_memory.append({"role": "system", "content": system_promt})
    chat_memory.append({"role": "user", "content": "You are a helpful assistant that can execute PySpice scripts."})
    while True:
        prompt = input("Enter your prompt: ")
        response = chat(prompt, chat_memory)
        print("Response: ", response)
if __name__ == "__main__":
    main()



