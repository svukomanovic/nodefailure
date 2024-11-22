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

def generate_graph_data_json(impact_reports):
    """Generate a JSON file containing graph data structured per node."""
    # Organize the reports by node
    nodes = sorted(set(report['node_name'] for report in impact_reports))
    graph_data = {}
    for node in nodes:
        node_reports = [report for report in impact_reports if report['node_name'] == node]
        node_graph = {
            'nodes': [],
            'edges': []
        }
        # Build node list and edges
        for report in node_reports:
            container_full_name = f"{report['namespace']}/{report['container_name']}"
            node_graph['nodes'].append({
                'id': container_full_name,
                'label': container_full_name,
                'criticality': report['criticality'],
                'description': report['description'],
                'dependencies': report['dependencies']
            })
            # Add edges for dependencies
            for dep in report['dependencies']:
                node_graph['edges'].append({
                    'from': container_full_name,
                    'to': dep
                })
        graph_data[node] = node_graph

    # Save to a JSON file
    filename = "graph_data.json"
    with open(filename, 'w') as f:
        json.dump(graph_data, f, indent=4)
    print(f"\nGraph data saved to '{filename}'.")

def main():
    # Check if session.json exists
    if not os.path.exists('session.json'):
        print("session.json not found. Collecting session data...")
        save_session_data()

    # Load session data
    session_data = load_session_data()
    if session_data is None:
        return

    # Get all containers
    pods_data = get_pods_all_nodes(session_data)
    containers = extract_containers(pods_data)
    if not containers:
        print("No containers found.")
        return

    # Load container info
    container_info = load_container_info()
    if container_info is None:
        return

    # Assess impact
    impact_reports, missing_containers = assess_impact(containers, container_info)

    if missing_containers:
        print("\nWarning: Some containers are missing from container_info.json:")
        for namespace, container_name in missing_containers:
            print(f"Namespace: {namespace}, Container: {container_name}")
        print("Consider updating container_info.json with these containers.")

    # Generate graph data JSON file
    generate_graph_data_json(impact_reports)

if __name__ == '__main__':
    main()
