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
            elif choice == len(node_names) + 1:
                return None, True  # True indicates combined report
            else:
                print(f"Please enter a number between 1 and {len(node_names) + 1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_pods_on_node(session_data, node_name):
    """Retrieve pods running on the selected node from session data."""
    pods_data = session_data['pods']
    pods_on_node = {
        'items': [
            pod for pod in pods_data['items']
            if pod['spec'].get('nodeName') == node_name
        ]
    }
    return pods_on_node

def get_pods_all_nodes(session_data):
    """Retrieve pods running on all nodes from session data."""
    return session_data['pods']

def extract_containers(pods_data):
    """Extract container names and namespaces from pods data."""
    containers = []
    for pod in pods_data['items']:
        namespace = pod['metadata']['namespace']
        pod_name = pod['metadata']['name']
        node_name = pod['spec'].get('nodeName', 'Unknown')
        for container in pod['spec']['containers']:
            containers.append({
                'namespace': namespace,
                'pod_name': pod_name,
                'container_name': container['name'],
                'node_name': node_name
            })
    return containers

def load_container_info():
    """Load predefined container information from a JSON file."""
    if not os.path.exists('container_info.json'):
        print("container_info.json not found. Please provide the container information.")
        return None
    with open('container_info.json') as f:
        return json.load(f)

def assess_impact(containers, container_info):
    """Assess the impact based on container criticality and dependencies."""
    reports = []
    missing_containers = []
    for container in containers:
        namespace = container['namespace']
        container_name = container['container_name']
        pod_name = container['pod_name']
        node_name = container['node_name']

        info = container_info.get(namespace, {}).get(container_name)
        if info is None:
            missing_containers.append((namespace, container_name))
            info = {
                'description': 'No information available',
                'dependencies': [],
                'criticality': 'unknown'
            }

        criticality = info.get('criticality', 'unknown')
        if criticality == 'high':
            impact = 'High impact'
            criticality_sort = 1
        elif criticality == 'medium':
            impact = 'Moderate impact'
            criticality_sort = 2
        elif criticality == 'low':
            impact = 'Low impact'
            criticality_sort = 3
        else:
            impact = 'Unknown impact'
            criticality_sort = 4

        reports.append({
            'namespace': namespace,
            'pod_name': pod_name,
            'container_name': container_name,
            'node_name': node_name,
            'description': info.get('description', 'No information available'),
            'dependencies': info.get('dependencies', []),
            'criticality': criticality,
            'criticality_sort': criticality_sort,
            'impact': impact
        })
    return reports, missing_containers

def generate_consolidated_json(impact_reports):
    """Generate a consolidated JSON file with the impact reports."""
    # Get current date and time for the filename (exclude seconds)
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"consolidated_{current_datetime}.json"

    # Organize the reports by node
    nodes = sorted(set(report['node_name'] for report in impact_reports))
    consolidated_data = {}
    for node in nodes:
        node_reports = [report for report in impact_reports if report['node_name'] == node]
        consolidated_data[node] = node_reports

    # Save to a JSON file
    with open(filename, 'w') as f:
        json.dump(consolidated_data, f, indent=4)
    print(f"\nConsolidated data saved to '{filename}'.")

def main():
    # Check if session.json exists
    if not os.path.exists('session.json'):
        print("session.json not found. Collecting session data...")
        save_session_data()

    # Load session data
    session_data = load_session_data()
    if session_data is None:
        return

    node_names = get_node_list(session_data)
    if not node_names:
        print("No nodes found in the session data.")
        return
    selected_node, is_combined = select_node(node_names)
    container_info = load_container_info()
    if container_info is None:
        return

    if is_combined:
        print("\nGenerating consolidated report for all nodes...\n")
        pods_data = get_pods_all_nodes(session_data)
    else:
        print(f"\nSelected Node: {selected_node}\n")
        pods_data = get_pods_on_node(session_data, selected_node)

    containers = extract_containers(pods_data)
    if not containers:
        print("No containers found.")
        return

    impact_reports, missing_containers = assess_impact(containers, container_info)

    if missing_containers:
        print("\nWarning: Some containers are missing from container_info.json:")
        for namespace, container_name in missing_containers:
            print(f"Namespace: {namespace}, Container: {container_name}")
        print("Consider updating container_info.json with these containers.")

    # Generate consolidated JSON file
    generate_consolidated_json(impact_reports)

if __name__ == '__main__':
    main()
