import json
import subprocess
import os
from datetime import datetime

def save_session_data():
    """Retrieve node and pod information and save it to session.json."""
    # Retrieve nodes
    cmd_nodes = ['kubectl', 'get', 'nodes', '-o', 'json']
    result_nodes = subprocess.run(cmd_nodes, capture_output=True, text=True)
    nodes_data = json.loads(result_nodes.stdout)

    # Retrieve pods
    cmd_pods = ['kubectl', 'get', 'pods', '--all-namespaces', '-o', 'json']
    result_pods = subprocess.run(cmd_pods, capture_output=True, text=True)
    pods_data = json.loads(result_pods.stdout)

    # Save to session.json
    session_data = {
        'nodes': nodes_data,
        'pods': pods_data
    }
    with open('session.json', 'w') as f:
        json.dump(session_data, f, indent=4)
    print("Session data saved to 'session.json'.")

def load_session_data():
    """Load node and pod information from session.json."""
    if not os.path.exists('session.json'):
        print("session.json not found. Please run the script to generate session data.")
        return None
    with open('session.json', 'r') as f:
        session_data = json.load(f)
    return session_data

def get_node_list(session_data):
    """Retrieve the list of node names from the session data."""
    nodes_data = session_data['nodes']
    node_names = [node['metadata']['name'] for node in nodes_data['items']]
    return node_names

def select_node(node_names):
    """Prompt the user to select a node from the list, or choose to generate a combined report."""
    print("Available Nodes:")
    for idx, name in enumerate(node_names, start=1):
        print(f"{idx}. {name}")
    print(f"{len(node_names) + 1}. Generate combined report for all nodes")
    while True:
        try:
            choice = int(input("Select a node by entering the corresponding number: "))
            if 1 <= choice <= len(node_names):
                return node_names[choice - 1], False  # False indicates not a combined report
