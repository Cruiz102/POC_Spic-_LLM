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
]

def execute_pyspice_script(script: str) -> str:
    with open("temp_script.py", "w") as f:
        f.write(script)
    result = subprocess.run(["python", "temp_script.py"], capture_output=True, text=True)
    os.remove("temp_script.py")
    if result.returncode != 0:
        return f"Error executing script: {result.stderr}"
    return result.stdout



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

    chat_memory.append({"role": "assistant", "content": response.output_text})
    return response.output_text


tool_promt = """You are a helpful assistant that can execute PySpice scripts. When given a prompt,
 you will generate a PySpice script to accomplish the task. You will then execute the script and return the output.

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
    chat_memory.append({"role": "system", "content": "You are a helpful assistant that can execute PySpice scripts."})
    while True:    
        promt = input("Enter your prompt: ")
        response = chat(promt, chat_memory)
        print("Response: ", response)
if __name__ == "__main__":
    main()



